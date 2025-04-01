import streamlit as st
import os
import google.generativeai as genai
import tempfile
import base64
import mimetypes
from io import BytesIO, StringIO
import re

# Add imports for document parsing
try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    from wordcloud import WordCloud, STOPWORDS
    WORDCLOUD_AVAILABLE = True
except ImportError:
    WORDCLOUD_AVAILABLE = False
    STOPWORDS = set()

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import plotly.express as px
    from collections import Counter
    DATA_ANALYSIS_AVAILABLE = True
except ImportError:
    DATA_ANALYSIS_AVAILABLE = False

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
if "extracted_text" not in st.session_state:
    st.session_state.extracted_text = None

# Function to extract text from DOCX
def extract_text_from_docx(file):
    if not DOCX_AVAILABLE:
        return "python-docx package is not installed. Install with: pip install python-docx"
    
    try:
        doc = docx.Document(file)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    except Exception as e:
        return f"Error extracting text from DOCX: {str(e)}"

# Function to extract text from TXT
def extract_text_from_txt(file):
    try:
        return file.getvalue().decode('utf-8')
    except Exception as e:
        return f"Error extracting text from TXT: {str(e)}"

# Function to extract text from CSV
def extract_text_from_csv(file):
    try:
        df = pd.read_csv(file)
        return df.to_string()
    except Exception as e:
        return f"Error extracting text from CSV: {str(e)}"

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
        message_parts = [{"text": prompt}]
        
        # If we have extracted text from DOCX or other unsupported formats
        if st.session_state.extracted_text and not file_data:
            # Include the extracted text in the prompt
            extended_prompt = f"{prompt}\n\nFile content:\n{st.session_state.extracted_text[:10000]}"
            message_parts = [{"text": extended_prompt}]
        # Add file if provided and not sending extracted text
        elif file_data:
            message_parts.append(file_data)
            
        content.append({"role": "user", "parts": message_parts})
        
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
        "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-lite",
        "gemini-2.0-pro-exp-02-05", "gemini-2.0-flash-thinking-exp-01-21",
        "gemini-2.5-pro-exp-03-25", "gemini-1.5-flash-8b"
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
        st.session_state.extracted_text = None
        st.success("New chat started!")
        st.rerun()
    
    st.markdown("---")
    
    # Display info about the current chat
    if st.session_state.chat_context:
        st.markdown(f"**Context Length:** {len(st.session_state.chat_context)} turns")
    
    if st.session_state.current_file:
        st.markdown(f"**Current File:** {st.session_state.current_file.name}")
        
        # Add file analysis options if we have a file
        if st.session_state.current_file and DATA_ANALYSIS_AVAILABLE:
            st.markdown("## 📊 File Analysis")
            if st.button("Analyze File Content", use_container_width=True):
                st.session_state.show_analysis = True
                st.rerun()

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
            elif uploaded_file.name.endswith('.docx'):
                mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            else:
                mime_type = 'application/octet-stream'
        
        st.session_state.file_type = mime_type
        
        # For DOCX files, extract text to avoid MIME type issues
        if mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            with st.spinner("Extracting text from DOCX..."):
                # Reset file position
                uploaded_file.seek(0)
                extracted_text = extract_text_from_docx(uploaded_file)
                st.session_state.extracted_text = extracted_text
                st.success("Text extracted from DOCX file")
        elif mime_type == 'text/plain':
            uploaded_file.seek(0)
            st.session_state.extracted_text = extract_text_from_txt(uploaded_file)
        elif mime_type == 'text/csv':
            uploaded_file.seek(0)
            st.session_state.extracted_text = extract_text_from_csv(uploaded_file)
        
        # Add initial system message about the file
        if not st.session_state.display_messages:
            file_info = f"File uploaded: {uploaded_file.name} ({mime_type})"
            st.session_state.display_messages.append({"role": "system", "content": file_info})
            
            # Auto-generate initial summary if file is uploaded
            if st.session_state.api_key:
                with st.spinner("Analyzing your file..."):
                    # For DOCX files, use extracted text
                    if mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                        summary_prompt = f"I've uploaded a DOCX file named {uploaded_file.name}. Please analyze its content and provide a brief summary."
                        summary = process_with_gemini(summary_prompt, None, st.session_state.model)
                    else:
                        # Reset file position
                        st.session_state.file_content.seek(0)
                        file_data = encode_file(st.session_state.file_content, st.session_state.file_type)
                        summary_prompt = f"I've uploaded a file named {uploaded_file.name}. Please analyze it and provide a brief summary of its contents."
                        summary = process_with_gemini(summary_prompt, file_data, st.session_state.model)
                    
                    st.session_state.display_messages.append({"role": "assistant", "content": summary})

# Display file content preview if available
if st.session_state.extracted_text:
    with st.expander("File Content Preview"):
        st.text_area("Extracted Content:", st.session_state.extracted_text[:2000], height=200)

# Display data analysis if requested
if "show_analysis" in st.session_state and st.session_state.show_analysis and DATA_ANALYSIS_AVAILABLE:
    with st.expander("Data Analysis", expanded=True):
        if st.session_state.file_type == 'text/csv':
            try:
                # Reset file position
                st.session_state.current_file.seek(0)
                df = pd.read_csv(st.session_state.current_file)
                
                st.subheader("📊 Data Visualizations")
                
                # Create tabs for different visualization categories
                viz_tabs = st.tabs(["Basic Stats", "Distributions", "Correlations"])
                
                with viz_tabs[0]:  # Basic Stats
                    st.write("### Data Overview")
                    st.dataframe(df.describe())
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("### Missing Values")
                        st.bar_chart(df.isnull().sum())
                    with col2:
                        st.write("### Data Types")
                        st.write(pd.DataFrame(df.dtypes, columns=['Data Type']))
                
                with viz_tabs[1]:  # Distributions
                    st.write("### Distributions")
                    
                    # Determine numeric columns
                    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                    if numeric_cols:
                        selected_col = st.selectbox("Select column for histogram:", numeric_cols)
                        fig = px.histogram(df, x=selected_col, marginal="box")
                        st.plotly_chart(fig, use_container_width=True)
                
                with viz_tabs[2]:  # Correlations
                    st.write("### Correlations")
                    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                    if len(numeric_cols) >= 2:
                        try:
                            corr = df[numeric_cols].corr()
                            fig = px.imshow(corr, text_auto=True, color_continuous_scale='RdBu_r')
                            st.plotly_chart(fig, use_container_width=True)
                        except Exception as e:
                            st.error(f"Error creating correlation matrix: {str(e)}")
                    else:
                        st.info("Need at least 2 numeric columns for correlation analysis.")
                        
            except Exception as e:
                st.error(f"Error analyzing CSV: {str(e)}")
        
        elif st.session_state.extracted_text:
            st.subheader("📝 Text Analysis")
            
            # Basic stats
            words = re.findall(r'\w+', st.session_state.extracted_text.lower())
            word_freq = Counter(words)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Words", len(words))
            with col2:
                st.metric("Unique Words", len(word_freq))
            with col3:
                st.metric("Total Characters", len(st.session_state.extracted_text))
            
            # Word cloud if available
            if WORDCLOUD_AVAILABLE and words:
                st.write("### Word Cloud")
                
                stop_words = set(STOPWORDS)
                filtered_words = [w for w in words if w not in stop_words and len(w) > 2]
                
                if filtered_words:
                    wc = WordCloud(width=800, height=400, 
                                  background_color='white', 
                                  colormap='viridis', 
                                  max_words=200)
                    wc.generate(" ".join(filtered_words))
                    
                    fig, ax = plt.subplots(figsize=(10, 5))
                    ax.imshow(wc, interpolation='bilinear')
                    ax.axis('off')
                    st.pyplot(fig)
            
            # Top words
            st.write("### Top Words")
            if word_freq:
                top_words = pd.DataFrame(word_freq.most_common(20), columns=['Word', 'Count'])
                fig = px.bar(top_words, x='Word', y='Count')
                st.plotly_chart(fig, use_container_width=True)

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
            # For DOCX files, use the extracted text approach
            if st.session_state.file_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                response = process_with_gemini(prompt, None, st.session_state.model)
            else:
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
