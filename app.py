import streamlit as st
import base64
import os
from google import genai
from google.genai import types


def save_binary_file(file_name, data):
    f = open(file_name, "wb")
    f.write(data)
    f.close()


def generate():
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.0-flash-exp-image-generation"
    
    # Option 1: If you have no previous image and want to start fresh
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="""Generate a serene mountain lake at sunset with reflections in the water, pine trees along the shore, and snow-capped peaks in the background. Style: photorealistic with warm lighting."""),
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

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        if not chunk.candidates or not chunk.candidates[0].content or not chunk.candidates[0].content.parts:
            continue
        if chunk.candidates[0].content.parts[0].inline_data:
            file_name = "generated_image.jpg"  # Replace with your desired filename
            save_binary_file(
                file_name, chunk.candidates[0].content.parts[0].inline_data.data
            )
            st.write(
                "File of mime type"
                f" {chunk.candidates[0].content.parts[0].inline_data.mime_type} saved"
                f" to: {file_name}"
            )
        else:
            st.write(chunk.text)


# A simple Streamlit button to trigger generation
if st.button("Generate Image"):
    generate()
