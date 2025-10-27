import json
import streamlit as st
from llm_clients.openai_backend import OpenAIChatBackend
from llm_clients.roles_and_prompts import (
    PLANNER_ROLE,
    PLAN_SUMMARIZER_ROLE,
    TOOL_KNOWLEDGE_ROLE)

from tools.registry import get_tools
from tools.execute_pandas import execute_pandas_local

st.set_page_config(page_title="AI Senior Data Analyst", page_icon="💬", layout="wide")

# ---------- Backend setup ----------
@st.cache_resource
def get_backend() -> OpenAIChatBackend:
    """Cache a single backend instance per session."""
    return OpenAIChatBackend()

backend = get_backend()

# ---------- Helper functions ----------
def summarize_plan_with_llm(backend, plan: dict) -> str:
    messages = [
        {"role": "system", "content": PLAN_SUMMARIZER_ROLE},
        {"role": "user", "content": "PLAN:\n" + json.dumps(plan, ensure_ascii=False, indent=2)}
    ]
    return backend.chat(messages)

# ---------- Session state ----------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": PLANNER_ROLE},
        {"role": "assistant", "content": "Hi 👋 I’m your AI Senior Data Analyst (planning mode). What analysis do you have in mind?"},
    ]

if "plan" not in st.session_state:
    st.session_state.plan = None

if "approved_plan" not in st.session_state:
    st.session_state.approved_plan = None

if "exec_out" not in st.session_state:
    st.session_state.exec_out = {}

# ---------- Chat history ----------
col1, col2, col3 = st.columns([1, 1, 8])
with col1:
    STREAMING = st.toggle("Stream responses", value=False)

with col2:
    if st.button("Clear session"):
        st.session_state.clear()
        st.rerun()

left, right = st.columns([0.35, 0.65])
with left:
    with st.container(border=True):
        # --- Chat history (no system messages) ---
        for msg in st.session_state.messages:
            if msg["role"] == "system":
                continue
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # ---------- Chat input ----------
        if prompt := st.chat_input("I will propose an action plan before proceeding."):
            # 1️⃣ Append user message
            st.session_state.messages.append({"role": "user", "content": prompt})

            # 2️⃣ Render user message immediately
            with st.chat_message("user"):
                st.markdown(prompt)

            # 🔀 LLM router decides: tool_qa vs plan
            with st.chat_message("assistant"):
                with st.spinner("Routing…"):
                    try:
                        specs_for_router = get_tools("executor")  # the real tool specs (descriptions)
                        decision = backend.route_mode(prompt, specs_for_router)
                        mode = decision["mode"]

                        if mode == "tool_qa":
                            with st.spinner("Summarising answer…"):
                                english = backend.answer_from_specs(
                                    system_prompt=TOOL_KNOWLEDGE_ROLE,
                                    specs=specs_for_router,
                                    user_text=prompt,
                                )
                                st.markdown(english)
                                st.session_state.messages.append({"role": "assistant", "content": english})

                        elif mode == "plan":
                            with st.spinner("Planning…"):
                                history = [
                                    m for m in st.session_state.messages
                                    if m["role"] in ("user", "assistant")
                                ][-6:]

                                plan_raw = backend.stream_planner(user_text=prompt, context=None, history=history, stream=False)
                                st.session_state.plan = plan_raw

                                # Short English gloss of the plan
                                english = summarize_plan_with_llm(backend, plan_raw)
                                st.markdown(english)
                                st.session_state.messages.append({"role": "assistant", "content": english})

                        else:
                            pass


                    except:
                        pass

# ---------- Display plan + actions ----------
with right:
    with st.container(border=True):
        if st.session_state.plan:
            st.subheader("Proposed Plan (latest)")
            st.json(st.session_state.plan)

            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if st.button("Approve plan ✅", use_container_width=True):
                    st.session_state.approved_plan = st.session_state.plan
                    st.success("Plan approved.")

            with col2:
                if st.button("Discard plan ❌", use_container_width=True):
                    st.session_state.plan = None
                    st.session_state.approved_plan = None
                    st.session_state.exec_out = None
                    st.info("Plan discarded. Enter a new request above.")

            with col3:
                # Only enabled once approved
                disabled = not bool(st.session_state.get("approved_plan"))
                if st.button("Execute plan ▶️", use_container_width=True, disabled=disabled):
                    try:
                        with st.spinner("Executing plan…"):
                            # Ensure plan is a dict (if not already)
                            plan_like = st.session_state.approved_plan
                            exec_out = backend.execute_plan_locally(plan_like)  # <-- sets observations/artifacts
                            st.session_state.exec_out = exec_out
                            st.success("Execution complete.")
                    except Exception as e:
                        st.session_state.exec_out = {"observations": [], "artifacts": {}, "debug": {"error": str(e)}}
                        st.error(f"Execution error: {e}")

    # ---------- Execution ----------
    exec_out = st.session_state.get("exec_out")
    if exec_out:
        arts = exec_out.get("artifacts", {})
        step0 = arts.get("step_0", {})
        step1 = arts.get("step_1", {})

        # existing panels for preview + code ...
        with st.container(border=True):
            st.subheader("Generated pandas code")
            code = step1.get("code") or ((step1.get("value") or {}).get("code") if isinstance(step1.get("value"), dict) else None)
            if code:
                st.code(code, language="python")
            else:
                st.caption("No code artifact found for step_1.")
                st.json(step1)

        # ---- Local deterministic execution (no LLM, no planner step) ----
        df_in = step0.get("df")
        if df_in is not None and code:
            if st.button("Run pandas code safely ▶️", use_container_width=True):
                try:
                    with st.spinner("Executing pandas locally…"):
                        df_out = execute_pandas_local(code, df_in)
                        st.success(f"Done. Rows: {len(df_out)} · Cols: {len(df_out.columns)}")
                        st.dataframe(df_out.head(50), use_container_width=True)
                except Exception as e:
                    st.error(f"Pandas execution error: {e}")
        else:
            st.caption("Load data and generate code first to enable execution.")