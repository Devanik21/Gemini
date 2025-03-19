import streamlit as st
import os
import google.generativeai as genai
import io
from PIL import Image

# Set page config
st.set_page_config(page_title="Gemini Image Generator", layout="wide")

# App title and description
st.title("Gemini 2.0 Image Generator")
st.markdown("Generate photorealistic images using Google's Gemini 2.0 model")

# API key input
api_key = st.sidebar.text_input("Enter your Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)

# Image generation function
def generate_image(prompt):
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")  # Use a valid Gemini model
        response = model.generate_content(prompt)
        
        if response and response.candidates:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image_data = part.inline_data.data
                    return image_data
        return None
    except Exception as e:
        st.error(f"Error generating image: {str(e)}")
        return None

# Main app interface
col1, col2 = st.columns([3, 2])

with col1:
    # Image prompt input
    prompt = st.text_area(
        "Describe the image you want to generate",
        "A serene mountain lake at sunset with reflections in the water, pine trees along the shore, and snow-capped peaks in the background.",
        height=150
    )

    # Generate button
    if st.button("Generate Image", type="primary"):
        if not api_key:
            st.warning("Please enter your Gemini API key in the sidebar")
        else:
            with st.spinner("Generating image..."):
                image_data = generate_image(prompt)
                
                if image_data:
                    # Convert binary data to image
                    image = Image.open(io.BytesIO(image_data))
                    
                    # Save to session state for download
                    st.session_state.image = image
                    st.session_state.image_data = image_data
                    
                    # Display image
                    with col2:
                        st.image(image, caption="Generated Image", use_column_width=True)
                        
                        # Download button
                        buf = io.BytesIO()
                        image.save(buf, format="JPEG")
                        byte_im = buf.getvalue()
                        st.download_button(
                            label="Download Image",
                            data=byte_im,
                            file_name="gemini_generated.jpg",
                            mime="image/jpeg",
                        )

# Display previously generated image if it exists
if 'image' in st.session_state and st.session_state.image:
    with col2:
        st.image(st.session_state.image, caption="Generated Image", use_column_width=True)
        
        # Download button
        buf = io.BytesIO()
        st.session_state.image.save(buf, format="JPEG")
        byte_im = buf.getvalue()
        st.download_button(
            label="Download Image",
            data=byte_im,
            file_name="gemini_generated.jpg",
            mime="image/jpeg",
        )

# Sidebar Instructions
st.sidebar.markdown("## Instructions")
st.sidebar.markdown("""
1. Enter your Gemini API key above  
2. Write a detailed prompt for your image  
3. Click 'Generate Image'  
4. Download the resulting image  
""")

st.sidebar.markdown("---")
st.sidebar.markdown("Built with Streamlit and Google's Gemini 2.0")
