import streamlit as st
import google.generativeai as genai
import os
import pandas as pd
import docx
import PyPDF2
import io
import time
from pathlib import Path

# Set page configuration
st.set_page_config(
    page_title="Chat With Your Files",
    page_icon="📁",
    layout="wide"
)

# Initialize session state variables
if "api_key" not in st.session_state:
    st.session_state.api_key = None
if "model" not in st.session_state:
    st.session_state.model = "gemini-1.5-flash"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "file_content" not in st.session_state:
    st.session_state.file_content = None
if "file_name" not in st.session_state:
    st.session_state.file_name = None

# Function to extract text from PDF
def extract_text_from_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

# Function to extract text from DOCX
def extract_text_from_docx(file):
    doc = docx.Document(file)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

# Function to extract text from TXT
def extract_text_from_txt(file):
    return file.getvalue().decode("utf-8")

# Function to extract text from CSV
def extract_text_from_csv(file):
    df = pd.read_csv(file)
    return df.to_string()

# Function to generate AI response
def generate_ai_response(prompt, file_content, model_name, api_key):
    try:
        genai.configure(api_key=api_key)
        
        # Select the model
        model = genai.GenerativeModel(model_name)
        
        # Create context with file content
        context = f"File content: {file_content[:50000]}"  # Limiting to first 50K chars to avoid token limits
        
        # Generate response
        response = model.generate_content(
            f"{context}\n\nUser question: {prompt}\n\nPlease answer the question based on the file content above."
        )
        
        return response.text
    except Exception as e:
        return f"Error generating response: {str(e)}"

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
        "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash", 
        "gemini-2.0-pro", "gemini-1.5-flash-8b"
    ]
    
    selected_model = st.selectbox("Select Gemini Model:", model_options, index=0)
    st.session_state.model = selected_model
    
    st.markdown("---")
    
    # About section
    st.markdown("## ℹ️ About")
    st.markdown("""
    This app allows you to chat with your files using Google's Gemini API.
    
    **Supported file types:**
    - PDF (.pdf)
    - Word (.docx)
    - Text (.txt)
    - CSV (.csv)
    
    **Note:** File contents are processed locally and are not stored permanently.
    """)

# Main content area
st.title("📁 Chat With Your Files")
st.write("Upload a document and ask questions about its content")

# File upload section
uploaded_file = st.file_uploader("Upload your file", type=["pdf", "docx", "txt", "csv"])

if uploaded_file:
    # Process the file
    file_details = {"Filename": uploaded_file.name, "FileType": uploaded_file.type, "FileSize": f"{uploaded_file.size / 1024:.2f} KB"}
    
    with st.expander("File Details", expanded=False):
        st.json(file_details)
    
    # Extract content based on file type
    try:
        with st.spinner("Processing file..."):
            if uploaded_file.type == "application/pdf":
                extracted_text = extract_text_from_pdf(uploaded_file)
                file_type = "PDF"
            elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                extracted_text = extract_text_from_docx(uploaded_file)
                file_type = "DOCX"
            elif uploaded_file.type == "text/plain":
                extracted_text = extract_text_from_txt(uploaded_file)
                file_type = "TXT"
            elif uploaded_file.type == "text/csv":
                extracted_text = extract_text_from_csv(uploaded_file)
                file_type = "CSV"
            else:
                st.error("Unsupported file type")
                extracted_text = None
                file_type = None
        
        if extracted_text:
            st.session_state.file_content = extracted_text
            st.session_state.file_name = uploaded_file.name
            
            with st.expander("Preview Content", expanded=False):
                st.text_area("Extracted text:", extracted_text[:5000], height=300, disabled=True)
                if len(extracted_text) > 5000:
                    st.info(f"Showing first 5000 characters out of {len(extracted_text)} total characters")
            
            st.success(f"✅ {file_type} file processed successfully!")
    
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")

# Chat interface
st.header("💬 Chat")

# Display chat history
chat_container = st.container()
with chat_container:
    for i, message in enumerate(st.session_state.chat_history):
        if message["role"] == "user":
            st.markdown(f"**You:** {message['content']}")
        else:
            st.markdown(f"**AI:** {message['content']}")
        
        # Add a separator between messages except for the last one
        if i < len(st.session_state.chat_history) - 1:
            st.markdown("---")

# User input
user_question = st.text_input("Ask a question about your file:", key="user_input")

# Submit button
col1, col2 = st.columns([1, 5])
with col1:
    submit_button = st.button("Ask 🔍", use_container_width=True)
with col2:
    if st.button("Clear Chat 🗑️", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

# Process user question
if submit_button and user_question:
    if not st.session_state.api_key:
        st.error("Please enter your Gemini API key in the sidebar.")
    elif not st.session_state.file_content:
        st.warning("Please upload a file first.")
    else:
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": user_question})
        
        # Display "AI is thinking" message
        with st.spinner("AI is thinking..."):
            # Generate AI response
            ai_response = generate_ai_response(
                user_question, 
                st.session_state.file_content, 
                st.session_state.model, 
                st.session_state.api_key
            )
            
            # Add AI response to chat history
            st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
        
        # Rerun the app to update the chat display
        st.rerun()

# Display a message if no file is uploaded
if not st.session_state.file_content:
    st.info("👆 Please upload a file to start chatting")

# Bottom area with tips
with st.expander("💡 Tips for better results"):
    st.markdown("""
    - Ask specific questions about the content in your file
    - For large documents, try to reference specific sections or topics
    - If the response seems incomplete, try breaking your question into smaller parts
    - For CSV files, you can ask for specific data analysis or summaries
    """)

# Footer
st.markdown("---")
st.markdown("📁 Chat With Your Files | Made with ❤️ using Streamlit and Google Gemini")
