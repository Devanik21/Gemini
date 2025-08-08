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
            try:
                self.image_model = genai.GenerativeModel('gemini-2.0-flash-preview-image-generation')
            except:
                self.image_model = None
        
    def is_image_generation_request(self, prompt):
        """Check if prompt is for image generation"""
        image_keywords = ['create image', 'generate image', 'draw', 'imagine', 'visualize', 
                         'make a picture', 'design', 'create a graphic', 'illustrate']
        return any(keyword in prompt.lower() for keyword in image_keywords)
    
    def process_uploaded_file(self, uploaded_file):
        """Process different file types"""
        try:
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
                content = df.head(100).to_string()  # Limit rows
            elif file_extension in ['json']:
                data = json.load(uploaded_file)
                content = json.dumps(data, indent=2)[:5000]  # Limit size
            elif file_extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                # Convert image to base64 string for storage
                image = Image.open(uploaded_file)
                buffer = BytesIO()
                image.save(buffer, format='PNG')
                img_str = base64.b64encode(buffer.getvalue()).decode()
                return f"[IMAGE_DATA:{img_str[:100]}...]"  # Truncated for storage
            
            return content[:10000]  # Limit content size
        except Exception as e:
            return f"Error processing file {uploaded_file.name}: {str(e)}"
    
    def generate_response(self, prompt, files=None, context=None):
        """Generate response using Gemini API"""
        try:
            # Check if it's an image generation request
            if self.is_image_generation_request(prompt) and self.image_model:
                response = self.image_model.generate_content([prompt])
                return response, "image"
            
            # Prepare content for text model
            content_parts = []
            
            # Add context from previous messages
            if context:
                context_text = "\n".join([f"{msg['role']}: {msg['content'][:500]}" for msg in context[-5:]])
                content_parts.append(f"Context: {context_text}")
            
            # Add uploaded files content
            if files:
                for i, file_content in enumerate(files):
                    if isinstance(file_content, str) and not file_content.startswith("[IMAGE_DATA"):
                        content_parts.append(f"File {i+1}: {file_content[:2000]}")
            
            content_parts.append(f"User request: {prompt}")
            
            response = self.text_model.generate_content("\n\n".join(content_parts))
            return response, "text"
            
        except Exception as e:
            return f"Error: {str(e)}", "error"
    
    def save_chat_to_db(self, messages, chat_id):
        """Save chat to TinyDB with serializable data only"""
        try:
            # Create serializable version of messages
            serializable_messages = []
            for msg in messages:
                clean_msg = {
                    "role": msg["role"],
                    "content": msg["content"][:5000],  # Limit content size
                    "timestamp": msg.get("timestamp", datetime.now().isoformat())
                }
                serializable_messages.append(clean_msg)
            
            chat_data = {
                "chat_id": chat_id,
                "messages": serializable_messages,
                "timestamp": datetime.now().isoformat()
            }
            
            # Remove existing chat with same ID
            Chat = Query()
            st.session_state.db.remove(Chat.chat_id == chat_id)
            
            # Insert new chat data
            st.session_state.db.insert(chat_data)
            
        except Exception as e:
            st.error(f"Error saving chat: {str(e)}")
    
    def load_chat_history(self, chat_id):
        """Load chat history from DB"""
        try:
            Chat = Query()
            return st.session_state.db.search(Chat.chat_id == chat_id)
        except:
            return []

def create_audio(text, lang='en'):
    """Create audio from text using gTTS"""
    try:
        # Clean and limit text
        clean_text = text.replace('\n', ' ').strip()[:1000]
        if not clean_text:
            return None
            
        tts = gTTS(text=clean_text, lang=lang, slow=False)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            tts.save(tmp_file.name)
            
            # Read file and create BytesIO object
            with open(tmp_file.name, 'rb') as f:
                audio_bytes = f.read()
            
            # Clean up temp file
            os.unlink(tmp_file.name)
            
            return audio_bytes
            
    except Exception as e:
        st.error(f"Audio generation failed: {str(e)}")
        return None

def create_download_options(content, content_type="text"):
    """Create download options for different formats"""
    downloads = {}
    
    if content_type == "text" and content:
        try:
            # Text file
            downloads['txt'] = content.encode('utf-8')
            
            # Markdown file
            downloads['md'] = f"# Gemini Response\n\n{content}".encode('utf-8')
            
            # JSON file
            data = {
                "response": content,
                "timestamp": datetime.now().isoformat()
            }
            downloads['json'] = json.dumps(data, indent=2).encode('utf-8')
        except Exception as e:
            st.error(f"Error creating downloads: {str(e)}")
    
    return downloads

def export_chat_history(messages, chat_id):
    """Export chat history as JSON"""
    try:
        if messages:
            # Create clean export data
            export_messages = []
            for msg in messages:
                clean_msg = {
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg.get("timestamp", datetime.now().isoformat())
                }
                export_messages.append(clean_msg)
            
            chat_data = {
                "chat_id": chat_id,
                "messages": export_messages,
                "export_timestamp": datetime.now().isoformat()
            }
            return json.dumps(chat_data, indent=2).encode('utf-8')
    except Exception as e:
        st.error(f"Export failed: {str(e)}")
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
            with st.spinner("Processing files..."):
                st.session_state.uploaded_files = []
                for file in uploaded_files:
                    try:
                        processed_content = st.session_state.gemini_chat.process_uploaded_file(file)
                        st.session_state.uploaded_files.append(processed_content)
                        st.success(f"✅ {file.name}")
                    except Exception as e:
                        st.error(f"❌ {file.name}: {str(e)}")
        
        # Advanced Features
        st.subheader("🚀 Advanced Features")
        
        # Smart Context Management
        with st.expander("🧠 Smart Context"):
            context_length = st.slider("Context Messages", 3, 20, 5)
            st.info("Maintains conversation context")
        
        # Multi-language Support
        with st.expander("🌐 Language Options"):
            audio_lang = st.selectbox("Audio Language", 
                ['en', 'es', 'fr', 'de', 'it', 'pt', 'hi', 'ja', 'ko', 'zh'])
        
        # Response Style
        with st.expander("✨ Response Style"):
            response_style = st.selectbox("Style", 
                ['Professional', 'Creative', 'Technical', 'Casual', 'Academic'])
        
        # Model Selection
        with st.expander("🤖 Model Options"):
            use_fast_mode = st.checkbox("Fast Mode", value=False)
            st.info("Optimizes for speed over detail")
        
        # Auto-save toggle
        with st.expander("💾 Storage Options"):
            auto_save = st.checkbox("Auto-save conversations", value=True)
            if st.button("Clear All History", type="secondary"):
                st.session_state.db.truncate()
                st.success("History cleared!")
        
        # Export Options
        st.subheader("💾 Export & Download")
        if st.session_state.messages:
            chat_export = export_chat_history(st.session_state.messages, st.session_state.chat_id)
            if chat_export:
                st.download_button(
                    "📥 Download Chat",
                    chat_export,
                    file_name=f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        # New Chat
        if st.button("🆕 New Chat", type="primary"):
            # Save current chat if auto-save is enabled
            if auto_save and st.session_state.messages:
                st.session_state.gemini_chat.save_chat_to_db(
                    st.session_state.messages, 
                    st.session_state.chat_id
                )
            
            st.session_state.messages = []
            st.session_state.chat_id = str(uuid.uuid4())
            st.session_state.uploaded_files = []
            st.rerun()
    
    # Main Chat Interface
    # Display Chat Messages
    for i, message in enumerate(st.session_state.messages):
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
            if "audio_bytes" in message and message["audio_bytes"]:
                st.audio(message["audio_bytes"])
            
            # Download options
            if message["content"]:
                downloads = create_download_options(message["content"])
                if downloads:
                    cols = st.columns(len(downloads))
                    for j, (format_type, data) in enumerate(downloads.items()):
                        with cols[j]:
                            st.download_button(
                                f"📥 {format_type.upper()}",
                                data,
                                file_name=f"response_{i}_{j}.{format_type}",
                                mime=f"text/{format_type}" if format_type != 'json' else "application/json",
                                key=f"download_{i}_{j}"
                            )
    
    # Chat Input
    prompt = st.chat_input("Ask Gemini anything... (supports image generation, file analysis, and more!)")
    
    if prompt:
        # Add user message
        user_message = {
            "role": "user", 
            "content": prompt,
            "timestamp": datetime.now().isoformat()
        }
        st.session_state.messages.append(user_message)
        
        # Show typing indicator and generate response
        with st.spinner("🧠 Gemini is thinking..."):
            try:
                # Prepare context and files
                context = st.session_state.messages[-context_length:] if len(st.session_state.messages) > 1 else None
                files = st.session_state.uploaded_files if st.session_state.uploaded_files else None
                
                # Add response style to prompt
                styled_prompt = f"[{response_style} style] {prompt}"
                if use_fast_mode:
                    styled_prompt = f"[Brief response] {styled_prompt}"
                
                # Generate response
                response, response_type = st.session_state.gemini_chat.generate_response(
                    styled_prompt, files, context
                )
                
                # Process response
                if response_type == "error":
                    response_text = response
                elif response_type == "image":
                    response_text = response.text if hasattr(response, 'text') else "Image generated successfully!"
                    # Handle image display here if needed
                else:
                    response_text = response.text if hasattr(response, 'text') else str(response)
                
                # Create audio
                audio_bytes = None
                if response_text and len(response_text.strip()) > 0:
                    audio_bytes = create_audio(response_text, audio_lang)
                
                # Add assistant message
                assistant_message = {
                    "role": "assistant", 
                    "content": response_text,
                    "timestamp": datetime.now().isoformat()
                }
                
                if audio_bytes:
                    assistant_message["audio_bytes"] = audio_bytes
                
                st.session_state.messages.append(assistant_message)
                
                # Auto-save to database
                if auto_save:
                    st.session_state.gemini_chat.save_chat_to_db(
                        st.session_state.messages, 
                        st.session_state.chat_id
                    )
                
            except Exception as e:
                error_message = {
                    "role": "assistant",
                    "content": f"I apologize, but I encountered an error: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
                st.session_state.messages.append(error_message)
        
        # Rerun to show new message
        st.rerun()

    # Footer
    st.markdown("---")
    st.markdown("### 🌟 Features: File Upload • Image Generation • Multi-language Audio • Smart Context • Export Options")
    
    # Stats
    if st.session_state.messages:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Messages", len(st.session_state.messages))
        with col2:
            st.metric("Files Uploaded", len(st.session_state.uploaded_files))
        with col3:
            try:
                total_chats = len(st.session_state.db.all())
                st.metric("Total Conversations", total_chats)
            except:
                st.metric("Total Conversations", "N/A")

if __name__ == "__main__":
    main()
