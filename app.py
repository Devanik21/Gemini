import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import PyPDF2
import docx
# Configure the Streamlit page
st.set_page_config(page_title="Gemini Chat Clone", page_icon="🤖", layout="wide")

# Sidebar for API Key and Controls
with st.sidebar:
    st.markdown("### 🔑 API Configuration")
    api_key = st.text_input("Enter Google Gemini API Key:", type="password")
    
    # Model Selection
    model_options = [
        "gemini-2.0-flash",
        "gemini-2.0-flash-exp-image-generation",
        "gemini-2.0-flash-lite",
        "gemini-2.0-pro-exp-02-05",
        "gemini-2.0-flash-thinking-exp-01-21"
    ]
    selected_model = st.selectbox("🤖 Select Model:", model_options)
    
    # New Chat Button
    if st.button("🆕 Start New Chat"):
        st.session_state["messages"] = []
        st.session_state["chat_history"] = []
        st.rerun()
    
    # Chat History Button
    if st.button("📜 View Chat History"):
        st.markdown("### 📝 Chat History")
        if st.session_state["messages"]:
            for message in st.session_state["messages"]:
                role = "User" if message["role"] == "user" else "AI"
                content = message.get("content", "[Image/File]")
                st.write(f"**{role}:** {content}")
        else:
            st.info("No chat history available.")

# Initialize session state for chat history and API chat session
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

if "file_content" not in st.session_state:
    st.session_state["file_content"] = None

st.title("🤖 Gemini Chat Clone")
st.write("Chat with AI continuously without losing context!")

# Display chat history
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        if "image" in message:
            st.image(message["image"], caption="User Image")
        elif "file" in message:
            st.write(f"📁 File: {message['file']}")
        else:
            st.markdown(message["content"])

# Input type selection with a + button
col1, col2 = st.columns([0.1, 0.9])
with col1:
    input_type = st.selectbox("+", ["Text", "Camera", "Gallery", "Files"], label_visibility="collapsed")

user_input = None
user_file = None

# Based on the input type, show the corresponding widget
if input_type == "Text":
    user_input = st.chat_input("Type your message...")
elif input_type == "Camera":
    user_file = st.camera_input("Capture a photo")
elif input_type == "Gallery":
    user_file = st.file_uploader("Select an image from your gallery", type=["png", "jpg", "jpeg"])
elif input_type == "Files":
    user_file = st.file_uploader("Upload a file", type=["pdf", "txt", "docx", "png", "jpg", "jpeg"])

# Process the uploaded file/image before taking input
if user_file is not None:
    if input_type in ["Camera", "Gallery"]:
        try:
            image = Image.open(user_file)
            st.session_state["messages"].append({"role": "user", "image": image})
            with st.chat_message("user"):
                st.image(image, caption="User Image")
                
            # Store image content for the model context
            if "chat_history" not in st.session_state:
                st.session_state["chat_history"] = []
            
            # Add image to chat history for context
            # Note: Actual implementation would require multimodal support
            st.session_state["chat_history"].append({"role": "user", "content": "[Image uploaded]"})
                
        except Exception as e:
            st.error(f"Error processing image: {e}")
    elif input_type == "Files":
        file_name = user_file.name
        file_extension = file_name.lower().split('.')[-1] if '.' in file_name else ''
        
        st.session_state["messages"].append({"role": "user", "file": file_name})
        with st.chat_message("user"):
            st.write(f"📁 File: {file_name}")
        
        # Initialize chat history if it doesn't exist
        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []
            
        # Handle different file types
        text = ""
        
        # PDF files
        if file_extension == "pdf":
            try:
                pdf_reader = PyPDF2.PdfReader(user_file)
                for page in pdf_reader.pages:
                    text += page.extract_text() or ""
            except Exception as e:
                st.error(f"Error extracting PDF text: {e}")
        
        # Text files
        elif file_extension in ["txt", "text"]:
            try:
                text = user_file.getvalue().decode('utf-8')
            except Exception as e:
                st.error(f"Error reading text file: {e}")
        
        # DOCX files (would need python-docx library)
        elif file_extension == "docx":
            st.warning("DOCX support requires additional setup. Please install python-docx library.")
            text = "DOCX file content would be processed here. To enable DOCX support, add: `import docx` and extract text with the docx library."
        
        # Handle images
        elif file_extension in ["png", "jpg", "jpeg"]:
            try:
                image = Image.open(user_file)
                st.session_state["messages"].append({"role": "user", "image": image})
                with st.chat_message("user"):
                    st.image(image, caption="User Image")
                
                # Add image context
                st.session_state["chat_history"].append({
                    "role": "user", 
                    "content": f"I've uploaded an image file named '{file_name}'."
                })
                # Removed the invalid 'return' statement that was here
                # Instead, we'll use a conditional to skip the rest of this block
                text = ""  # Set empty text to indicate we've handled the image
            except Exception as e:
                st.error(f"Error processing image: {e}")
                text = f"[Failed to process image: {file_name}]"
        
        # Default handling for unsupported file types
        else:
            text = f"[Uploaded file: {file_name}. This file type isn't fully supported for text extraction.]"
        
        # Process extracted text (for all text-based files)
        if text:
            # Store the extracted text in session state for context
            st.session_state["file_content"] = text
            
            # Add file content to display history
            content_preview = text[:500] + "..." if len(text) > 500 else text
            st.session_state["messages"].append({"role": "user", "content": f"**Extracted Content from {file_name}:**\n{content_preview}"})
            
            with st.chat_message("user"):
                st.markdown(f"**Extracted Content from {file_name}:**")
                st.write(content_preview)
            
            # Add to model context history
            st.session_state["chat_history"].append({
                "role": "user", 
                "content": f"I've uploaded a file named '{file_name}'. Here's the content:\n\n{text}"
            })

# Keep chat input always visible for follow-up queries
query = st.chat_input("Ask a question about your file, image, or continue chatting...")

if query:
    if not api_key:
        st.warning("⚠️ Please enter a valid Google Gemini API Key in the sidebar.")
    else:
        try:
            # Configure API
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(selected_model)
            
            # Add user message to history for display
            st.session_state["messages"].append({"role": "user", "content": query})
            
            # Add user message to chat history for context
            st.session_state["chat_history"].append({"role": "user", "content": query})
            
            # Display user message instantly
            with st.chat_message("user"):
                st.markdown(query)
            
            # Generate AI response with full context
            with st.spinner("Thinking..."):
                # Create a formatted chat history for the model
                formatted_history = []
                for msg in st.session_state["chat_history"]:
                    # Format messages for the gemini API
                    formatted_history.append({
                        "role": "user" if msg["role"] == "user" else "model",
                        "parts": [msg["content"]]
                    })
                
                # Use the chat method to maintain context
                chat = model.start_chat(history=formatted_history)
                response = chat.send_message(query)
            
            # Process the response
            try:
                # Extract the text response - this is the primary method that should work in most cases
                ai_response = response.text.strip()
                
                # Add AI response to history
                st.session_state["messages"].append({"role": "assistant", "content": ai_response})
                
                # Add to model context history
                st.session_state["chat_history"].append({"role": "assistant", "content": ai_response})
                
                # Display AI response
                with st.chat_message("assistant"):
                    st.markdown(ai_response)
                    
            except Exception as e:
                st.error(f"❌ Error processing response: {e}")
                st.error("The model response couldn't be properly processed.")
                
                # Display AI response
                with st.chat_message("assistant"):
                    st.markdown(ai_response)
        
        except Exception as e:
            st.error(f"❌ Error: {e}")
            st.error(f"Details: {str(e)}")
