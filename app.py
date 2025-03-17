import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import PyPDF2

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

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state["messages"] = []

st.title("🤖 Gemini Chat Clone")
st.write("Chat with AI continuously without losing context!")

# Display chat history
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        if "image" in message:
            st.image(message["image"], caption="Generated Image")
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
        except Exception as e:
            st.error(f"Error processing image: {e}")
    elif input_type == "Files":
        file_name = user_file.name
        st.session_state["messages"].append({"role": "user", "file": file_name})
        with st.chat_message("user"):
            st.write(f"📁 Uploaded file: {file_name}")
        
        # If the file is a PDF, extract its text automatically
        if file_name.lower().endswith(".pdf"):
            try:
                pdf_reader = PyPDF2.PdfReader(user_file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() or ""
                if text:
                    st.session_state["messages"].append({"role": "user", "content": text})
                    with st.chat_message("user"):
                        st.markdown("**Extracted PDF Content:**")
                        st.write(text[:500] + "..." if len(text) > 500 else text)
            except Exception as e:
                st.error(f"Error extracting PDF text: {e}")
        # For other file types, you might add other handling methods.

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
            
            # Add user message to history
            st.session_state["messages"].append({"role": "user", "content": query})
            
            # Display user message instantly
            with st.chat_message("user"):
                st.markdown(query)
            
            # Generate AI response
            with st.spinner("Thinking..."):
                response = model.generate_content(query)
            
            # Check if response contains an image
            if hasattr(response, "image"):
                image_data = response.image  # Extract image data
                image = Image.open(io.BytesIO(image_data))  # Convert to PIL image
                
                # Add image response to history
                st.session_state["messages"].append({"role": "assistant", "image": image})
                
                # Display image
                with st.chat_message("assistant"):
                    st.image(image, caption="Generated Image")
            else:
                # Add AI response to history
                ai_response = response.text.strip()
                st.session_state["messages"].append({"role": "assistant", "content": ai_response})
                
                # Display AI response
                with st.chat_message("assistant"):
                    st.markdown(ai_response)
        
        except Exception as e:
            st.error(f"❌ Error: {e}")
