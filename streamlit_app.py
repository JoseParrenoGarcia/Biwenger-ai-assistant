import json
import streamlit as st
from llm_clients.openai_backend import OpenAIChatBackend
from llm_clients.roles_and_prompts import (
    PLANNER_ROLE,
    PLAN_SUMMARIZER_ROLE,
    TOOL_KNOWLEDGE_ROLE)

from tools.registry import get_tools
from tools.specs import MAKE_PLAN_SPEC

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
                            # Direct answer from specs (no planning)
                            english = backend.answer_from_specs(
                                system_prompt=TOOL_KNOWLEDGE_ROLE,
                                specs=specs_for_router,
                                user_text=prompt,
                            )
                            st.markdown(english)
                            st.session_state.messages.append({"role": "assistant", "content": english})

                        elif mode == "plan":
                            with st.spinner("Planning…"):
                                plan_raw = backend.stream_planner(user_text=prompt, context=None, stream=False)
                                st.session_state.plan = plan_raw  # right panel will render it

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
        with st.container(border=True):
            st.subheader("Execution Results")
            arts = exec_out.get("artifacts", {})
            first = arts.get("step_0", {})

            if "df_head" in first:
                st.markdown("**Data preview (top 50)**")
                st.dataframe(first["df_head"], use_container_width=True)

            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown("**Observations**")
                st.json(exec_out.get("observations", []))


            with col2:
                if "columns" in first:
                    st.markdown("**Columns**")
                    st.write(first["columns"])



            # if "value" in first and "df_head" not in first:
            #     st.markdown("**Value**")
            #     st.write(first["value"])