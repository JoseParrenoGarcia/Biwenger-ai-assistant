# app/llm/openai_backend.py
from __future__ import annotations
from typing import TypedDict, Optional, Dict, Any, Tuple, List
from openai import OpenAI
import tomllib
import json
from pathlib import Path
import inspect

from tools.registry import MAKE_PLAN_SPEC, TOOLS_SPECS, TOOL_REGISTRY

# ---------- Types / Interface ----------
class Message(TypedDict):
    role: str
    content: str
    name: Optional[str]  # for tool role messages
    tool_call_id: Optional[str]

# ---------- Config & helpers ----------
def _load_openai_config() -> dict:
    """
    Loads OpenAI credentials from ./secrets/openAI.toml (local) or env vars (cloud).
    Expected file structure:
        [openai]
        api_key = "sk-..."
        model = "..."
    """
    # 2️⃣ If missing, fall back to secrets file
    secrets_path = Path(__file__).resolve().parent.parent / "secrets" / "openAI.toml"

    if not secrets_path.exists():
        raise FileNotFoundError(f"Missing OpenAI secrets at {secrets_path}")
    with open(secrets_path, "rb") as f:
        config = tomllib.load(f)

    api_key = config["openai"].get("api_key")
    model = config["openai"].get("model")

    if not api_key:
        raise ValueError("OpenAI API key not found in secrets file.")
    if not model:
        raise ValueError("OpenAI model not found in secrets file.")

    return {"api_key": api_key, "model": model}

def _tools_specs_to_text(specs) -> str:
    lines = []
    for s in specs:
        fn = s.get("function", {})
        name = fn.get("name", "")
        desc = (fn.get("description") or "").strip()
        lines.append(f"{name}:\n{desc}")
    return "\n\n".join(lines)

def _is_dataframe(x) -> bool:
    try:
        import pandas as pd
        return isinstance(x, pd.DataFrame)
    except Exception:
        return False

# ---------- Backend ----------
class OpenAIChatBackend:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        cfg = _load_openai_config()
        self.api_key = api_key or cfg["api_key"]
        self.model = model or cfg["model"]
        self.client = OpenAI(api_key=self.api_key)

    # -------------------------
    # PLANNING PHASE
    # -------------------------
    def stream_planner(
            self,
            user_text: str,
            context: Optional[str] = None,
            history: Optional[List[Dict[str, str]]] = None,
            stream: bool = True,
    ) -> Dict[str, Any]:
        """
        Deterministic planning pass:
        - Exposes only the 'make_plan' tool.
        - Forces the LLM to return a PLAN JSON (no data execution).
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a planning agent. Your job is to output a minimal JSON PLAN "
                    "that outlines the sequence of tool calls needed to satisfy the user's request. "
                    "Do NOT execute anything. Use the 'make_plan' function only."
                ),
            },
            {"role": "user", "content": user_text},
        ]

        if context:
            messages.append({"role": "system", "content": f"CONTEXT_SCHEMA:\n{context}"})

        if history:
            # keep it compact and plain text; model doesn’t need JSON here
            joined = "\n".join(
                f"{m.get('role', 'user')}: {m.get('content', '')}".strip()
                for m in history
                if m.get("content")
            )
            if joined:
                messages.append({
                    "role": "system",
                    "content": "RECENT_CHAT:\n" + joined
                })

        messages.append({"role": "user", "content": user_text})

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=[MAKE_PLAN_SPEC],
            tool_choice={"type": "function", "function": {"name": "make_plan"}},
            stream=stream,
        )

        # For streaming UIs, return the raw iterator; otherwise parse
        if stream:
            return resp  # Streamlit can iterate over tokens

        msg = resp.choices[0].message

        if msg.tool_calls:
            args = json.loads(msg.tool_calls[0].function.arguments)
            return args

        return json.loads(msg.content)

    # -------------------------
    # EXECUTION PHASE
    # -------------------------
    def stream_executor(
            self,
            user_text: str,
            plan: Optional[Dict[str, Any]] = None,
            stream: bool = True,
            tool_choice: str = "auto",
    ):
        """
        Execution pass:
        - Exposes the real data tools from TOOLS_SPECS.
        - Either lets the LLM choose tools (tool_choice='auto')
          or enforces one per plan step deterministically.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are now in execution mode. You can call the available data tools "
                    "to carry out the approved PLAN. Follow the ReAct pattern: "
                    "Thought → Action → Observation → Response. Keep outputs short."
                ),
            },
            {"role": "user", "content": user_text},
        ]

        # Optionally inject the plan as prior context
        if plan:
            messages.append(
                {
                    "role": "system",
                    "content": f"APPROVED_PLAN:\n{json.dumps(plan, indent=2)}",
                }
            )

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=TOOLS_SPECS,
            tool_choice=tool_choice,
            stream=stream,
        )

        return resp

    # -------------------------
    # REGULAR CHAT
    # -------------------------
    def chat(
            self,
            messages,
            *,
            tools=None,
            tool_choice=None,
            response_format=None,
            stream: bool = False,
    ):
        """
        Minimal one-shot chat. Returns text if non-stream; returns the stream iterator if stream=True.
        Use for small helper turns (e.g., summarizing a plan).
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
        }
        if tools is not None:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        if response_format is not None:
            kwargs["response_format"] = response_format
        if stream:
            kwargs["stream"] = True
            return self.client.chat.completions.create(**kwargs)

        resp = self.client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        return msg.content or ""

    # -------------------------
    # ROUTER
    # -------------------------
    def route_mode(self, user_text: str, specs) -> dict:
        """
        LLM router: returns {"mode": "tool_qa"|"plan", "why": "..."} as strict JSON.
        """
        specs_text = _tools_specs_to_text(specs)

        ROUTER_ROLE = """
        You must choose exactly one mode for handling the user's message.

        Modes:
        - "tool_qa": The user is asking ABOUT the tools or table/schema/columns/fields, and can be answered from tool descriptions alone.
        - "plan": The user asks to ANALYZE data, filter/sort/aggregate/plot, or otherwise requires using tools on data (planning phase).

        Rules:
        - Output STRICT JSON with keys: mode, why.
        - mode ∈ {"tool_qa","plan"}.
        - Keep "why" ≤ 120 characters.
        - Do not add any other keys. No prose outside JSON. No code.
        """

        ROUTER_JSON_SCHEMA = {
            "name": "route_mode",
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "mode": {"type": "string", "enum": ["tool_qa", "plan"]},
                    "why": {"type": "string", "maxLength": 120}
                },
                "required": ["mode", "why"]
            }
        }

        messages = [
            {"role": "system", "content": ROUTER_ROLE},
            {"role": "system", "content": f"TOOL_SPECS:\n{specs_text}"},
            {"role": "user", "content": user_text},
        ]
        out = self.chat(
            messages,
            response_format={"type": "json_schema", "json_schema": ROUTER_JSON_SCHEMA},
        )
        return json.loads(out)

    def answer_from_specs(self, system_prompt: str, specs, user_text: str) -> str:
        ctx = _tools_specs_to_text(specs)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": f"TOOL_SPECS:\n{ctx}"},
            {"role": "user", "content": user_text},
        ]
        return self.chat(messages)

    # -------------------------
    # EXECUTOR
    # -------------------------

    def _adapt_english_to_pandas(out):
        code = (out or {}).get("code", "")
        obs = {"tool": "english_to_pandas", "status": "ok", "type": "code", "length": len(code)}
        arts = {"code": code}
        return obs, arts

    _TOOL_ADAPTERS = {
        "english_to_pandas": _adapt_english_to_pandas
    }  # e.g., {"some_tool": custom_handler_func}

    def _handle_result(self, tool: str, out: Any) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Normalize any tool result into (observation, artifacts).
        observation: small JSON for the chat/trace
        artifacts: richer payload for the UI (tables, lists, values)
        """
        # # --- Debug breadcrumb ---
        # print(f"[HANDLE] tool={tool} out_type={type(out).__name__}")

        # --- Special case for english_to_pandas so UI sees 'code' directly ---
        if tool == "english_to_pandas" and isinstance(out, dict) and "code" in out:
            code = out.get("code") or ""
            # print(f"[HANDLE] english_to_pandas code_len={len(code)}")
            obs = {
                "tool": tool,
                "status": "ok",
                "type": "code",
                "length": len(code)
            }
            artifacts = {
                "code": code,
                "raw": out  # keep raw dict for inspection if needed
            }
            return obs, artifacts

        # --- Tool-specific adapter still takes precedence ---
        if tool in self._TOOL_ADAPTERS:
            return self._TOOL_ADAPTERS[tool](out)

        # --- Generic handlers ---
        if _is_dataframe(out):
            obs = {
                "tool": tool,
                "status": "ok",
                "type": "dataframe",
                "shape": [int(out.shape[0]), int(out.shape[1])],
                "columns_count": int(len(out.columns)),
            }
            artifacts = {
                "columns": list(out.columns),
                "df_head": out.head(50),  # small sample for display
                "df": out,
            }
            return obs, artifacts

        if isinstance(out, (dict, list)):
            size = len(out) if hasattr(out, "__len__") else None
            obs = {"tool": tool, "status": "ok", "type": "json", "size": size}
            artifacts = {"value": out}
            return obs, artifacts

        if isinstance(out, (str, bytes)):
            obs = {"tool": tool, "status": "ok", "type": "text", "length": len(out)}
            artifacts = {"value": out[:2000]}  # cap
            return obs, artifacts

        if isinstance(out, (int, float, bool)) or out is None:
            obs = {"tool": tool, "status": "ok", "type": "scalar"}
            artifacts = {"value": out}
            return obs, artifacts

        # --- Fallback ---
        obs = {"tool": tool, "status": "ok", "type": "unknown"}
        artifacts = {"repr": repr(out)}
        return obs, artifacts

    def execute_plan_locally(self, plan: dict) -> dict:
        """
        Deterministically execute a PLAN (no LLM). Generic across tools.
        Returns: {"observations": [...], "artifacts": {"step_0": {...}, ...}}
        """
        if not isinstance(plan, dict) or "steps" not in plan or not plan["steps"]:
            raise ValueError("Invalid PLAN: missing non-empty 'steps'.")

        observations, artifacts_by_step = [], {}
        for i, step in enumerate(plan["steps"]):
            tool = step.get("tool")
            args = step.get("args", {}) or {}

            # # 👇 DEBUG 1: see each step coming in
            # print(f"[EXEC] step={i} tool={tool} args={args}")

            if tool not in TOOL_REGISTRY:
                observations.append({
                    "tool": tool, "status": "skipped", "reason": "Unknown tool"
                })
                continue

            fn = TOOL_REGISTRY[tool]
            try:
                sig = inspect.signature(fn)
                call_kwargs = dict(args)
                if "backend" in sig.parameters:
                    call_kwargs["backend"] = self

                # # 👇 DEBUG 2: show what kwargs we actually pass (backend/model injection)
                # print(f"[EXEC] step={i} call_kwargs_keys={list(call_kwargs.keys())}")
                # print(f"[EXEC] step={i} fn={getattr(fn, '__name__', str(fn))}")
                out = fn(**call_kwargs)

                # # 👇 DEBUG 3: what did the tool return?
                # typ = type(out).__name__
                # preview = (str(out)[:200] + "…") if isinstance(out, (dict, list, str)) else repr(out)
                # print(f"[EXEC] step={i} raw_out_type={typ} preview={preview}")

                obs, arts = self._handle_result(tool, out)
                observations.append(obs)
                artifacts_by_step[f"step_{i}"] = arts

                # # 👇 DEBUG 4: what did we store for the UI?
                # print(f"[EXEC] step={i} obs_type={obs.get('type')} arts_keys={list(arts.keys())}")


            except Exception as e:
                observations.append({
                    "tool": tool, "status": "error", "error": str(e)
                })

        return {"observations": observations, "artifacts": artifacts_by_step}

