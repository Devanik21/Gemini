# --- START OF FILE gemini_file_chat.py ---

import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import PyPDF2
import docx
import os # To handle file extensions better

# --- Configuration ---
st.set_page_config(page_title="Gemini Chat with Files", page_icon="🤖", layout="wide")

# --- Helper Functions ---

def extract_text_from_pdf(file):
    """Extracts text from a PDF file."""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n" # Add newline between pages
        return text.strip() if text else "[No text found in PDF]"
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return None

def extract_text_from_txt(file):
    """Extracts text from a TXT file."""
    try:
        # Reset stream position just in case
        file.seek(0)
        # Decode assuming UTF-8, with error handling
        return file.read().decode("utf-8", errors='replace')
    except Exception as e:
        st.error(f"Error reading TXT file: {e}")
        return None

def extract_text_from_docx(file):
    """Extracts text from a DOCX file."""
    try:
        doc = docx.Document(file)
        text = ""
        # Extract text from paragraphs
        for para in doc.paragraphs:
            if para.text.strip():
                text += para.text + "\n"

        # Extract text from tables (basic)
        if doc.tables:
            text += "\n--- Tables ---\n"
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells)
                    if row_text:
                        text += row_text + "\n"
            text += "--- End Tables ---\n"

        return text.strip() if text else "[No text found in DOCX]"
    except Exception as e:
        st.error(f"Error reading DOCX file: {e}")
        return None

def get_file_details(uploaded_file):
    """Gets name and extension from uploaded file."""
    if uploaded_file is None:
        return None, None
    file_name = uploaded_file.name
    file_extension = os.path.splitext(file_name)[1].lower()
    return file_name, file_extension

# --- Session State Initialization ---
if "chat_context" not in st.session_state:
    # Stores the history in the format required by the Gemini API
    st.session_state.chat_context = []
if "display_messages" not in st.session_state:
    # Stores messages formatted for display in Streamlit chat UI
    st.session_state.display_messages = []

# --- Sidebar ---
with st.sidebar:
    st.markdown("## 🔑 API Configuration")
    # Best practice: Use st.secrets for API keys in deployed apps
    # api_key = st.secrets.get("GOOGLE_API_KEY")
    # if not api_key:
    #     api_key = st.text_input("Enter Google Gemini API Key:", type="password", help="Get your key from [Google AI Studio](https://aistudio.google.com/app/apikey)")
    # else:
    #     st.success("API Key loaded from secrets.", icon="✅")
    # For local development/simplicity:
    api_key = st.text_input("Enter Google Gemini API Key:", type="password", help="Get your key from [Google AI Studio](https://aistudio.google.com/app/apikey)")


    st.markdown("---")
    st.markdown("## ⚙️ Model Settings")
    # Add models known to support multimodal input if needed
    # e.g., "gemini-pro-vision" was common, newer models often combine capabilities
    model_options = [
        "gemini-1.5-flash", # Good balance of speed and capability, often multimodal
        "gemini-1.5-pro",   # More powerful, multimodal
        "gemini-1.0-pro",   # Text-only generally
        # Add other models you have access to if desired
    ]
    selected_model = st.selectbox("Select Model:", model_options)

    st.markdown("---")
    st.markdown("## 📄 Chat Controls")
    if st.button("🆕 Start New Chat", use_container_width=True):
        st.session_state.chat_context = []
        st.session_state.display_messages = []
        st.success("New chat started!")
        st.rerun() # Rerun to clear the chat display

    st.markdown("---")
    # Display info about the current chat length (optional)
    st.markdown(f"**Context Length:** {len(st.session_state.chat_context)} turns")


# --- Main Chat Interface ---
st.title("🤖 Gemini Chat with File Upload")
st.write("Upload PDF, TXT, DOCX, or Images (PNG, JPG) and chat about them!")

# Display existing messages (from display_messages)
for msg in st.session_state.display_messages:
    with st.chat_message(msg["role"]):
        # Render different content types
        if "image" in msg:
            st.image(msg["image"], width=250)
        if "text" in msg:
            st.markdown(msg["text"])
        if "file_info" in msg:
             st.info(msg["file_info"], icon="📁")


# --- File Uploader ---
uploaded_file = st.file_uploader(
    "Upload a file (PDF, TXT, DOCX, PNG, JPG)",
    type=["pdf", "txt", "docx", "png", "jpg", "jpeg"]
)

# Process uploaded file *immediately*
if uploaded_file is not None:
    file_name, file_extension = get_file_details(uploaded_file)
    bytes_data = uploaded_file.getvalue() # Read file bytes

    # Add a message to the display list *first*
    display_msg = f"Processing uploaded file: **{file_name}** ({file_extension})"
    st.session_state.display_messages.append({"role": "user", "text": display_msg})
    with st.chat_message("user"):
        st.markdown(display_msg)

    # Prepare content for the Gemini API context
    context_parts = []
    processed = False
    file_content_for_context = f"The user uploaded a file named '{file_name}'.\n"

    try:
        if file_extension == ".pdf":
            text = extract_text_from_pdf(io.BytesIO(bytes_data))
            if text:
                file_content_for_context += "Here is the extracted text content:\n---\n" + text + "\n---"
                context_parts.append(file_content_for_context)
                processed = True
            else:
                 st.warning(f"Could not extract text from {file_name}.")
                 context_parts.append(f"The user uploaded a PDF file named '{file_name}', but text extraction failed or it was empty.")
                 processed = True # Mark as processed even if empty/failed

        elif file_extension == ".txt":
            text = extract_text_from_txt(io.BytesIO(bytes_data))
            if text:
                file_content_for_context += "Here is the text content:\n---\n" + text + "\n---"
                context_parts.append(file_content_for_context)
                processed = True
            else:
                st.warning(f"{file_name} seems to be empty.")
                context_parts.append(f"The user uploaded an empty text file named '{file_name}'.")
                processed = True

        elif file_extension == ".docx":
            text = extract_text_from_docx(io.BytesIO(bytes_data))
            if text:
                file_content_for_context += "Here is the extracted text content:\n---\n" + text + "\n---"
                context_parts.append(file_content_for_context)
                processed = True
            else:
                st.warning(f"Could not extract text from {file_name} (it might be empty or structured unusually).")
                context_parts.append(f"The user uploaded a DOCX file named '{file_name}', but text extraction failed or it was empty.")
                processed = True

        elif file_extension in [".png", ".jpg", ".jpeg"]:
            # Requires a multimodal model
            if "pro" in selected_model or "flash" in selected_model: # Basic check, adjust if needed
                img = Image.open(io.BytesIO(bytes_data))
                # Add text description *and* the image object
                context_parts.append(f"The user uploaded an image named '{file_name}'.")
                context_parts.append(img) # Add the PIL Image object directly

                # Add image to display messages as well
                st.session_state.display_messages.append({"role": "user", "image": img})

                processed = True
            else:
                st.warning(f"Selected model '{selected_model}' might not support image input. Uploading info only.")
                context_parts.append(f"The user uploaded an image file named '{file_name}', but the current model may not process images.")
                processed = True

        else:
            # Handle unsupported file types gracefully
            st.warning(f"File type '{file_extension}' not fully supported for content extraction. Uploading file info only.")
            context_parts.append(f"The user uploaded a file named '{file_name}' of an unsupported type ({file_extension}).")
            processed = True

        # Add the processed content to the main chat context if successful
        if processed:
            st.session_state.chat_context.append({"role": "user", "parts": context_parts})
            st.success(f"File '{file_name}' processed and added to chat context.")
            # We clear the uploader by rerunning ONLY after successful processing
            st.rerun() # Rerun to clear the file uploader widget

    except Exception as e:
        st.error(f"An error occurred during file processing: {e}")
        # Optionally remove the "Processing..." message if it failed badly
        if st.session_state.display_messages and st.session_state.display_messages[-1]["text"].startswith("Processing"):
            st.session_state.display_messages.pop()


# --- Chat Input and Response Generation ---
prompt = st.chat_input("Ask about the file or start a new topic...")

if prompt:
    # 1. Add User Input to Display
    st.session_state.display_messages.append({"role": "user", "text": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Add User Input to API Context
    st.session_state.chat_context.append({"role": "user", "parts": [prompt]})

    # 3. Check for API Key
    if not api_key:
        st.warning("⚠️ Please enter your Google Gemini API Key in the sidebar to chat.")
        st.stop()

    # 4. Generate Response
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(selected_model)

        # --- Safety Settings (Optional) ---
        # You can customize these. See Google AI documentation.
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]

        # --- Generation Configuration (Optional) ---
        generation_config = genai.types.GenerationConfig(
            # temperature=0.7, # Example: Control randomness (0.0 = deterministic, 1.0 = creative)
            # max_output_tokens=2048, # Example: Limit response length
        )

        # Send the *entire* context history to the model
        with st.spinner("Gemini is thinking..."):
            response = model.generate_content(
                st.session_state.chat_context,
                stream=False, # Set to True for streaming response (more complex handling)
                safety_settings=safety_settings,
                generation_config=generation_config
            )

        # 5. Process and Display AI Response
        try:
            ai_response_text = response.text
            st.session_state.display_messages.append({"role": "assistant", "text": ai_response_text})
            # Add AI response to the API context for the next turn
            st.session_state.chat_context.append({"role": "model", "parts": [ai_response_text]})

            # Rerun to display the new AI message immediately
            st.rerun()

        except (ValueError, IndexError) as e:
             # Handle cases where the response might be blocked or empty
             st.error(f"Error processing response: {e}")
             st.error(f"Full response object: {response}") # Log the raw response for debugging
             # You might want to add a placeholder to the display/context
             blocked_msg = "[Response blocked or empty]"
             st.session_state.display_messages.append({"role": "assistant", "text": blocked_msg})
             st.session_state.chat_context.append({"role": "model", "parts": [blocked_msg]})
             st.rerun()
        except Exception as e:
            # Catch other potential errors during response handling
            st.error(f"An unexpected error occurred processing the response: {e}")


    except Exception as e:
        st.error(f"An error occurred while communicating with the Gemini API: {e}")
        # Optional: Remove the last user message from context if API call failed?
        # if st.session_state.chat_context and st.session_state.chat_context[-1]["role"] == "user":
        #     st.session_state.chat_context.pop()
        # if st.session_state.display_messages and st.session_state.display_messages[-1]["role"] == "user":
        #      st.session_state.display_messages.pop()


# --- Final check to ensure UI updates ---
# (st.rerun() is called after successful file processing or message generation,
# so this might not be strictly needed, but good for ensuring state consistency)
# st.experimental_rerun() # Use st.rerun() in newer versions

# --- END OF FILE gemini_file_chat.py ---
