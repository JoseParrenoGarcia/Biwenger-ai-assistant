# app/llm/openai_backend.py
from __future__ import annotations
from typing import TypedDict, Optional, Dict, Any
from openai import OpenAI
import tomllib
import json
from pathlib import Path

from tools.registry import MAKE_PLAN_SPEC, TOOLS_SPECS

# ---------- Types / Interface ----------
class Message(TypedDict):
    role: str
    content: str
    name: Optional[str]  # for tool role messages
    tool_call_id: Optional[str]

# ---------- Config helpers ----------
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
