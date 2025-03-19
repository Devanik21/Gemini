import streamlit as st
import google.generativeai as genai
import base64
import re

# Configure Gemini API Key
API_KEY = "AIzaSyDuMuSDMX4A33NYki7lgs6x13uxbHirMQk"
genai.configure(api_key=API_KEY)

# Streamlit UI
st.set_page_config(page_title="Dream Visualizer AI", layout="centered")
st.title("🔮 Dream Visualizer AI")
st.markdown("Enter your dream description, and AI will generate an image based on it!")

# Function to generate AI text analysis of dream using Gemini-2.0-Flash-Exp
def analyze_dream(dream_text):
    try:
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        response = model.generate_content(dream_text)
        return response.text
    except Exception as e:
        return f"Error in analysis: {str(e)}"

# Function to generate dream image using Gemini-2.0-Flash-Exp-Image-Generation
def generate_dream_image(prompt):
    try:
        model = genai.GenerativeModel("gemini-2.0-flash-exp-image-generation")
        response = model.generate_content(prompt)
        if response.parts:
            return response.parts[0].text  # Expected to be an image URL or base64 encoded image
        else:
            return "Error: No image generated"
    except Exception as e:
        return f"Error in image generation: {str(e)}"

# Helper function to check if the result is a valid image URL or base64 image data
def is_valid_image(content):
    # Check if content is a URL that ends with an image extension
    if content.startswith("http") and re.search(r'\.(jpg|jpeg|png|gif)$', content, re.IGNORECASE):
        return True
    # Check if content is a base64 image data URL
    if content.startswith("data:image/"):
        return True
    return False

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
        
        # Validate if the output is a proper image
        if is_valid_image(image_result):
            st.subheader("Dream Visualization:")
            st.image(image_result, caption="Your Dream, Visualized by AI", use_column_width=True)
        else:
            st.error("Image generation did not return a valid image. Output:\n" + image_result)
    else:
        st.warning("Please enter a dream description.")
