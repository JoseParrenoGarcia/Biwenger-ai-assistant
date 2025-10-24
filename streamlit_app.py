import json
import streamlit as st
from llm_clients.openai_backend import OpenAIChatBackend
from llm_clients.roles_and_prompts import PLANNER_ROLE
from tools.registry import get_tools
from tools.specs import MAKE_PLAN_SPEC

st.set_page_config(page_title="AI Senior Data Analyst", page_icon="💬", layout="centered")

# ---------- Backend setup ----------
@st.cache_resource
def get_backend() -> OpenAIChatBackend:
    """Cache a single backend instance per session."""
    return OpenAIChatBackend()

backend = get_backend()

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

    # Show the planner tool definition for transparency
    with st.expander("Planner tool spec (make_plan)"):
        st.json(MAKE_PLAN_SPEC, expanded=False)

# ---------- Chat history ----------
for msg in st.session_state.messages:
    if msg["role"] == "system":
        continue
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------- Chat input ----------
if prompt := st.chat_input("Ask for an analysis or data task (planning mode)..."):
    # 1️⃣ Append user message
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2️⃣ Render user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)

    # 3️⃣ Generate plan (planner phase)
    with st.chat_message("assistant"):
        with st.spinner("Planning..."):
            try:
                # Call backend planner
                plan = backend.stream_planner(
                    user_text=prompt,
                    context=None,
                    stream=False,          # keep deterministic JSON
                )
                # Parse tool arguments safely
                if isinstance(plan, str):
                    plan = json.loads(plan)
                elif hasattr(plan, "arguments"):
                    plan = json.loads(plan.arguments)

                # Validate and render
                st.session_state.plan = plan
                st.markdown("### 🧠 Proposed Plan")
                st.json(plan, expanded=True)
                reply_text = "Here’s a minimal JSON plan. You can review or approve it below."
                st.markdown(reply_text)

            except Exception as e:
                reply_text = f"Planner error: {type(e).__name__}: {e}"
                st.error(reply_text)

    # 4️⃣ Append assistant message
    st.session_state.messages.append({"role": "assistant", "content": reply_text})

# ---------- Display plan + actions ----------
if st.session_state.plan:
    st.divider()
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
            st.info("Plan discarded. Enter a new request above.")

# ---------- Approved plan persistence ----------
if st.session_state.approved_plan:
    st.divider()
    st.subheader("Approved Plan (saved)")
    st.json(st.session_state.approved_plan)
    st.info("Execution phase is disabled for now — this plan will be passed to the executor once implemented.")
