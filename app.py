import streamlit as st
import google.generativeai as genai
import base64

# Configure Gemini API Key
API_KEY = "your_gemini_api_key_here"
genai.configure(api_key=API_KEY)

# Streamlit UI
st.set_page_config(page_title="Dream Visualizer AI", layout="centered")
st.title("🔮 Dream Visualizer AI")
st.markdown("Enter your dream description, and AI will generate an image based on it!")

# Function to generate AI text analysis of dream
def analyze_dream(dream_text):
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(dream_text)
        return response.text
    except Exception as e:
        return f"Error in analysis: {str(e)}"

# Function to generate dream image using Gemini-2.0-Flash-Exp-Image-Generation
def generate_dream_image(prompt):
    try:
        model = genai.GenerativeModel("gemini-2.0-flash-exp")  # Alias for Gemini-2.0-Flash-Exp-Image-Generation
        response = model.generate_content(prompt)
        if response.parts:
            return response.parts[0].text  # Image URL or base64 content
        else:
            return "Error: No image generated"
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
        
        if "Error" not in image_result:
            st.subheader("Dream Visualization:")
            st.image(image_result, caption="Your Dream, Visualized by AI", use_column_width=True)
        else:
            st.error(image_result)
    else:
        st.warning("Please enter a dream description.")

# Run the app using: streamlit run your_script.py
