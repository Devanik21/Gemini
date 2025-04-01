import streamlit as st
import os
import google.generativeai as genai
import tempfile
import base64
import mimetypes
from io import BytesIO

# Page configuration
st.set_page_config(page_title="File Chat Assistant", layout="wide")

# Initialize session state variables
if "chat_context" not in st.session_state:
    st.session_state.chat_context = []
if "display_messages" not in st.session_state:
    st.session_state.display_messages = []
if "current_file" not in st.session_state:
    st.session_state.current_file = None
if "file_content" not in st.session_state:
    st.session_state.file_content = None
if "file_type" not in st.session_state:
    st.session_state.file_type = None

# Function to get file content as base64
def get_file_content(uploaded_file):
    if uploaded_file is not None:
        return BytesIO(uploaded_file.getvalue())
    return None

# Function to encode file for API
def encode_file(file_content, mime_type):
    if file_content is not None:
        file_bytes = file_content.read()
        encoded = base64.b64encode(file_bytes).decode('utf-8')
        return {"mime_type": mime_type, "data": encoded}
    return None

# Function to process text with Gemini API
def process_with_gemini(prompt, file_data=None, model_name="gemini-1.5-pro"):
    try:
        genai.configure(api_key=st.session_state.api_key)
        model = genai.GenerativeModel(model_name)
        
        # Create message content
        content = []
        
        # Add text prompt
        content.append({"role": "user", "parts": [{"text": prompt}]})
        
        # Add file if provided
        if file_data:
            content[0]["parts"].append(file_data)
        
        # Get chat based on history
        chat = model.start_chat(history=st.session_state.chat_context)
        
        # Generate response
        response = chat.send_message(content[0]["parts"])
        
        # Update chat context
        st.session_state.chat_context = chat.history
        
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# Sidebar configuration
with st.sidebar:
    st.title("🤖 File Chat Assistant")
    st.markdown("---")
    
    st.markdown("## 🔑 API Configuration")
    api_key = st.text_input("Enter Google Gemini API Key:", type="password", 
                          help="Get your key from [Google AI Studio](https://aistudio.google.com/app/apikey)")
    
    if api_key:
        st.session_state.api_key = api_key
    
    st.markdown("---")
    
    st.markdown("## ⚙️ Model Settings")
    model_options = [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-1.0-pro",gemini-2.0-flash
    ]
    
    selected_model = st.selectbox("Select Model:", model_options)
    st.session_state.model = selected_model
    
    st.markdown("---")
    
    st.markdown("## 📄 Chat Controls")
    if st.button("🆕 Start New Chat", use_container_width=True):
        st.session_state.chat_context = []
        st.session_state.display_messages = []
        st.session_state.current_file = None
        st.session_state.file_content = None
        st.session_state.file_type = None
        st.success("New chat started!")
        st.rerun()
    
    st.markdown("---")
    
    # Display info about the current chat
    if st.session_state.chat_context:
        st.markdown(f"**Context Length:** {len(st.session_state.chat_context)} turns")
    
    if st.session_state.current_file:
        st.markdown(f"**Current File:** {st.session_state.current_file.name}")

# Main content area
st.title("📁 Chat With Your Files")

# File uploader
with st.expander("Upload a file to discuss", expanded=not st.session_state.current_file):
    uploaded_file = st.file_uploader("Choose a file", type=None)
    
    if uploaded_file and (not st.session_state.current_file or uploaded_file.name != st.session_state.current_file.name):
        st.session_state.current_file = uploaded_file
        file_content = get_file_content(uploaded_file)
        st.session_state.file_content = file_content
        
        # Determine file type
        mime_type, _ = mimetypes.guess_type(uploaded_file.name)
        if mime_type is None:
            # Fallback for unknown types
            if uploaded_file.name.endswith('.csv'):
                mime_type = 'text/csv'
            else:
                mime_type = 'application/octet-stream'
        
        st.session_state.file_type = mime_type
        
        # Add initial system message about the file
        if not st.session_state.display_messages:
            file_info = f"File uploaded: {uploaded_file.name} ({mime_type})"
            st.session_state.display_messages.append({"role": "system", "content": file_info})
            
            # Auto-generate initial summary if file is uploaded
            if st.session_state.api_key:
                with st.spinner("Analyzing your file..."):
                    file_data = encode_file(st.session_state.file_content, st.session_state.file_type)
                    summary_prompt = f"I've uploaded a file named {uploaded_file.name}. Please analyze it and provide a brief summary of its contents."
                    summary = process_with_gemini(summary_prompt, file_data, st.session_state.model)
                    st.session_state.display_messages.append({"role": "assistant", "content": summary})

# Display chat messages
chat_container = st.container()
with chat_container:
    for message in st.session_state.display_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

# Chat input
if prompt := st.chat_input("Ask something about your file..."):
    if not st.session_state.api_key:
        st.error("Please enter your Gemini API key in the sidebar")
    elif not st.session_state.current_file:
        st.warning("Please upload a file first")
    else:
        # Add user message to display
        st.session_state.display_messages.append({"role": "user", "content": prompt})
        
        with st.spinner("Thinking..."):
            # Reset file content position
            if st.session_state.file_content:
                st.session_state.file_content.seek(0)
            
            # Encode file
            file_data = encode_file(st.session_state.file_content, st.session_state.file_type)
            
            # Process with Gemini
            response = process_with_gemini(prompt, file_data, st.session_state.model)
            
            # Add assistant response to display
            st.session_state.display_messages.append({"role": "assistant", "content": response})
            
            # Force refresh to show the new messages
            st.rerun()

# Footer
st.markdown("---")
st.caption("Built with Streamlit and Gemini API")
