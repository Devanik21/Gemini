import streamlit as st
import google.generativeai as genai
import pandas as pd
import docx
import PyPDF2
import io
import json
import openpyxl
from io import BytesIO

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
    st.session_state.model = "gemini-2.0-flash"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "files_content" not in st.session_state:
    st.session_state.files_content = {}
if "last_uploaded_files" not in st.session_state:
    st.session_state.last_uploaded_files = []

# File extraction functions
def extract_text_from_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

def extract_text_from_docx(file):
    doc = docx.Document(file)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

def extract_text_from_txt(file):
    return file.getvalue().decode("utf-8")

def extract_text_from_csv(file):
    df = pd.read_csv(file)
    return df.to_string()

def extract_text_from_xlsx(file):
    excel_data = BytesIO(file.getvalue())
    workbook = openpyxl.load_workbook(excel_data, data_only=True)
    text = ""
    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
        text += f"Sheet: {sheet_name}\n"
        for row in sheet.iter_rows(values_only=True):
            text += str(row) + "\n"
        text += "\n"
    return text

def extract_text_from_json(file):
    try:
        json_data = json.loads(file.getvalue().decode("utf-8"))
        return json.dumps(json_data, indent=2)
    except:
        return "Error parsing JSON file"

# Process file based on type
def process_file(uploaded_file):
    try:
        file_type = uploaded_file.type
        if file_type == "application/pdf":
            return extract_text_from_pdf(uploaded_file), "PDF"
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return extract_text_from_docx(uploaded_file), "DOCX"
        elif file_type == "text/plain":
            return extract_text_from_txt(uploaded_file), "TXT"
        elif file_type == "text/csv":
            return extract_text_from_csv(uploaded_file), "CSV"
        elif file_type == "application/json":
            return extract_text_from_json(uploaded_file), "JSON"
        elif "spreadsheetml" in file_type or file_type == "application/vnd.ms-excel":
            return extract_text_from_xlsx(uploaded_file), "XLSX"
        else:
            return None, "Unsupported"
    except Exception as e:
        return f"Error processing file: {str(e)}", "Error"

# Generate AI response
def generate_ai_response(prompt, files_content, model_name, api_key):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        # Combine file contents and limit to avoid token limits
        combined_content = ""
        for filename, content in files_content.items():
            combined_content += f"[File: {filename}]\n{content[:10000]}\n\n"  # Limit each file content
        
        # Generate response with clear instructions
        response = model.generate_content(
            f"""Files content:
{combined_content}

User question: {prompt}

IMPORTANT: Please answer based ONLY on the files content above. 
Reference file names when providing information.
DO NOT reference any previous conversations or files not listed above."""
        )
        
        return response.text
    except Exception as e:
        return f"Error generating response: {str(e)}"

# Sidebar configuration
with st.sidebar:
    st.title("🤖 File Chat Assistant")
    st.markdown("---")
    
    # API Configuration
    st.markdown("## 🔑 API Configuration")
    api_key = st.text_input("Enter Google Gemini API Key:", type="password", 
                         help="Get your key from [Google AI Studio](https://aistudio.google.com/app/apikey)")
    if api_key:
        st.session_state.api_key = api_key
    
    # Model Settings
    st.markdown("## ⚙️ Model Settings")
    model_options = [
        "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-pro-exp-02-05",
        "gemini-2.5-pro-exp-03-25", "gemini-1.5-flash-8b"
    ]
    st.session_state.model = st.selectbox("Select Gemini Model:", model_options, index=0)


    
    # About Section
    st.markdown("## ℹ️ About")
    st.markdown("""
    This app allows you to chat with your files using Google's Gemini API.
    
    **Supported file types:**
    - PDF (.pdf)
    - Word (.docx)
    - Text (.txt)
    - CSV (.csv)
    - Excel (.xlsx)
    - JSON (.json)
    
    **Note:** Files are processed locally and not stored permanently.
    """)

# Main content
st.title("📁 Chat With Your Files")
st.write("Upload one or more documents and ask questions about their content")

# File management
col1, col2 = st.columns([4, 1])
with col1:
    # File upload section - Multiple files
    uploaded_files = st.file_uploader("Upload your files", type=["pdf", "docx", "txt", "csv", "xlsx", "json"], accept_multiple_files=True)
with col2:
    if st.button("Clear All Files", use_container_width=True):
        st.session_state.files_content = {}
        st.session_state.chat_history = []
        st.session_state.last_uploaded_files = []
        st.success("All files cleared")
        st.rerun()

if uploaded_files:
    # Check if the uploaded files have changed
    current_files = [file.name for file in uploaded_files]
    if current_files != st.session_state.last_uploaded_files:
        # Files changed, clear previous files
        st.session_state.files_content = {}
        st.session_state.last_uploaded_files = current_files
    
    # Process each uploaded file
    for uploaded_file in uploaded_files:
        # Check if file was already processed
        if uploaded_file.name not in st.session_state.files_content:
            with st.spinner(f"Processing {uploaded_file.name}..."):
                extracted_text, file_type = process_file(uploaded_file)
                if extracted_text and file_type != "Error" and file_type != "Unsupported":
                    st.session_state.files_content[uploaded_file.name] = extracted_text
                    st.success(f"✅ {file_type} file '{uploaded_file.name}' processed successfully!")
                else:
                    st.error(f"❌ Could not process '{uploaded_file.name}': {extracted_text}")
    
    # Display summary of processed files
    if st.session_state.files_content:
        file_count = len(st.session_state.files_content)
        file_names = ", ".join(st.session_state.files_content.keys())
        st.success(f"✅ {file_count} file{'s' if file_count > 1 else ''} processed: {file_names}")

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
        if i < len(st.session_state.chat_history) - 1:
            st.markdown("---")

# User input
user_question = st.text_input("Ask a question about your files:", key="user_input")

# Action buttons
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
    elif not st.session_state.files_content:
        st.warning("Please upload at least one file first.")
    else:
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": user_question})
        
        # Generate AI response
        with st.spinner("AI is thinking..."):
            ai_response = generate_ai_response(
                user_question, 
                st.session_state.files_content, 
                st.session_state.model, 
                st.session_state.api_key
            )
            
            # Add AI response to chat history
            st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
        
        # Rerun to update chat display
        st.rerun()

# Display message if no files uploaded
if not st.session_state.files_content:
    st.info("👆 Please upload at least one file to start chatting")

# Tips for better results
with st.expander("💡 Tips for better results"):
    st.markdown("""
    - Ask specific questions about the content in your files
    - When working with multiple files, specify which file you're asking about
    - For large documents, try to reference specific sections or topics
    - For data files (CSV, Excel), you can ask for specific data analysis or summaries
    """)

# Footer
st.markdown("---")
st.markdown("📁 Chat With Your Files | Made with ❤️ using Streamlit and Google Gemini")
