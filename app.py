import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
import os

# Page settings
st.set_page_config(page_title="Gemini Pro", layout="wide", page_icon="💎")
st.title(" 💎 Gemini Pro – Multi-Mode Chat Assistant")

# Name input
name = st.text_input("Please enter your name", value=" ")
if name.strip():
    st.markdown(f"### Hello {name}, ready to explore ideas? ⚡")

# Sidebar - API, Chat Mode, Clear
with st.sidebar:
    st.header("🔐 Gemini API Settings")
    api_key = st.text_input("Enter your Gemini API key:", type="password")

    st.markdown("---")
    chat_mode = st.selectbox(
        "🧠 Select Chat Mode",
        ["Normal", "Deep Research", "Creative", "Explain Like I'm 5", "Code Helper"]
    )

    st.markdown("---")
    export_pdf = st.button("📤 Export Last Response to PDF")
    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []
        if "chat" in st.session_state:
            del st.session_state.chat
        st.success("Chat history cleared!")

    if api_key:
        genai.configure(api_key=api_key)
        st.success("API key set successfully!", icon="✅")
    else:
        st.warning("Enter Gemini API key to begin", icon="⚠️")

# Initialize session
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat" not in st.session_state and api_key:
    st.session_state.chat = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        generation_config={"max_output_tokens": 8192}
    ).start_chat(history=[])

# Show chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# PDF Export Function
def export_to_pdf(text, filename="gemini_response.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)

    for line in text.split("\n"):
        pdf.multi_cell(0, 10, line)

    pdf.output(filename)
    return filename

# Chat input
if api_key:
    user_prompt = st.chat_input("Ask anything 💬")

    if user_prompt:
        st.chat_message("user").markdown(user_prompt)
        st.session_state.messages.append({"role": "user", "content": user_prompt})

        # Prepare system prompt for different modes
        if chat_mode == "Deep Research":
            system_prompt = f"""
You are a high-level research assistant writing in-depth academic responses. 
Structure the output as a formal article (~8000 tokens) with:
1. Executive Summary
2. Introduction
3. History & Evolution
4. Concepts & Frameworks
5. Current State
6. Challenges
7. Applications
8. Comparisons
9. Future Outlook
10. Conclusion
11. References (Optional)

Query:
\"\"\"{user_prompt}\"\"\"
"""
        elif chat_mode == "Creative":
            system_prompt = f"You are a wildly creative storyteller and ideator. Think like a novelist or futurist. Respond creatively to: {user_prompt}"
        elif chat_mode == "Explain Like I'm 5":
            system_prompt = f"Explain this like I’m 5 years old: {user_prompt}"
        elif chat_mode == "Code Helper":
            system_prompt = f"You are a coding assistant. Explain, debug, or generate code for this prompt: {user_prompt}"
        else:
            system_prompt = user_prompt

        # Get response from Gemini
        response = st.session_state.chat.send_message(system_prompt)
        reply = response.text

        st.chat_message("assistant").markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

        # Save last reply to export
        st.session_state.last_reply = reply

# Export last response to PDF
if export_pdf:
    if "last_reply" in st.session_state:
        filename = export_to_pdf(st.session_state.last_reply)
        with open(filename, "rb") as f:
            st.download_button(
                label="📄 Download PDF",
                data=f,
                file_name=filename,
                mime="application/pdf"
            )
    else:
        st.warning("No reply available to export yet.")
