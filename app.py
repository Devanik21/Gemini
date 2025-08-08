import streamlit as st
import google.generativeai as genai
from tinydb import TinyDB, Query
import json
import base64
import io
from PIL import Image
import tempfile
import os
import html # <--- ADD THIS LINE
from datetime import datetime
import re
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

# Custom CSS - Modern Dark Theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
    
    .stApp {
        background: #0a0a0b;
        color: #e8e9ea;
        font-family: 'Inter', sans-serif;
    }
    
    .main {
        background: #0a0a0b;
        padding: 0 !important;
    }
    
    .main-header {
        text-align: center;
        padding: 2rem 1rem;
        background: linear-gradient(135deg, #1e1e2e 0%, #2d3748 50%, #1a1a2e 100%);
        border-radius: 16px;
        margin-bottom: 2rem;
        color: #f7fafc;
        border: 1px solid #2d3748;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        backdrop-filter: blur(10px);
    }
    
    .main-header h1 {
        font-weight: 600;
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
        background: linear-gradient(135deg, #64b5f6 0%, #9c88ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .main-header p {
        color: #a0aec0;
        font-weight: 400;
    }
    
    .chat-message {
        padding: 1.25rem;
        border-radius: 12px;
        margin: 1.5rem 0;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
        transition: all 0.3s ease;
    }
    
    .chat-message:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #ffffff;
        margin-left: 15%;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .assistant-message {
        background: rgba(45, 55, 72, 0.6);
        border-left: 3px solid #64b5f6;
        color: #e8e9ea;
        margin-right: 15%;
    }
    
    .stSidebar {
        background: rgba(26, 32, 44, 0.95) !important;
        border-right: 1px solid #2d3748 !important;
    }
    
    .stSidebar .stSelectbox > div > div {
        background: rgba(45, 55, 72, 0.8);
        border: 1px solid #4a5568;
        color: #e8e9ea;
    }
    
    .stSidebar .stSlider > div > div {
        color: #e8e9ea;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4);
    }
    
    .stTextInput > div > div > input {
        background: rgba(45, 55, 72, 0.8);
        color: #e8e9ea;
        border: 1px solid #4a5568;
        border-radius: 8px;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #64b5f6;
        box-shadow: 0 0 0 2px rgba(100, 181, 246, 0.2);
    }
    
    .stFileUploader {
        background: rgba(45, 55, 72, 0.6);
        border: 2px dashed #4a5568;
        border-radius: 12px;
        padding: 2rem;
        transition: all 0.3s ease;
    }
    
    .stFileUploader:hover {
        border-color: #64b5f6;
        background: rgba(45, 55, 72, 0.8);
    }
    
    .stExpander {
        background: rgba(45, 55, 72, 0.4);
        border: 1px solid #4a5568;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    .stExpander > div > div {
        color: #e8e9ea;
    }
    
    .stMetric {
        background: rgba(45, 55, 72, 0.6);
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #4a5568;
    }
    
    .stMetric > div {
        color: #e8e9ea;
    }
    
    .stSuccess {
        background: rgba(72, 187, 120, 0.2);
        border: 1px solid #48bb78;
        color: #68d391;
    }
    
    .stError {
        background: rgba(245, 101, 101, 0.2);
        border: 1px solid #f56565;
        color: #fc8181;
    }
    
    .stInfo {
        background: rgba(99, 179, 237, 0.2);
        border: 1px solid #63b3ed;
        color: #90cdf4;
    }
    
    .stSpinner > div {
        border-color: #64b5f6;
    }
    
    /* Chat input styling */
    .stChatInput > div {
        background: rgba(45, 55, 72, 0.8) !important;
        border: 1px solid #4a5568 !important;
        border-radius: 12px !important;
    }
    
    .stChatInput input {
        background: transparent !important;
        color: #e8e9ea !important;
        border: none !important;
    }
    
    .stChatInput input::placeholder {
        color: #a0aec0 !important;
    }
    
    /* Download button styling */
    .stDownloadButton > button {
        background: rgba(45, 55, 72, 0.8);
        border: 1px solid #4a5568;
        color: #e8e9ea;
        border-radius: 6px;
        font-size: 0.8rem;
        padding: 0.4rem 0.8rem;
        transition: all 0.2s ease;
    }
    
    .stDownloadButton > button:hover {
        background: rgba(100, 181, 246, 0.2);
        border-color: #64b5f6;
        transform: translateY(-1px);
    }
    
    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #1a202c;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #4a5568;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #64b5f6;
    }
    
    /* Glassmorphism effect for cards */
    .glass-card {
        background: rgba(45, 55, 72, 0.25);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    /* Audio player styling */
    audio {
        width: 100%;
        height: 40px;
        background: rgba(45, 55, 72, 0.8);
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class GeminiChat:
    def __init__(self):
        self.api_key = st.secrets.get("GEMINI_API_KEY", "")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            # Use current, publicly available and capable models
            # gemini-1.5-flash is a fast, multimodal model for chat and analysis
            self.text_model = genai.GenerativeModel('gemini-2.0-flash')
            try:
                # Gemini 1.5 Pro is powerful and can generate images
                self.image_model = genai.GenerativeModel('gemini-2.5-flash')
            except Exception as e:
                st.warning(f"Could not initialize the image generation model: {e}")
                self.image_model = None
        
    def is_image_generation_request(self, prompt):
        """Check if prompt is for image generation"""
        image_keywords = ['create image', 'generate image', 'draw', 'imagine', 'visualize', 
                         'make a picture', 'design', 'create a graphic', 'illustrate']
        return any(keyword in prompt.lower() for keyword in image_keywords)
    
    def process_uploaded_file(self, uploaded_file):
        """Process different file types. Returns content as string or PIL Image."""
        try:
            file_extension = uploaded_file.name.split('.')[-1].lower()
            
            if file_extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                # For images, return a PIL Image object for the model to analyze
                image = Image.open(uploaded_file)
                return image
            
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
                content = df.head(100).to_string()
            elif file_extension == 'json':
                data = json.load(uploaded_file)
                content = json.dumps(data, indent=2)[:5000]
            
            return content[:10000]
        except Exception as e:
            # Return the error as a string so it can be displayed to the user
            return f"Error processing file {uploaded_file.name}: {str(e)}"

    def generate_response(self, prompt, files=None, context=None):
        """Generate response using Gemini API for image generation OR for analyzing text, files, and uploaded images."""
        try:
            # First, check if the user wants to CREATE an image.
            # This flow is separate from analyzing uploaded files.
            if self.is_image_generation_request(prompt) and self.image_model:
                try:
                    image_prompt = re.sub(r'\[.*?\]\s*', '', prompt).strip()
                    response = self.image_model.generate_content(image_prompt)
                    
                    if hasattr(response, 'parts') and any(p.mime_type.startswith("image/") for p in response.parts):
                        return response, "image" # Return type for image creation
                    else:
                        return response, "text"
                except Exception as e:
                    fallback_prompt = f"I tried to generate an image for '{prompt}', but an error occurred. Here is a text description instead: {prompt}"
                    fallback_response = self.text_model.generate_content(fallback_prompt)
                    return fallback_response, "text"

            # This is the flow for analyzing inputs (text, uploaded files, and uploaded images).
            model_input = []

            if context:
                context_text = "\n".join([f"{msg['role']}: {msg['content'][:500]}" for msg in context[-5:]])
                model_input.append(f"Context from conversation:\n{context_text}\n---")

            # Add uploaded files (text or images) to the model input
            if files:
                model_input.append("Please analyze the following uploaded file(s) to answer the user's request:")
                for file_content in files:
                    if isinstance(file_content, str):
                        model_input.append(f"--- File Content ---\n{file_content[:4000]}")
                    elif isinstance(file_content, Image.Image):
                        # Add the PIL image object directly to the input
                        model_input.append(file_content)
            
            # Add the user's prompt to the end of the input list
            model_input.append(f"\n--- User's Request ---\n{prompt}")
            
            # Generate a response from the combined multimodal input
            response = self.text_model.generate_content(model_input)
            return response, "text"
            
        except Exception as e:
            return f"Error: {str(e)}", "error"

    def save_chat_to_db(self, chat_data):
        """Save chat to TinyDB with serializable data only"""
        try:
            messages = chat_data.get('messages', [])
            chat_id = chat_data.get('chat_id', str(uuid.uuid4()))
            
            serializable_messages = []
            for msg in messages:
                # Exclude non-serializable data like image bytes before saving
                clean_msg = {
                    "role": msg["role"],
                    "content": msg["content"][:5000],
                    "timestamp": msg.get("timestamp", datetime.now().isoformat())
                }
                serializable_messages.append(clean_msg)
            
            clean_chat_data = {
                "chat_id": chat_id,
                "messages": serializable_messages,
                "timestamp": datetime.now().isoformat()
            }
            
            Chat = Query()
            st.session_state.db.remove(Chat.chat_id == chat_id)
            st.session_state.db.insert(clean_chat_data)
            
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
                chat_data = {
                    'messages': st.session_state.messages,
                    'chat_id': st.session_state.chat_id
                }
                st.session_state.gemini_chat.save_chat_to_db(chat_data)
            
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
            # --- DIAGNOSTIC STEP ---
            # By escaping the content, we're testing if special characters in the
            # model's response are confusing the HTML renderer. This will disable
            # markdown formatting like lists and bolding for this test.
            escaped_content = html.escape(message["content"])

            st.markdown(f"""
            <div class="chat-message assistant-message">
                <strong>🧠 Gemini:</strong> {escaped_content}
            </div>
            """, unsafe_allow_html=True)

            # Display generated image if it exists
            if "image_data" in message and message["image_data"]:
                st.image(message["image_data"], caption="Image generated by Gemini")

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
                                key=f"downloadmd3iiiiii3imiwod83ffffff4klq3n43_{i}_{j}"
                            )
            
            # Audio playback for assistant messages
          #  if "audio_bytes" in message and message["audio_bytes"]:
            #    st.audio(message["audio_bytes"])
            
            # Download options
            
    
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
                    chat_data = {
                        'messages': st.session_state.messages,
                        'chat_id': st.session_state.chat_id
                    }
                    st.session_state.gemini_chat.save_chat_to_db(chat_data)
                
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
