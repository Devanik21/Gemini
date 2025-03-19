import streamlit as st
import google.generativeai as genai
import base64
import io
from PIL import Image

# Configure Gemini API Key
API_KEY = "AIzaSyDuMuSDMX4A33NYki7lgs6x13uxbHirMQk"  # Replace with your actual API key
genai.configure(api_key=API_KEY)

# Streamlit UI
st.set_page_config(page_title="Dream Visualizer AI", layout="centered")
st.title("🔮 Dream Visualizer AI")
st.markdown("Enter your dream description, and AI will generate an image based on it!")

# Function to analyze dream using Gemini Pro
def analyze_dream(dream_text):
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(
            f"""Analyze this dream and create a detailed visual description that can be used 
            for image generation. Focus on visual elements, colors, mood, and composition. 
            Keep the description under 200 words and make it suitable for image generation: 
            {dream_text}"""
        )
        return response.text
    except Exception as e:
        return f"Error in analysis: {str(e)}"

# Function to generate dream image using Gemini's image generation model
def generate_dream_image(prompt):
    try:
        # Use the correct model for image generation
        model = genai.GenerativeModel("gemini-2.0-flash-exp-image-generation")
        
        # Configure generation parameters
        generation_config = {
            "temperature": 0.9,
            "top_p": 1,
            "top_k": 32,
            "max_output_tokens": 2048,
        }
        
        # Set the prompt to specifically request an image
        image_prompt = f"""Generate a photorealistic image based on this dream description: 
        {prompt}
        
        The image should be vivid, detailed, and capture the essence of the dream.
        """
        
        # Generate the content
        response = model.generate_content(
            image_prompt,
            generation_config=generation_config,
            stream=False
        )
        
        # Extract and decode the image data
        if hasattr(response, 'parts'):
            for part in response.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    if part.inline_data.mime_type.startswith('image/'):
                        return part.inline_data.data
        
        # If no image data is found, return an error message
        return "No image data found in the response. The model might not support image generation."
    
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
        if isinstance(image_result, str) and (image_result.startswith("Error") or image_result.startswith("No")):
            st.error(image_result)
            
            # Fallback to using a placeholder image
            st.subheader("Alternative Visualization:")
            st.info("Using a placeholder image service instead")
            
            # Create a safe query from the analyzed text
            safe_query = analyzed_text.replace(" ", "+")[:100]
            placeholder_url = f"https://source.unsplash.com/800x600/?{safe_query}"
            
            try:
                st.image(placeholder_url, caption="Alternative visualization based on your dream")
            except Exception as e:
                st.error(f"Failed to load placeholder image: {str(e)}")
        else:
            try:
                # Try to display the image using base64 data
                st.subheader("Dream Visualization:")
                st.image(image_result, caption="Your Dream, Visualized by AI")
            except Exception as e:
                st.error(f"Failed to display image: {str(e)}")
    else:
        st.warning("Please enter a dream description.")

# Add a footer
st.markdown("---")
st.markdown("Powered by Google Gemini AI")
