"""
💬 Chat — Talk to your AI health coach.
Uses the LLM Agent with Groq native tool calling.
"""

import streamlit as st
from database import crud
from core.agent import run as agent_run

st.set_page_config(page_title="Chat - HealthyBot", page_icon="💬", layout="wide")
st.title("💬 Chat with HealthyBot")
st.markdown("Talk naturally — log meals, exercise, habits, or ask for advice!")
st.markdown("---")


user = crud.get_first_user()

if not user:
    st.warning("Please complete your profile in **⚙️ Settings** first!")
    st.stop()

# Initialize chat history in session state
if "messages" not in st.session_state:
    history = crud.get_chat_history(user["id"], limit=50)
    st.session_state.messages = [
        {"role": m["role"], "content": m["content"]} for m in history
    ]

    if not st.session_state.messages:
        st.session_state.messages.append({
            "role": "assistant",
            "content": (
                f"Hey {user.get('name', 'there')}! 👋 I'm your health buddy.\n\n"
                "Just talk to me naturally — tell me what you ate, how you worked out, "
                "about your sleep and habits. I'll track everything and give you tips!\n\n"
                "**Try saying things like:**\n"
                "• \"I had 2 rotis and dal for lunch\"\n"
                "• \"Did 30 min running today\"\n"
                "• \"Slept 6 hours, 3 hours screen time\"\n"
                "• \"What did I eat yesterday?\"\n"
                "• \"Am I making progress?\"\n"
                "• \"Suggest a workout\""
            )
        })

# Display chat history
for msg in st.session_state.messages:
    avatar = "🤖" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Type your message..."):
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    crud.save_chat_message(user["id"], "user", prompt)

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Thinking..."):
            # Pass chat history for memory
            response = agent_run(
                user_id=user["id"],
                message=prompt,
                chat_history=st.session_state.messages[:-1],  # exclude current msg
            )
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
    crud.save_chat_message(user["id"], "assistant", response)
