import streamlit as st
import google.generativeai as genai

# Configure the Streamlit page
st.set_page_config(page_title="Gemini Chat Clone", page_icon="🤖", layout="wide")

# Sidebar for API Key
with st.sidebar:
    st.markdown("### 🔑 API Configuration")
    api_key = st.text_input("Enter Google Gemini API Key:", type="password")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state["messages"] = []

st.title("🤖 Gemini Chat Clone")
st.write("Chat with AI continuously without losing context!")

# Display chat history
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
if user_input := st.chat_input("Type your message..."):
    if not api_key:
        st.warning("⚠️ Please enter a valid Google Gemini API Key in the sidebar.")
    else:
        try:
            # Configure API
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.0-flash")  # Using Pro version for better conversation handling
            
            # Add user message to history
            st.session_state["messages"].append({"role": "user", "content": user_input})
            
            # Display user message instantly
            with st.chat_message("user"):
                st.markdown(user_input)
            
            # Generate AI response
            with st.spinner("Thinking..."):
                response = model.generate_content(user_input)
            
            # Add AI response to history
            ai_response = response.text.strip()
            st.session_state["messages"].append({"role": "assistant", "content": ai_response})
            
            # Display AI response
            with st.chat_message("assistant"):
                st.markdown(ai_response)
        
        except Exception as e:
            st.error(f"❌ Error: {e}")
