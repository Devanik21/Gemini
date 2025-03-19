import streamlit as st
import google.generativeai as genai
import base64
import io
from PIL import Image
import requests

# Configure Gemini API Key
API_KEY = "AIzaSyDuMuSDMX4A33NYki7lgs6x13uxbHirMQk"
genai.configure(api_key=API_KEY)

# Streamlit UI
st.set_page_config(page_title="Dream Visualizer AI", layout="centered")
st.title("🔮 Dream Visualizer AI")
st.markdown("Enter your dream description, and AI will generate an image based on it!")

# Function to analyze dream using Gemini-2.0-Flash-Exp
def analyze_dream(dream_text):
    try:
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        response = model.generate_content(
            f"Analyze this dream and create a detailed visual description for image generation: {dream_text}"
        )
        return response.text
    except Exception as e:
        return f"Error in analysis: {str(e)}"

# Function to generate dream image using Gemini-2.0-Flash-Exp-Image-Generation
def generate_dream_image(prompt):
    try:
        model = genai.GenerativeModel("gemini-2.0-flash-exp-image-generation")  
        response = model.generate_content(
            f"Generate a vivid image based on this dream description: {prompt}"
        )
        
        # Check if response contains image data
        if hasattr(response, 'parts') and response.parts:
            for part in response.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    if part.inline_data.mime_type.startswith('image/'):
                        # Get base64 encoded image data
                        image_data = part.inline_data.data
                        return image_data
        
        # If we couldn't find image data, the response might be in another format
        # Return a message to help debugging
        return f"No valid image data found in response: {str(response)}"
    except Exception as e:
        return f"Error in image generation: {str(e)}"

# User Input
dream_text = st.text_area("Describe your dream:")

if st.button("Visualize My Dream ✨"):
    if dream_text:
        with st.spinner("Analyzing your dream..."):
            analyzed_text = analyze_dream(dream_text)
        
        st.subheader("Dream Interpretation:")
        st.write(analyzed_text)
        
        with st.spinner("Generating dream image..."):
            image_result = generate_dream_image(analyzed_text)
        
        # Handle the image result
        if isinstance(image_result, str) and image_result.startswith("Error") or image_result.startswith("No valid"):
            st.error(image_result)
        else:
            try:
                # Try to display the image using base64 data
                st.subheader("Dream Visualization:")
                st.image(image_result, caption="Your Dream, Visualized by AI")
            except Exception as e:
                st.error(f"Failed to display image: {str(e)}")
                
                # Fallback - provide base64 string that can be used elsewhere
                st.code(f"Base64 image data: {image_result[:50]}...")
    else:
        st.warning("Please enter a dream description.")
