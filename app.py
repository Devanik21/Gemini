import streamlit as st
import google.generativeai as genai
from tinydb import TinyDB, Query
import json
import base64
import io
from PIL import Image
import tempfile
import os
from datetime import datetime
import uuid
import time
from gtts import gTTS
import pandas as pd
import docx
import PyPDF2
import markdown
from io import BytesIO
import zipfile

# Page configuration
st.set_page_config(
    page_title="Gemini Pro Chat",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'chat_id' not in st.session_state:
    st.session_state.chat_id = str(uuid.uuid4())
if 'db' not in st.session_state:
    st.session_state.db = TinyDB('chat_history.json')
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-left: 20%;
    }
    .assistant-message {
        background: #f8f9fa;
        border-left: 4px solid #667eea;
    }
    .file-upload-area {
        border: 2px dashed #667eea;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        margin: 1rem 0;
    }
    .feature-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem;
    }
    .audio-player {
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class GeminiChat:
    def __init__(self):
        self.api_key = st.secrets.get("GEMINI_API_KEY", "")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.text_model = genai.GenerativeModel('gemma-3n-e4b-it')
            self.image_model = genai.GenerativeModel('gemini-2.0-flash-preview-image-generation')
        
    def is_image_generation_request(self, prompt):
        """Check if prompt is for image generation"""
        image_keywords = ['create image', 'generate image', 'draw', 'imagine', 'visualize', 
                         'make a picture', 'design', 'create a graphic', 'illustrate']
        return any(keyword in prompt.lower() for keyword in image_keywords)
    
    def process_uploaded_file(self, uploaded_file):
        """Process different file types"""
        file_extension = uploaded_file.name.split('.')[-1].lower()
        content = ""
        
        if file_extension == 'pdf':
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            for page in pdf_reader.pages:
                content += page.extract_text()
        elif file_extension in ['txt', 'md']:
            content = str(uploaded_file.read(), "utf-8")
        elif file_extension == 'docx':
            doc = docx.Document(uploaded_file)
            content = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        elif file_extension in ['csv']:
            df = pd.read_csv(uploaded_file)
            content = df.to_string()
        elif file_extension in ['json']:
            data = json.load(uploaded_file)
            content = json.dumps(data, indent=2)
        elif file_extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            return uploaded_file  # Return image file as is
        
        return content
    
    def generate_response(self, prompt, files=None, context=None):
        """Generate response using Gemini API"""
        try:
            # Check if it's an image generation request
            if self.is_image_generation_request(prompt):
                response = self.image_model.generate_content([prompt])
                return response, "image"
            
            # Prepare content for text model
            content_parts = [prompt]
            
            # Add context from previous messages
            if context:
                context_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in context[-10:]])
                content_parts.insert(0, f"Previous context:\n{context_text}\n\nCurrent request:")
            
            # Add uploaded files content
            if files:
                for file_content in files:
                    if isinstance(file_content, str):
                        content_parts.append(f"File content:\n{file_content}")
                    else:  # Image file
                        content_parts.append(file_content)
            
            response = self.text_model.generate_content(content_parts)
            return response, "text"
            
        except Exception as e:
            return f"Error generating response: {str(e)}", "error"
    
    def save_chat_to_db(self, chat_data):
        """Save chat to TinyDB"""
        st.session_state.db.insert(chat_data)
    
    def load_chat_history(self, chat_id):
        """Load chat history from DB"""
        Chat = Query()
        return st.session_state.db.search(Chat.chat_id == chat_id)

def create_audio(text, lang='en'):
    """Create audio from text using gTTS"""
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        fp = BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp
    except:
        return None

def create_download_options(content, content_type="text"):
    """Create download options for different formats"""
    downloads = {}
    
    if content_type == "text":
        # Text file
        downloads['txt'] = content.encode('utf-8')
        
        # Markdown file
        downloads['md'] = f"# Gemini Response\n\n{content}".encode('utf-8')
        
        # JSON file
        downloads['json'] = json.dumps({"response": content, "timestamp": datetime.now().isoformat()}).encode('utf-8')
    
    return downloads

def export_chat_history():
    """Export entire chat history"""
    if st.session_state.messages:
        chat_data = {
            "chat_id": st.session_state.chat_id,
            "messages": st.session_state.messages,
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(chat_data, indent=2).encode('utf-8')
    return None

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🧠 Gemini Pro Chat Assistant</h1>
        <p>Industry-grade AI assistant with advanced features</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize Gemini Chat
    if 'gemini_chat' not in st.session_state:
        st.session_state.gemini_chat = GeminiChat()
    
    # Sidebar
    with st.sidebar:
        st.header("🛠️ Features")
        
        # API Key check
        if not st.session_state.gemini_chat.api_key:
            st.error("⚠️ Please add GEMINI_API_KEY to Streamlit secrets")
            return
        else:
            st.success("✅ API Key configured")
        
        # File Upload
        st.subheader("📁 Upload Files")
        uploaded_files = st.file_uploader(
            "Upload documents, images, or data files",
            accept_multiple_files=True,
            type=['txt', 'pdf', 'docx', 'md', 'csv', 'json', 'jpg', 'jpeg', 'png', 'gif', 'webp']
        )
        
        # Process uploaded files
        if uploaded_files:
            st.session_state.uploaded_files = []
            for file in uploaded_files:
                processed_content = st.session_state.gemini_chat.process_uploaded_file(file)
                st.session_state.uploaded_files.append(processed_content)
                st.success(f"✅ {file.name}")
        
        # Advanced Features
        st.subheader("🚀 Advanced Features")
        
        # Smart Context Management
        with st.expander("🧠 Smart Context"):
            context_length = st.slider("Context Messages", 5, 50, 10)
            st.info("Maintains conversation context for better responses")
        
        # Multi-language Support
        with st.expander("🌐 Language Options"):
            audio_lang = st.selectbox("Audio Language", ['en', 'es', 'fr', 'de', 'it', 'pt', 'hi'])
            st.info("Text-to-speech in multiple languages")
        
        # Response Style
        with st.expander("✨ Response Style"):
            response_style = st.selectbox("Style", ['Professional', 'Creative', 'Technical', 'Casual'])
            st.info("Customize AI response tone")
        
        # Export Options
        st.subheader("💾 Export & Download")
        if st.session_state.messages:
            chat_export = export_chat_history()
            if chat_export:
                st.download_button(
                    "📥 Download Chat History",
                    chat_export,
                    file_name=f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        # Clear Chat
        if st.button("🗑️ Clear Chat", type="secondary"):
            st.session_state.messages = []
            st.session_state.chat_id = str(uuid.uuid4())
            st.rerun()
    
    # Main Chat Interface
    col1, col2, col3 = st.columns([1, 6, 1])
    
    with col2:
        # Display Chat Messages
        chat_container = st.container()
        
        with chat_container:
            for message in st.session_state.messages:
                if message["role"] == "user":
                    st.markdown(f"""
                    <div class="chat-message user-message">
                        <strong>You:</strong> {message["content"]}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="chat-message assistant-message">
                        <strong>🧠 Gemini:</strong> {message["content"]}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Audio playback for assistant messages
                    if "audio_data" in message:
                        st.audio(message["audio_data"])
                    
                    # Download options
                    if message["content"]:
                        downloads = create_download_options(message["content"])
                        cols = st.columns(len(downloads))
                        for i, (format_type, data) in enumerate(downloads.items()):
                            with cols[i]:
                                st.download_button(
                                    f"📥 {format_type.upper()}",
                                    data,
                                    file_name=f"response_{len(st.session_state.messages)}_{i}.{format_type}",
                                    mime=f"text/{format_type}" if format_type != 'json' else "application/json",
                                    key=f"download_{len(st.session_state.messages)}_{i}"
                                )
        
        # Chat Input
        prompt = st.chat_input("Ask Gemini anything... (supports image generation, file analysis, and more!)")
        
        if prompt:
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Show typing indicator
            with st.spinner("🧠 Gemini is thinking..."):
                # Prepare context and files
                context = st.session_state.messages[:-1] if len(st.session_state.messages) > 1 else None
                files = st.session_state.uploaded_files if st.session_state.uploaded_files else None
                
                # Add response style to prompt
                styled_prompt = f"[{response_style} style] {prompt}"
                
                # Generate response
                response, response_type = st.session_state.gemini_chat.generate_response(
                    styled_prompt, files, context
                )
                
                if response_type == "error":
                    response_text = response
                elif response_type == "image":
                    # Handle image generation response
                    response_text = response.text if hasattr(response, 'text') else "Image generated successfully!"
                    # Note: Image handling would need additional setup for display
                else:
                    response_text = response.text if hasattr(response, 'text') else str(response)
                
                # Create audio
                audio_data = create_audio(response_text[:500], audio_lang)  # Limit audio length
                
                # Add assistant message
                assistant_message = {
                    "role": "assistant", 
                    "content": response_text,
                    "timestamp": datetime.now().isoformat()
                }
                
                if audio_data:
                    assistant_message["audio_data"] = audio_data
                
                st.session_state.messages.append(assistant_message)
                
                # Save to database
                chat_data = {
                    "chat_id": st.session_state.chat_id,
                    "messages": st.session_state.messages,
                    "timestamp": datetime.now().isoformat()
                }
                st.session_state.gemini_chat.save_chat_to_db(chat_data)
            
            # Rerun to show new message
            st.rerun()

    # Footer with advanced features info
    st.markdown("---")
    with st.expander("🌟 Advanced Features Available"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            **🎯 Smart Features:**
            - Universal file upload support
            - Persistent chat sessions
            - Context-aware responses
            - Multi-format downloads
            """)
        
        with col2:
            st.markdown("""
            **🎨 AI Capabilities:**
            - Text generation & analysis
            - Image generation (on request)
            - Document processing
            - Data analysis
            """)
        
        with col3:
            st.markdown("""
            **🔧 Professional Tools:**
            - TinyDB storage
            - Audio responses (TTS)
            - Export/Import chats
            - Multi-language support
            """)

if __name__ == "__main__":
    main()
