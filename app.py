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
        
        # Set up the generation config
        generation_config = {
            "temperature": 0.4,
            "top_p": 1,
            "top_k": 32,
        }
        
        # Set up model
        model = genai.GenerativeModel(
            model_name='gemini-2.0-flash-exp-image-generation',
            generation_config=generation_config
        )
        
        # Generate image
        response = model.generate_content(prompt)
        
        # Print response structure for debugging
        st.write("Response type:", type(response))
        st.write("Response dir:", dir(response))
        
        # Try to retrieve the image
        if hasattr(response, 'text'):
            st.write("Response text:", response.text)
        
        # For Gemini 2.0, images are typically returned as base64 in the .text field
        # Let's try to find and decode it
        if hasattr(response, 'text') and response.text:
            # Look for base64 data in the text
            import re
            base64_pattern = r'data:image\/[^;]+;base64,([^"]+)'
            match = re.search(base64_pattern, response.text)
            if match:
                base64_data = match.group(1)
                image_data = base64.b64decode(base64_data)
                return image_data
        
        # If we made it here, we didn't find an image
        st.error("Could not extract image from response.")
        return None
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None

# Main app interface
prompt = st.text_area("Enter your image description:", height=100, 
                     value="a landscape of mountains" if "prompt" not in st.session_state else st.session_state.prompt)

# Generate button
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
                try:
                    # Display the generated image
                    st.subheader("Generated Image")
                    img = Image.open(io.BytesIO(image_data))
                    st.image(img, use_column_width=True)
                    
                    # Add download button
                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format=img.format or 'PNG')
                    img_b64 = base64.b64encode(img_bytes.getvalue()).decode()
                    download_button = f'<a href="data:image/png;base64,{img_b64}" download="generated_image.png" target="_blank"><button style="background-color:#4CAF50;color:white;padding:10px 24px;border:none;border-radius:4px;cursor:pointer;">Download Image</button></a>'
                    st.markdown(download_button, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error displaying image: {str(e)}")
            else:
                st.error("Failed to generate image. Check the error messages above.")

# Example prompts
st.sidebar.markdown("### Example Prompts")
examples = [
    "A serene lake surrounded by mountains at sunset",
    "Futuristic cityscape with flying cars and neon lights",
    "A photorealistic cat wearing a space helmet"
]
for example in examples:
    if st.sidebar.button(example):
        st.session_state.prompt = example
        st.experimental_rerun()

# Usage instructions
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
