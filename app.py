import streamlit as st
import google.generativeai as genai
import os
import PyPDF2
from docx import Document
import json
import pandas as pd
from io import BytesIO
import time
import base64

# Initialize Streamlit app
st.set_page_config(page_title="Claude-Like Chat Interface", page_icon="🤖", layout="wide")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []
    
if "file_contents" not in st.session_state:
    st.session_state.file_contents = {}

# Sidebar for API Key and settings
with st.sidebar:
    st.header("🔑 API Configuration")
    api_key = st.text_input("Enter API Key:", type="password")
    
    st.header("⚙️ Model Settings")
    model_option = st.selectbox(
        "Model Selection:", 
        ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"]
    )
    
    temperature = st.slider("Temperature:", 0.0, 1.0, 0.7, 0.1)
    
    # File upload section in sidebar
    st.header("📂 Upload Files")
    uploaded_files = st.file_uploader(
        "Upload files (PDF, DOCX, TXT, CSV, JSON, Images)", 
        type=["pdf", "docx", "txt", "csv", "json", "jpg", "jpeg", "png"], 
        accept_multiple_files=True
    )
    
    # Add files button
    if uploaded_files:
        if st.button("➕ Add Files to Chat"):
            # Process and add files to session state
            for uploaded_file in uploaded_files:
                if uploaded_file.name not in [f["name"] for f in st.session_state.uploaded_files]:
                    file_type = uploaded_file.name.split('.')[-1].lower()
                    
                    # Extract text from documents
                    if file_type == 'pdf':
                        text_content = extract_text_from_pdf(uploaded_file)
                    elif file_type == 'docx':
                        text_content = extract_text_from_docx(uploaded_file)
                    elif file_type == 'txt':
                        text_content = uploaded_file.getvalue().decode('utf-8')
                    elif file_type == 'csv':
                        text_content = f"CSV file with {len(pd.read_csv(uploaded_file))} rows"
                    elif file_type == 'json':
                        text_content = json.loads(uploaded_file.getvalue())
                    elif file_type in ['jpg', 'jpeg', 'png']:
                        # For images, store the binary data
                        text_content = "Image file"
                        
                    # Store file info and content
                    st.session_state.uploaded_files.append({
                        "name": uploaded_file.name,
                        "type": file_type,
                        "size": uploaded_file.size
                    })
                    
                    st.session_state.file_contents[uploaded_file.name] = {
                        "content": uploaded_file.getvalue(),
                        "extracted_text": text_content
                    }
                    
            # Add system message about files
            file_names = [f["name"] for f in st.session_state.uploaded_files]
            st.session_state.messages.append({
                "role": "system",
                "content": f"Files added to chat: {', '.join(file_names)}"
            })
            st.rerun()
    
    # Display current files in chat
    if st.session_state.uploaded_files:
        st.header("Current Files in Chat")
        for idx, file in enumerate(st.session_state.uploaded_files):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"{file['name']} ({file['size']/1024:.1f} KB)")
            with col2:
                if st.button("❌", key=f"remove_{idx}"):
                    # Remove file from session
                    del st.session_state.file_contents[file['name']]
                    st.session_state.uploaded_files.pop(idx)
                    st.rerun()

    # Clear chat button
    if st.session_state.messages:
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.rerun()

# Text extraction functions
def extract_text_from_pdf(uploaded_file):
    reader = PyPDF2.PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n\n"
    return text

def extract_text_from_docx(uploaded_file):
    doc = Document(uploaded_file)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n\n"
    return text

# Function to encode image to base64
def get_image_base64(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

# Main chat interface
st.title("🤖 Claude-Like Chat Interface")

# Display chat messages
for message in st.session_state.messages:
    if message["role"] == "system":
        st.info(message["content"])
    elif message["role"] == "user":
        st.chat_message("user").write(message["content"])
    else:
        st.chat_message("assistant").write(message["content"])

# Generate response function
def generate_response(prompt, api_key, model, temp):
    # Configure the API
    if not api_key:
        return "❌ API key is required."
    
    genai.configure(api_key=api_key)
    model_instance = genai.GenerativeModel(model)
    
    # Get context from uploaded files
    context = ""
    if st.session_state.uploaded_files:
        context += "Here's information from the uploaded files:\n\n"
        for file in st.session_state.uploaded_files:
            file_content = st.session_state.file_contents[file["name"]]
            if isinstance(file_content["extracted_text"], str):
                # Truncate long text to avoid context window issues
                context += f"From {file['name']}:\n{file_content['extracted_text'][:2000]}...\n\n"
    
    # Get conversation history
    history = ""
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            history += f"{msg['role'].capitalize()}: {msg['content']}\n\n"
    
    # Create the full prompt with context and history
    full_prompt = f"{context}\n\nConversation history:\n{history}\n\nUser: {prompt}\n\nAssistant:"
    
    try:
        response = model_instance.generate_content(
            full_prompt, 
            generation_config={
                "temperature": temp,
                "max_output_tokens": 2048
            }
        )
        return response.text
    except Exception as e:
        return f"Error generating response: {str(e)}"

# Chat input with "up arrow" functionality 
# (Streamlit doesn't support JS for keyboard shortcuts directly, but we'll add a placeholder)
user_input = st.chat_input("Type your message...")

if user_input:
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)
    
    # Generate AI response
    with st.spinner("Thinking..."):
        response = generate_response(user_input, api_key, model_option, temperature)
    
    # Add AI response to chat
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.chat_message("assistant").write(response)

# Add a note about features
st.caption("""
💡 **Tips**: 
- Use the sidebar to upload files and add them to the chat
- The "➕ Add Files" button adds uploaded files to the conversation
- Chat history is maintained within the session
""")
