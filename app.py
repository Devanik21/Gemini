import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import base64

# Set page config
st.set_page_config(page_title="Gemini Image Generator", layout="wide")

# Initialize the app with title
st.title("Text to Image Generator")
st.subheader("Powered by Google Gemini")

# API key input (with secure password input)
api_key = st.sidebar.text_input("Enter your Google API Key:", type="password")

# Function to generate image
def generate_image(prompt, api_key):
    try:
        # Configure the API
        genai.configure(api_key=api_key)
        
        # Set up model
        model = genai.GenerativeModel('gemini-2.0-flash-exp-image-generation')
        
        # Generate image
        response = model.generate_content(prompt)
        
        # Extract and return image data
        for part in response.parts:
            if part.mime_type.startswith('image/'):
                return part.data
                
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

# Main app interface
prompt = st.text_area("Enter your image description:", height=100)

# Image generation settings
col1, col2 = st.columns(2)
with col1:
    generate_button = st.button("Generate Image", type="primary")

# Generate image when button is clicked
if generate_button:
    if not api_key:
        st.warning("Please enter your Google API Key in the sidebar.")
    elif not prompt:
        st.warning("Please enter a description for the image.")
    else:
        with st.spinner("Generating image..."):
            image_data = generate_image(prompt, api_key)
            
            if image_data:
                # Display the generated image
                st.subheader("Generated Image")
                st.image(Image.open(io.BytesIO(image_data)), use_column_width=True)
                
                # Add download button
                img_bytes = io.BytesIO(image_data)
                img_b64 = base64.b64encode(img_bytes.getvalue()).decode()
                download_button = f'<a href="data:image/jpeg;base64,{img_b64}" download="generated_image.jpg" target="_blank"><button style="background-color:#4CAF50;color:white;padding:10px 24px;border:none;border-radius:4px;cursor:pointer;">Download Image</button></a>'
                st.markdown(download_button, unsafe_allow_html=True)
            else:
                st.error("Failed to generate image. Please try again with a different prompt.")

# Add some example prompts
st.sidebar.markdown("### Example Prompts")
examples = [
    "A serene lake surrounded by mountains at sunset",
    "Futuristic cityscape with flying cars and neon lights",
    "A photorealistic cat wearing a space helmet"
]
for example in examples:
    if st.sidebar.button(example):
        st.session_state.prompt = example
        st.rerun()

# Add usage instructions
st.sidebar.markdown("### How to use")
st.sidebar.markdown("""
1. Enter your Google API Key
2. Write a detailed description
3. Click 'Generate Image'
4. Download your created image
""")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("Using Google's Gemini 2.0 Flash Image Generation model")
