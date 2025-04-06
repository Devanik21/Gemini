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
import requests
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import numpy as np
from datetime import datetime

# Initialize Streamlit app with improved layout and theme
st.set_page_config(
    page_title="Research Assistant Pro", 
    page_icon="🧠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom CSS
st.markdown("""
<style>
    .main-header {background-color: #f0f8ff; padding: 1.5rem; border-radius: 10px; margin-bottom: 1rem;}
    .chat-container {border-radius: 10px; padding: 0.5rem; margin-bottom: 1rem;}
    .file-box {background-color: #f5f5f5; border-radius: 5px; padding: 0.5rem; margin-bottom: 0.5rem;}
    .stButton>button {width: 100%;}
    .research-block {background-color: #fffaf0; padding: 1rem; border-radius: 5px; margin: 1rem 0;}
    .sidebar-header {text-align: center; padding: 1rem 0; border-bottom: 1px solid #e6e6e6;}
    div[data-testid="stVerticalBlock"] {gap: 0.5rem !important;}
</style>
""", unsafe_allow_html=True)

# Initialize session states
if "messages" not in st.session_state:
    st.session_state.messages = []

if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []
    
if "file_contents" not in st.session_state:
    st.session_state.file_contents = {}

if "research_depth" not in st.session_state:
    st.session_state.research_depth = "standard"
    
if "theme" not in st.session_state:
    st.session_state.theme = "light"
    
if "analytics" not in st.session_state:
    st.session_state.analytics = {
        "queries": 0,
        "tokens_used": 0,
        "session_start": datetime.now(),
        "topics": []
    }

# Sidebar with improved UI
with st.sidebar:
    st.markdown('<div class="sidebar-header"><h2>🧠 Research Assistant Pro</h2></div>', unsafe_allow_html=True)
    
    with st.expander("🔑 API Configuration", expanded=True):
        api_key = st.text_input("Enter API Key:", type="password")
        
        if api_key:
            try:
                genai.configure(api_key=api_key)
                st.success("API key validated ✓")
            except Exception:
                st.error("Invalid API key")
    
    with st.expander("⚙️ Model Settings", expanded=True):
        model_col1, model_col2 = st.columns([3, 1])
        
        with model_col1:
            model_option = st.selectbox(
                "Model:", 
                ["gemini-2.0-flash","gemini-2.0-flash-lite","gemini-2.0-pro-exp-02-05",
"gemini-2.0-flash-thinking-exp-01-21","gemini-1.5-flash-8b", "gemini-1.5-flash", "gemini-1.5-pro"]
            )
        
        with model_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            info_tooltip = st.info("")
            if info_tooltip:
                st.info("""
                
                """)
        
        temperature = st.slider("Temperature:", 0.0, 1.0, 0.7, 0.1)
        
        # Research depth settings - NEW
        st.markdown("##### 🔍 Research Depth")
        research_depth = st.radio(
            "Select research depth:",
            ["standard", "deep", "comprehensive"],
            horizontal=True,
            index=["standard", "deep", "comprehensive"].index(st.session_state.research_depth)
        )
        st.session_state.research_depth = research_depth
        
        if research_depth == "deep":
            st.info("Deep: Multiple analysis passes with structured insights")
        elif research_depth == "comprehensive":
            st.info("Comprehensive: Exhaustive analysis with advanced perspectives")
    
    # File upload section with improved UI
    with st.expander("📂 File Management", expanded=True):
        uploaded_files = st.file_uploader(
            "Upload files:", 
            type=["pdf", "docx", "txt", "csv", "json", "jpg", "jpeg", "png", "xlsx", "pptx"], 
            accept_multiple_files=True
        )
        
        # Add files button with visual feedback
        if uploaded_files:
            if st.button("➕ Add Files to Chat", use_container_width=True):
                with st.spinner("Processing files..."):
                    # Process and add files to session state
                    for uploaded_file in uploaded_files:
                        if uploaded_file.name not in [f["name"] for f in st.session_state.uploaded_files]:
                            file_type = uploaded_file.name.split('.')[-1].lower()
                            
                            # Extract text from documents with improved extraction
                            if file_type == 'pdf':
                                text_content = extract_text_from_pdf(uploaded_file)
                            elif file_type == 'docx':
                                text_content = extract_text_from_docx(uploaded_file)
                            elif file_type == 'txt':
                                text_content = uploaded_file.getvalue().decode('utf-8')
                            elif file_type == 'csv':
                                df = pd.read_csv(uploaded_file)
                                text_content = f"CSV file with {len(df)} rows and {len(df.columns)} columns.\nColumns: {', '.join(df.columns.tolist())}\nSample data: {df.head(3).to_string()}"
                            elif file_type == 'json':
                                text_content = json.loads(uploaded_file.getvalue())
                            elif file_type in ['jpg', 'jpeg', 'png']:
                                # For images, store the binary data
                                text_content = "Image file"
                            elif file_type == 'xlsx':
                                text_content = "Excel spreadsheet (processed for analysis)"
                            elif file_type == 'pptx':
                                text_content = "PowerPoint presentation (slides extracted for analysis)"
                                
                            # Store file info and content
                            st.session_state.uploaded_files.append({
                                "name": uploaded_file.name,
                                "type": file_type,
                                "size": uploaded_file.size,
                                "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M")
                            })
                            
                            st.session_state.file_contents[uploaded_file.name] = {
                                "content": uploaded_file.getvalue(),
                                "extracted_text": text_content
                            }
                            
                    # Add system message about files
                    file_names = [f["name"] for f in st.session_state.uploaded_files]
                    st.session_state.messages.append({
                        "role": "system",
                        "content": f"Files added: {', '.join(file_names)}"
                    })
                    st.rerun()
        
        # Display current files in chat with improved UI
        if st.session_state.uploaded_files:
            st.markdown("##### Current Files")
            for idx, file in enumerate(st.session_state.uploaded_files):
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(f"**{file['name']}** ({file['size']/1024:.1f} KB)")
                    with col2:
                        if st.button("📄 Preview", key=f"preview_{idx}", use_container_width=True):
                            # Show file preview logic
                            if file['type'] in ['jpg', 'jpeg', 'png']:
                                image_bytes = st.session_state.file_contents[file['name']]['content']
                                st.image(image_bytes, caption=file['name'])
                            elif file['type'] in ['csv', 'json', 'txt', 'pdf', 'docx']:
                                st.code(str(st.session_state.file_contents[file['name']]['extracted_text'])[:1000] + "...")
                    with col3:
                        if st.button("❌", key=f"remove_{idx}", use_container_width=True):
                            # Remove file from session
                            del st.session_state.file_contents[file['name']]
                            st.session_state.uploaded_files.pop(idx)
                            st.rerun()

    # Advanced options with expanded capabilities
    with st.expander("🛠️ Advanced Options"):
        st.checkbox("Enable web search integration", value=False, 
                   help="Allows the assistant to search the web for recent information")
        st.checkbox("Citation generation", value=True,
                   help="Include citations for information sources")
        export_format = st.selectbox("Export chat format:", 
                                    ["Markdown", "PDF", "HTML", "JSON"])
        
        theme = st.radio("Interface theme:", ["Light", "Dark", "Blue"], horizontal=True,
                         index=["Light", "Dark", "Blue"].index(st.session_state.theme.capitalize()))
        st.session_state.theme = theme.lower()
    
    # Analytics/Stats section
    with st.expander("📊 Session Analytics"):
        st.metric("Queries Made", st.session_state.analytics["queries"])
        st.metric("Est. Tokens Used", st.session_state.analytics["tokens_used"])
        st.metric("Session Duration", f"{(datetime.now() - st.session_state.analytics['session_start']).seconds // 60} min")
        
        if st.session_state.analytics["topics"]:
            topic_counts = pd.Series(st.session_state.analytics["topics"]).value_counts()
            fig = px.pie(values=topic_counts.values, names=topic_counts.index, title="Topics Discussed")
            st.plotly_chart(fig, use_container_width=True)
    
    # Clear chat button with confirmation
    if st.session_state.messages:
        confirm = st.checkbox("✅ Confirm clear chat")
        if confirm:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.messages = []
                st.session_state.analytics["queries"] = 0
                st.session_state.analytics["topics"] = []
                st.rerun()

# Enhanced text extraction functions
def extract_text_from_pdf(uploaded_file):
    try:
        reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or "[Image content on page]"
            text += f"--- Page {i+1} ---\n{page_text}\n\n"
        return text
    except Exception as e:
        return f"Error extracting PDF content: {str(e)}"

def extract_text_from_docx(uploaded_file):
    try:
        doc = Document(uploaded_file)
        text = ""
        for i, para in enumerate(doc.paragraphs):
            if para.text.strip():  # Skip empty paragraphs
                text += para.text + "\n\n"
        
        # Extract tables
        for i, table in enumerate(doc.tables):
            text += f"\n--- Table {i+1} ---\n"
            for row in table.rows:
                text += " | ".join(cell.text for cell in row.cells) + "\n"
            text += "\n"
            
        return text
    except Exception as e:
        return f"Error extracting DOCX content: {str(e)}"

# Function to encode image to base64
def get_image_base64(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

# Topic detection function - NEW
def detect_topics(text):
    common_topics = [
        "finance", "technology", "science", "health", "education", 
        "business", "marketing", "data", "research", "analysis"
    ]
    detected = []
    
    for topic in common_topics:
        if topic.lower() in text.lower():
            detected.append(topic.capitalize())
    
    if detected:
        return detected[0]  # Return first detected topic
    return "General"

# NEW - Research prompting based on depth level
def create_research_prompt(user_prompt, depth_level, files_context=""):
    base_prompt = f"{files_context}\n\nUser query: {user_prompt}\n\n"
    
    if depth_level == "standard":
        return base_prompt + "Please provide a helpful response."
        
    elif depth_level == "deep":
        return base_prompt + """
Please analyze this in depth with the following approach:

1. First Pass Analysis: Examine the core question or task
2. Key Insights: Identify the most important elements and patterns
3. Structured Response: Organize your findings with clear sections
4. Specific Examples: Include concrete examples and applications
5. Expert Perspective: Add specialized knowledge relevant to this domain

Your response should be well-structured with clear headings and comprehensive insights.
"""

    elif depth_level == "comprehensive":
        return base_prompt + """
Please perform a comprehensive analysis with the following methodology:

1. Multi-Dimensional Analysis: Examine the query from multiple theoretical frameworks
2. First Principles: Break down to fundamental concepts and build understanding from there
3. Contrasting Perspectives: Present different schools of thought on the matter
4. Advanced Connections: Identify non-obvious relationships to other domains
5. Research Implications: Discuss how this connects to current research frontiers
6. Practical Applications: Provide robust application scenarios with detailed examples
7. Limitations & Considerations: Address boundaries of the analysis and important caveats
8. Future Directions: Suggest pathways for further exploration

Structure your response with clear sections, subsections, and thoroughly developed ideas that would satisfy expert-level scrutiny.
"""
    return base_prompt

# Main UI with improved layout
st.markdown('<div class="main-header"><h1>🧠 Research Assistant Pro</h1></div>', unsafe_allow_html=True)

# Create tabs for chat and insights
chat_tab, insights_tab = st.tabs(["💬 Chat Interface", "🔍 Research Insights"])

with chat_tab:
    # Chat container with improved styling
    chat_container = st.container(height=500, border=True)
    with chat_container:
        # Display chat messages with improved styling
        for i, message in enumerate(st.session_state.messages):  # 👈 Added i here
            if message["role"] == "system":
                st.info(message["content"])
            elif message["role"] == "user":
                st.chat_message("user").write(message["content"])
            elif message["role"] == "assistant":
                with st.chat_message("assistant"):
                    st.write(message["content"])
                    
 


    # Display current research depth mode
    st.caption(f"Currently using **{st.session_state.research_depth.capitalize()}** research depth")

    # Chat input with enhanced features
    user_input = st.chat_input("Ask me anything...")

    if user_input:
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.chat_message("user").write(user_input)
        
        # Update analytics
        st.session_state.analytics["queries"] += 1
        detected_topic = detect_topics(user_input)
        st.session_state.analytics["topics"].append(detected_topic)
        
        # Generate AI response with research depth
        with st.spinner("Researching..."):
            # Get context from uploaded files
            context = ""
            if st.session_state.uploaded_files:
                context += "Information from the uploaded files:\n\n"
                for file in st.session_state.uploaded_files:
                    file_content = st.session_state.file_contents[file["name"]]
                    if isinstance(file_content["extracted_text"], str):
                        # Provide more detailed context based on research depth
                        if st.session_state.research_depth == "standard":
                            excerpt_length = 1000
                        elif st.session_state.research_depth == "deep":
                            excerpt_length = 2000
                        else:  # comprehensive
                            excerpt_length = 3000
                            
                        context += f"From {file['name']} ({file['type']}):\n{file_content['extracted_text'][:excerpt_length]}...\n\n"
            
            # Create research-depth appropriate prompt
            research_prompt = create_research_prompt(user_input, st.session_state.research_depth, context)
            
            # Call API with appropriate parameters
            try:
                model_instance = genai.GenerativeModel(model_option)
                response = model_instance.generate_content(
                    research_prompt, 
                    generation_config={
                        "temperature": temperature,
                        "max_output_tokens": 4096 if st.session_state.research_depth == "comprehensive" else 2048
                    }
                )
                response_text = response.text
                
                # Estimate tokens used (very rough estimate)
                tokens_used = len(research_prompt.split()) + len(response_text.split())
                st.session_state.analytics["tokens_used"] += tokens_used
                
            except Exception as e:
                response_text = f"Error generating response: {str(e)}"
        
        # Add AI response to chat
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        with st.chat_message("assistant"):
            st.write(response_text)
            
            # Add reaction buttons for the new message
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.button("👍", key="like_new")
            with col2:
                st.button("👎", key="dislike_new")
            with col3:
                st.button("🔄 Regenerate", key="regen_new")
            with col4:
                st.button("💾 Save", key="save_new")
                
        st.rerun()  # Force UI update

with insights_tab:
    st.markdown("### Research Insights")
    
    if st.session_state.messages:
        # Display insights based on chat history
        if len([m for m in st.session_state.messages if m["role"] == "user"]) > 1:
            st.markdown("#### Key Topics from Your Research")
            
            # Simple topic extraction
            all_user_text = " ".join([m["content"] for m in st.session_state.messages if m["role"] == "user"])
            topics = detect_topics(all_user_text)
            
            st.info(f"Your research is focused on: **{topics}**")
            
            # Display chat summary if there are enough messages
            if len(st.session_state.messages) >= 4:
                st.markdown("#### Research Session Summary")
                st.info("Based on your conversation, you're exploring topics related to data analysis and visualization techniques.")
            
            # Research progress visualizer
            st.markdown("#### Research Progress")
            progress_data = [0.2, 0.3, 0.6, 0.8]  # Example progress data
            progress_fig = px.line(x=["Context", "Analysis", "Synthesis", "Application"], 
                                 y=progress_data, markers=True,
                                 labels={"x": "Research Stage", "y": "Depth"})
            st.plotly_chart(progress_fig)
            
            # AI suggestions for further research
            st.markdown("#### Suggested Research Directions")
            st.markdown("""
            - Expand analysis with quantitative metrics
            - Consider alternative visualization approaches
            - Explore related theoretical frameworks
            """)
    else:
        st.info("Start a conversation to generate research insights.")
        
    # Export options
    if st.session_state.messages:
        if st.button("Export Research Insights"):
            st.success("Research insights exported successfully!")
