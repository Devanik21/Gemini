import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
import os
import json
import time
from datetime import datetime

# Page settings



# Gradient-styled title using HTML
gradient_title = """
<style>
@keyframes gradient {
  0% {background-position: 0%;}
  100% {background-position: 100%;}
}
.animated-gradient {
  font-size: 64px;
  font-weight: bold;
  text-align: center;
  background: linear-gradient(90deg, #4f46e5, #ec4899, #4f46e5);
  background-size: 200%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: gradient 3s infinite linear;
  font-family: "Segoe UI", sans-serif;
}
</style>

<h1 class='animated-gradient'> Gemini</h1>
"""
st.markdown(gradient_title, unsafe_allow_html=True)


st.markdown(gradient_title, unsafe_allow_html=True)


# Blurry Gradient Background Style
# Add this after st.set_page_config(...)


name = st.text_input("Please enter your name", value=" ")

if name.strip():
    st.markdown(f"""
        <style>
        @keyframes gradientShift {{
            0% {{ background-position: 0%; }}
            100% {{ background-position: 100%; }}
        }}
        .animated-greeting {{
            font-size: 36px;
            font-weight: bold;
            text-align: center;
            background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899);
            background-size: 300%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: gradientShift 4s linear infinite;
            font-family: "Segoe UI", sans-serif;
            margin-top: 10px;
        }}
        </style>

        <h3 class='animated-greeting'>Hello, {name}, ready to explore ideas? ⚡</h3>
    """, unsafe_allow_html=True)


# Initialize session data for settings and themes
if "settings" not in st.session_state:
    st.session_state.settings = {
        "temperature": 0.7,
        "top_k": 40,
        "top_p": 0.95,
        "max_tokens": 8192
    }

if "theme" not in st.session_state:
    st.session_state.theme = "light"

if "favorites" not in st.session_state:
    st.session_state.favorites = []

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = {}

# Name input


# Theme toggle function
def toggle_theme():
    st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
    # Apply theme changes
    if st.session_state.theme == "dark":
        st.markdown("""
        <style>
        .main {background-color: #0e1117; color: #ffffff;}
        .sidebar .sidebar-content {background-color: #262730; color: #ffffff;}
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
        .main {background-color: #ffffff; color: #31333F;}
        .sidebar .sidebar-content {background-color: #f0f2f6; color: #31333F;}
        </style>
        """, unsafe_allow_html=True)

# Sidebar - API, Chat Mode, Clear, Settings
with st.sidebar:
    st.header("🔐 Gemini API Settings")
    api_key = st.text_input("Enter your Gemini API key:", type="password")

    st.markdown("---")
    chat_mode = st.selectbox(
        "🧠 Select Chat Mode",
        ["Normal", "Deep Research", "Creative", "Explain Like I'm 5", "Code Helper", 
         "Debate Mode", "Translation Helper", "Summarizer"]
    )

    st.markdown("---")
    # New feature: Save/Load conversation
    st.header("💾 Conversation Management")
    save_name = st.text_input("Conversation name:")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 Save Chat"):
            if save_name and len(st.session_state.messages) > 0:
                st.session_state.conversation_history[save_name] = {
                    "messages": st.session_state.messages.copy(),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                st.success(f"Saved as '{save_name}'")
            else:
                st.error("Please enter a name and ensure chat has messages")
    
    with col2:
        if st.button("🧹 Clear Chat"):
            st.session_state.messages = []
            if "chat" in st.session_state:
                del st.session_state.chat
            st.success("Chat history cleared!")

    # Load saved conversation
    if st.session_state.conversation_history:
        st.markdown("---")
        st.subheader("📚 Saved Conversations")
        selected_chat = st.selectbox("Select a conversation:", 
                                    options=list(st.session_state.conversation_history.keys()),
                                    format_func=lambda x: f"{x} ({st.session_state.conversation_history[x]['timestamp']})")
        
        if st.button("📂 Load Selected Chat"):
            if selected_chat:
                st.session_state.messages = st.session_state.conversation_history[selected_chat]["messages"].copy()
                st.success(f"Loaded conversation: {selected_chat}")
                st.rerun()

    st.markdown("---")
    
    # Export options
    st.header("📤 Export Options")
    export_pdf = st.button("Export Last Response to PDF")
    export_json = st.button("Export All as JSON")
    
    # Theme toggle
    st.markdown("---")
    st.header("🎨 Appearance")
    if st.button("Toggle Dark/Light Mode"):
        toggle_theme()
    
    # Advanced model settings
    st.markdown("---")
    st.header("⚙️ Advanced Settings")
    with st.expander("Model Parameters"):
        st.session_state.settings["temperature"] = st.slider(
            "Temperature", min_value=0.0, max_value=1.0, 
            value=st.session_state.settings["temperature"], step=0.1,
            help="Higher values make output more random, lower values more deterministic"
        )
        st.session_state.settings["top_p"] = st.slider(
            "Top P", min_value=0.0, max_value=1.0, 
            value=st.session_state.settings["top_p"], step=0.05,
            help="Controls diversity via nucleus sampling"
        )
        st.session_state.settings["max_tokens"] = st.slider(
            "Max Output Tokens", min_value=256, max_value=8192, 
            value=st.session_state.settings["max_tokens"], step=256,
            help="Maximum length of generated text"
        )
    
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
        generation_config={
            "max_output_tokens": st.session_state.settings["max_tokens"],
            "temperature": st.session_state.settings["temperature"],
            "top_p": st.session_state.settings["top_p"],
            "top_k": st.session_state.settings["top_k"]
        }
    ).start_chat(history=[])

# Show chat history
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # Add favorite button for assistant messages
        if msg["role"] == "assistant":
            if st.button("⭐ Favorite", key=f"fav_{i}"):
                if msg["content"] not in [f["content"] for f in st.session_state.favorites]:
                    st.session_state.favorites.append({
                        "content": msg["content"],
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "mode": chat_mode
                    })
                    st.success("Added to favorites!")
                    time.sleep(1)
                    st.rerun()

# Show favorites in a collapsed section
if st.session_state.favorites:
    with st.expander("⭐ Your Favorites"):
        for i, fav in enumerate(st.session_state.favorites):
            st.markdown(f"**{i+1}. [{fav['mode']}] - {fav['timestamp']}**")
            st.markdown(fav["content"])
            if st.button("Remove", key=f"remove_fav_{i}"):
                st.session_state.favorites.pop(i)
                st.success("Removed from favorites!")
                time.sleep(1)
                st.rerun()
            st.markdown("---")

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

# Export to JSON Function
def export_to_json(chat_history, filename="gemini_chat_export.json"):
    export_data = {
        "messages": chat_history,
        "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "chat_mode": chat_mode
    }
    
    with open(filename, "w") as f:
        json.dump(export_data, f, indent=4)
    
    return filename

# Chat input
if api_key:
    # Add a typing effect toggle
    typing_effect = st.checkbox("Enable typing effect for responses", value=False)
    
    # Add language selection for Translation Mode
    if chat_mode == "Translation Helper":
        target_language = st.selectbox(
            "Translate to:", 
            ["Spanish", "French", "German", "Italian", "Portuguese", "Russian", "Japanese", "Chinese", "Arabic", "Hindi"]
        )
    
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
            system_prompt = f"Explain this like I'm 5 years old: {user_prompt}"
        elif chat_mode == "Code Helper":
            system_prompt = f"You are a coding assistant. Explain, debug, or generate code for this prompt: {user_prompt}"
        elif chat_mode == "Debate Mode":
            system_prompt = f"""
You are a balanced debate assistant. For the topic provided:
1. Present a strong case for the position (Pro)
2. Present a strong case against the position (Con)
3. Analyze the strongest points from both sides
4. Provide a balanced conclusion

Topic: {user_prompt}
"""
        elif chat_mode == "Translation Helper":
            system_prompt = f"Translate the following text to {target_language}. Provide both the translation and any cultural notes or context that might be helpful: {user_prompt}"
        elif chat_mode == "Summarizer":
            system_prompt = f"""
Summarize the following text in three different ways:
1. Executive summary (2-3 sentences)
2. Bullet point summary (5-7 key points)
3. Detailed summary (3-4 paragraphs)

Text to summarize:
\"\"\"{user_prompt}\"\"\"
"""
        else:
            system_prompt = user_prompt

        # Show a spinner while loading
        with st.spinner("Gemini is thinking..."):
            # Update model parameters before sending
            if "chat" in st.session_state:
                # Get response from Gemini
                response = st.session_state.chat.send_message(system_prompt)
                reply = response.text

                # Typing effect simulation
                if typing_effect:
                    with st.chat_message("assistant"):
                        message_placeholder = st.empty()
                        full_response = ""
                        # Simulate typing with chunks of text
                        for chunk in reply.split():
                            full_response += chunk + " "
                            message_placeholder.markdown(full_response + "▌")
                            time.sleep(0.05)  # Adjust typing speed
                        message_placeholder.markdown(reply)
                else:
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

# Export all conversation to JSON
if export_json:
    if st.session_state.messages:
        filename = export_to_json(st.session_state.messages)
        with open(filename, "rb") as f:
            st.download_button(
                label="📄 Download JSON",
                data=f,
                file_name=filename,
                mime="application/json"
            )
    else:
        st.warning("No conversation available to export yet.")

# Add feedback mechanism


# Display system status in footer
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.caption(f"Theme: {st.session_state.theme.capitalize()}")
with col2:
    st.caption(f"Mode: {chat_mode}")
with col3:
    st.caption(f"Temperature: {st.session_state.settings['temperature']}")
