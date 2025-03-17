import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

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
                # For image/file messages, show a placeholder text
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
            st.write(f"File: {message['file']}")
        else:
            st.markdown(message["content"])

# Input type selection with a + button
col1, col2 = st.columns([0.1, 0.9])
with col1:
    input_type = st.selectbox("+", ["Text", "Camera", "Gallery", "Files"], label_visibility="collapsed")

# Based on the input type, show the corresponding widget
user_input = None
if input_type == "Text":
    user_input = st.chat_input("Type your message...")
elif input_type == "Camera":
    # Open the device camera
    user_input = st.camera_input("Capture a photo")
elif input_type == "Gallery":
    # Open the gallery to select an image (only image files)
    user_file = st.file_uploader("Select an image from your gallery", type=["png", "jpg", "jpeg"])
    if user_file is not None:
        user_input = user_file
elif input_type == "Files":
    # Upload any file from the device
    user_file = st.file_uploader("Upload a file")
    if user_file is not None:
        user_input = user_file

# Process the input if available
if user_input:
    if input_type == "Text":
        # For text input, proceed with API call
        if not api_key:
            st.warning("⚠️ Please enter a valid Google Gemini API Key in the sidebar.")
        else:
            try:
                # Configure API
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(selected_model)
                
                # Add user text message to history
                st.session_state["messages"].append({"role": "user", "content": user_input})
                
                # Display user message instantly
                with st.chat_message("user"):
                    st.markdown(user_input)
                
                # Generate AI response
                with st.spinner("Thinking..."):
                    response = model.generate_content(user_input)
                
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
    elif input_type in ["Camera", "Gallery"]:
        # Process image input: display the image and add to chat history
        try:
            image = Image.open(user_input) if hasattr(user_input, "read") else user_input
            st.session_state["messages"].append({"role": "user", "image": image})
            with st.chat_message("user"):
                st.image(image, caption="User Image")
        except Exception as e:
            st.error(f"Error processing image: {e}")
    elif input_type == "Files":
        # For files, display the filename and add to chat history
        st.session_state["messages"].append({"role": "user", "file": user_input.name})
        with st.chat_message("user"):
            st.write(f"Uploaded file: {user_input.name}")
