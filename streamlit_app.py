import streamlit as st
from llm_clients.openai_backend import OpenAIChatBackend

st.set_page_config(page_title="AI Senior Data Analyst", page_icon="💬", layout="centered")

# ---------- Backend setup ----------
@st.cache_resource
def get_backend() -> OpenAIChatBackend:
    """Cache a single backend instance per session."""
    return OpenAIChatBackend()

backend = get_backend()

# ---------- Session state init ----------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are a helpful Senior Data Analyst."},
        {"role": "assistant", "content": "Hi 👋 I am your AI Senior Data Analyst. How can I help today?"},
    ]

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("### Session")
    st.write(f"Total messages: {len(st.session_state.messages) - 1}")  # exclude system message
    STREAMING = st.toggle("Stream responses", value=True)
    if st.button("Clear chat"):
        st.session_state.messages = [
            {"role": "system", "content": "You are a helpful Senior Data Analyst."},
            {"role": "assistant", "content": "Hi 👋 I am your AI Senior Data Analyst. How can I help today?"},
        ]
        st.rerun()

# ---------- Render chat history ----------
for msg in st.session_state.messages:
    if msg["role"] == "system":
        continue
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------- Chat input ----------
if prompt := st.chat_input("Type your message"):
    # 1️⃣ Append user message
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2️⃣ Render user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)

    # 3️⃣ Generate assistant reply (streaming or full)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            if STREAMING:
                reply_text = st.write_stream(backend.stream(st.session_state.messages))
#             else:
#                 reply_text = backend.chat(st.session_state.messages)
#                 st.markdown(reply_text)
#
#     # 4️⃣ Append assistant message
#     st.session_state.messages.append({"role": "assistant", "content": reply_text})