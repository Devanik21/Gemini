
'''
Replace this:(for file upload)(not working)


if api_key:
    user_prompt = st.chat_input("Type your message here 💬")

    
With this:



if api_key:
    col1, col2 = st.columns([0.1, 0.9])

    with col1:
        uploaded_file = st.file_uploader(" ", type=["pdf"], label_visibility="collapsed")
        if uploaded_file:
            st.toast("📄 PDF uploaded! (But I'm not reading it yet~ 💖)", icon="📎")

    with col2:
        user_prompt = st.chat_input("Type your message here 💬")
        if user_prompt:
            # Show user message
            st.chat_message("user").markdown(user_prompt)
            st.session_state.messages.append({"role": "user", "content": user_prompt})

            # Send to Gemini
            response = st.session_state.chat.send_message(user_prompt)
            reply = response.text

            # Show bot response
            st.chat_message("assistant").markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
'''



import streamlit as st
import google.generativeai as genai

import streamlit as st
from datetime import datetime

# Page settings
st.set_page_config(page_title="Gemini", layout="wide", page_icon="💎")
st.title(" 💎 Gemini ")

# Name input
name = st.text_input("Hey explorer! What's your name? 💬", value="Prince")

# Time-based greeting
def get_greeting():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good morning 🌅"
    elif 12 <= hour < 17:
        return "Good afternoon ☀️"
    elif 17 <= hour < 21:
        return "Good evening 🌇"
    else:
        return "Good night 🌙"

# Show the greeting
if name:
    greeting = get_greeting()
    st.markdown(f"### {greeting}, **{name}**! 💖 Hope you're having a wonderful day! ")


# Sidebar - API Key Input and Clear Button
with st.sidebar:
    st.header("🔐 Gemini API Settings")
    api_key = st.text_input("Enter your Gemini API key:", type="password")

    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []
        if "chat" in st.session_state:
            del st.session_state.chat
        st.success("Chat history cleared!")

    if api_key:
        genai.configure(api_key=api_key)
        st.success("API key set successfully!", icon="✅")
    else:
        st.warning("Please enter your Gemini API key to start chatting", icon="⚠️")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat" not in st.session_state and api_key:
    st.session_state.chat = genai.GenerativeModel("gemini-2.0-flash").start_chat(history=[])

# Display previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Input
if api_key:
    user_prompt = st.chat_input("Type your message here 💬")
    if user_prompt:
        # Show user message
        st.chat_message("user").markdown(user_prompt)
        st.session_state.messages.append({"role": "user", "content": user_prompt})

        # Send to Gemini
        response = st.session_state.chat.send_message(user_prompt)
        reply = response.text

        # Show bot response
        st.chat_message("assistant").markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})







