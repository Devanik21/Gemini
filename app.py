import streamlit as st
import base64
import os
from google import genai
from google.genai import types
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
    os.environ["GEMINI_API_KEY"] = api_key

# Image generation function
def generate_image(prompt):
    try:
        client = genai.Client(
            api_key=os.environ.get("GEMINI_API_KEY"),
        )

        model = "gemini-2.0-flash-exp-image-generation"
        
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                ],
            ),
        ]
        
        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            response_modalities=[
                "image",
                "text",
            ],
            response_mime_type="text/plain",
        )

        image_data = None
        text_response = ""
        
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if not chunk.candidates or not chunk.candidates[0].content or not chunk.candidates[0].content.parts:
                continue
            if chunk.candidates[0].content.parts[0].inline_data:
                image_data = chunk.candidates[0].content.parts[0].inline_data.data
            else:
                text_response += chunk.text if chunk.text else ""
        
        return image_data, text_response
    
    except Exception as e:
        st.error(f"Error generating image: {str(e)}")
        return None, str(e)

# Main app interface
col1, col2 = st.columns([3, 2])

with col1:
    # Image prompt input
    prompt = st.text_area(
        "Describe the image you want to generate",
        "Generate a serene mountain lake at sunset with reflections in the water, pine trees along the shore, and snow-capped peaks in the background. Style: photorealistic with warm lighting.",
        height=150
    )
    
    # Generation settings
    with st.expander("Advanced Settings"):
        st.info("The default settings work well for most cases")
        # Add more settings here if needed

    # Generate button
    if st.button("Generate Image", type="primary"):
        if not api_key:
            st.warning("Please enter your Gemini API key in the sidebar")
        else:
            with st.spinner("Generating image..."):
                image_data, text_response = generate_image(prompt)
                
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
                    
                    # Display any text response
                    if text_response:
                        st.markdown("### Model Commentary")
                        st.write(text_response)

# Initialize session state for storing generated images
if 'image' not in st.session_state:
    st.session_state.image = None
if 'image_data' not in st.session_state:
    st.session_state.image_data = None

# Display previously generated image if it exists
if st.session_state.image and not st.button:
    with col2:
        st.image(st.session_state.image, caption="Generated Image", use_column_width=True)
        
        # Download button for previously generated image
        buf = io.BytesIO()
        st.session_state.image.save(buf, format="JPEG")
        byte_im = buf.getvalue()
        st.download_button(
            label="Download Image",
            data=byte_im,
            file_name="gemini_generated.jpg",
            mime="image/jpeg",
        )

# Instructions in the sidebar
st.sidebar.markdown("## Instructions")
st.sidebar.markdown("""
1. Enter your Gemini API key above
2. Write a detailed prompt for your image
3. Click 'Generate Image'
4. Download the resulting image
""")

st.sidebar.markdown("---")
st.sidebar.markdown("Built with Streamlit and Google's Gemini 2.0")
