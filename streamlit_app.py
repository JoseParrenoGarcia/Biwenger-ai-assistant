import json
import streamlit as st
from llm_clients.openai_backend import OpenAIChatBackend
from llm_clients.roles_and_prompts import PLANNER_ROLE, PLAN_SUMMARIZER_ROLE, PLAN_SUMMARIZER_ROLE, TOOL_KNOWLEDGE_ROLE

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
    # Use a tiny model, temp=0, and non-stream for determinism
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

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("### Phase")
    st.caption("Currently: **Planning only** (no tool execution)")
    STREAMING = st.toggle("Stream responses", value=False)
    st.divider()
    if st.button("Clear session"):
        st.session_state.clear()
        st.rerun()

# ---------- Chat history ----------
left, right = st.columns([0.35, 0.65])
with left:
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
                            # english = backend.summarize_plan(plan_raw, system_prompt=PLAN_SUMMARIZER_ROLE)
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

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Approve plan ✅", use_container_width=True):
                    st.session_state.approved_plan = st.session_state.plan
                    st.success("Plan approved. You can now enable the execution phase (coming next).")

            with col2:
                if st.button("Discard plan ❌", use_container_width=True):
                    st.session_state.plan = None
                    st.session_state.approved_plan = None
                    st.info("Plan discarded. Enter a new request above.")

    # ---------- Approved plan persistence ----------
    if st.session_state.plan and st.session_state.approved_plan:
        with st.container(border=True):
            st.subheader("Execution Phase (coming soon)")
