import streamlit as st
import google.generativeai as genai

# Page settings
st.set_page_config(page_title="Gemini", layout="wide", page_icon="💎")
st.title(" 💎 Gemini ")

# Name input
name = st.text_input("Please enter your name ", value=" ")

if name.strip():
    st.markdown(f"### Hello {name},  let's explore together 💫 ")

# Sidebar
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

    # Deep Research Toggle
    st.markdown("---")
    deep_research = st.checkbox("🔍 Enable Deep Research Mode", value=False)

# Initialize chat and history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat" not in st.session_state and api_key:
    st.session_state.chat = genai.GenerativeModel(
        model_name="gemini-2.0-pro",  # Use the full token limit model
        generation_config={"max_output_tokens": 8192}
    ).start_chat(history=[])

# Display past messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Main chat input
if api_key:
    user_prompt = st.chat_input("Type your message here 💬")

    if user_prompt:
        st.chat_message("user").markdown(user_prompt)
        st.session_state.messages.append({"role": "user", "content": user_prompt})

        # Deep Research Mode Prompting
        if deep_research:
            research_prompt = f"""
You are a deeply knowledgeable, high-level research assistant with expertise in technical, scientific, and academic writing.

You are tasked with generating an in-depth, structured response of up to 8000 words (8192 tokens). The output should feel like a high-quality research article or whitepaper, suitable for university-level work, academic publication, or investor/industry analysis.

Follow these guidelines:

---

🔍 Objective:
Answer the user’s query with academic rigor, depth, and completeness.

---

✍️ Structure:

1. Executive Summary  
2. Introduction  
3. Historical Context  
4. Core Concepts  
5. Current State  
6. Challenges & Debates  
7. Applications & Use Cases  
8. Comparative Analysis  
9. Future Outlook  
10. Conclusion  
11. References (Optional)

---

📑 Formatting:
- Markdown-friendly
- Use headings, bullets, code blocks (if applicable)
- Authoritative tone
- No token/word restriction; go as deep as needed

---

🗨️ Query:
\"\"\"{user_prompt}\"\"\"

Begin now.
"""
            response = st.session_state.chat.send_message(research_prompt)
        else:
            response = st.session_state.chat.send_message(user_prompt)

        reply = response.text
        st.chat_message("assistant").markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})
