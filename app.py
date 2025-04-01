import streamlit as st
import google.generativeai as genai
import os
from PIL import Image
import io

# --- Page Configuration ---
st.set_page_config(
    page_title="Multimodal Chat App",
    page_icon="💬",
    layout="wide"
)

# --- Session State Initialization ---
# Stores the chat history for API calls (structured)
if "chat_context" not in st.session_state:
    st.session_state.chat_context = []
# Stores the chat history for UI display (simplified)
if "display_messages" not in st.session_state:
    st.session_state.display_messages = []
# To keep track of uploaded file objects across messages if needed, but
# here we will process them with each message input.

# --- Helper Function ---
def get_gemini_response(client, model, chat_history, prompt, uploaded_files):
    """
    Gets response from Gemini model, handling text and files.

    Args:
        client: Initialized GenerativeModel client.
        model: The selected model name.
        chat_history: List of previous turns for context.
        prompt: The user's text input for the current turn.
        uploaded_files: A list of Streamlit UploadedFile objects.

    Returns:
        A generator object for streaming the response, or None on error.
        Error message string if an error occurs before API call.
    """
    # --- Prepare input for the API ---
    current_turn_parts = []

    # 1. Add Text part (if prompt exists)
    if prompt:
        current_turn_parts.append(prompt)
    else:
        # If only files are uploaded, maybe add a default prompt? Or handle as needed.
        # For now, require text prompt. A user needs to *ask* something.
        if not uploaded_files: # No text AND no files, do nothing
             return None, "Please enter a message or upload files and ask a question."
        # If files are present but no text, maybe implicitly ask to describe?
        # current_turn_parts.append("Describe the content of the uploaded file(s).")


    # 2. Add File parts
    if uploaded_files:
        st.info(f"Processing {len(uploaded_files)} file(s)...")
        for uploaded_file in uploaded_files:
            try:
                # Get bytes from the file buffer
                bytes_data = uploaded_file.getvalue()
                file_info = {"mime_type": uploaded_file.type, "data": bytes_data}
                current_turn_parts.append(file_info)
                # --- Optional: Simple Image Display in Chat ---
                # Try to display image directly if it's a common type
                # Note: Large images might slow down the app
                if uploaded_file.type.startswith("image/"):
                     try:
                         img = Image.open(io.BytesIO(bytes_data))
                         # Could display here, but better to add to display message later
                         # st.image(img, caption=f"Uploaded: {uploaded_file.name}", width=150)
                     except Exception as img_err:
                         print(f"Could not display image {uploaded_file.name}: {img_err}") # Log error

            except Exception as e:
                st.error(f"Error reading file {uploaded_file.name}: {e}")
                return None, f"Failed to process file: {uploaded_file.name}"

    if not current_turn_parts:
         return None, "No input (text or files) provided." # Should not happen if checked above

    # --- Construct full context for API ---
    full_context_api = chat_history + [{"role": "user", "parts": current_turn_parts}]


    # --- Call the API ---
    try:
        # Check which model is used - vision models preferred for file analysis
        # Note: Newer models like gemini-1.5-flash/pro handle multimodal automatically
        print(f"Sending request to {model} with {len(full_context_api)} history turns.")
        # print("Last user turn parts:", current_turn_parts) # Debug: See what's being sent

        response = client.generate_content(
            full_context_api,
            stream=True,
            # generation_config=genai.types.GenerationConfig(...) # Optional
        )
        return response, None # Return the streaming generator
    except Exception as e:
        st.error(f"Gemini API Error: {e}")
        # Consider more specific error handling (Auth errors, Quota errors, etc.)
        return None, f"An error occurred while communicating with the Gemini API: {e}"


# --- Sidebar Elements ---
with st.sidebar:
    st.markdown("## 🔑 API Configuration")
    # Best practice: Use st.secrets for API keys in deployed apps
    # api_key_secrets = st.secrets.get("GOOGLE_API_KEY")
    # if api_key_secrets:
    #     api_key = api_key_secrets
    #     st.success("API Key loaded from secrets.", icon="✅")
    # else:
    #     api_key = st.text_input("Enter Google Gemini API Key:", type="password", help="Get your key from [Google AI Studio](https://aistudio.google.com/app/apikey)")
    # For local development/simplicity:
    api_key = st.text_input(
        "Enter Google Gemini API Key:",
        type="password",
        help="Get your key from [Google AI Studio](https://aistudio.google.com/app/apikey)",
        key="api_key_input" # Add a key for potential programmatic access
        )

    st.markdown("---")
    st.markdown("## ⚙️ Model Settings")
    # Add models known to support multimodal input if needed
    model_options = [
        "gemini-1.5-flash", # Good balance, multimodal
        "gemini-1.5-pro",   # Powerful, multimodal
        # "gemini-pro-vision", # Older vision-specific
        "gemini-1.0-pro",   # Text-only generally (might error with files)
    ]
    selected_model = st.selectbox("Select Model:", model_options, key="model_select")
    if "pro-vision" not in selected_model and "1.5" not in selected_model :
         st.warning("Selected model might not support file inputs directly.", icon="⚠️")

    st.markdown("---")
    st.markdown("## 📄 Chat Controls")
    if st.button("🆕 Start New Chat", use_container_width=True):
        st.session_state.chat_context = []
        st.session_state.display_messages = []
        st.success("New chat started!")
        # Optionally clear file uploader too, though it usually clears on button press/rerun
        if 'file_uploader' in st.session_state:
            st.session_state.file_uploader = [] # Try to clear (might need widget key)
        st.rerun()

    st.markdown("---")
    st.markdown(f"**API Context Length:** {len(st.session_state.chat_context)} turns")
    st.info(f"**Display History Length:** {len(st.session_state.display_messages)} messages")
    # API Key Status Indicator
    if api_key:
        st.success("API Key Entered.", icon="🔑")
        try:
            genai.configure(api_key=api_key)
            # Optional: Test connection lightly (e.g., list models)
            # genai.list_models()
        except Exception as e:
             st.error(f"Invalid API Key or configuration error: {e}", icon="❌")
             api_key = None # Nullify the key if invalid
    else:
        st.warning("Please enter your Google API Key.", icon="⚠️")


# --- Main Chat Interface ---
st.title("💬 Multimodal Chat App with Gemini")
st.caption(f"Using model: {selected_model} | Ask questions about text and uploaded files.")

# --- File Uploader Widget ---
# Important: Place *before* the chat input if you want files processed
# with the *next* text input submitted by the user.
uploaded_files_list = st.file_uploader(
    "Upload files (images, text, code, etc.)",
    accept_multiple_files=True,
    type=None, # Allow any file type (be cautious with execution)
    key="file_uploader_widget", # Unique key for the widget
    help="Upload files you want to discuss in your next message."
)

# --- Display Existing Chat History ---
for msg in st.session_state.display_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # Optional: If image data was stored, display it
        if msg.get("image"):
            try:
                st.image(msg["image"], width=250)
            except Exception as e:
                print(f"Error displaying stored image: {e}")

# --- Handle Chat Input from User ---
if prompt := st.chat_input("Enter your message here..."):

    # --- Basic Checks ---
    if not api_key:
        st.error("🚨 Please configure your Google API Key in the sidebar!")
        st.stop() # Halt execution if no API key

    # --- Prepare and Display User Message ---
    # 1. Combine Text and File Info for Display
    user_message_content_display = prompt
    user_images_for_display = [] # Store images to display with user message

    if uploaded_files_list:
        user_message_content_display += "\n\n*Attached Files:*\n"
        for uf in uploaded_files_list:
            user_message_content_display += f"- `{uf.name}` ({uf.type})\n"
            # Try to get image data for display with user message
            if uf.type.startswith("image/"):
                try:
                     # We need the bytes again here for display
                     img_bytes_display = uf.getvalue() # Read bytes again
                     user_images_for_display.append(img_bytes_display)
                except Exception as e:
                    print(f"Couldn't read image {uf.name} for display: {e}")

    # 2. Add to display history *before* API call
    st.session_state.display_messages.append({"role": "user", "content": user_message_content_display}) #"image": user_images_for_display # Add images if needed

    # 3. Display it in the chat UI
    with st.chat_message("user"):
        st.markdown(user_message_content_display)
        # Also display the uploaded images under the user message
        for img_data in user_images_for_display:
             try:
                st.image(img_data, width=200)
             except Exception as e:
                 st.error(f"Could not display uploaded image: {e}", icon="🖼️")


    # --- Prepare for and Call Gemini API ---
    try:
        # Initialize the GenerativeModel client *inside* the logic block
        # This ensures configuration uses the latest key from sidebar
        genai.configure(api_key=api_key)
        gemini_client = genai.GenerativeModel(selected_model)

        # Get the streaming response (or error message)
        stream_response, error_msg = get_gemini_response(
            client=gemini_client,
            model=selected_model,
            chat_history=st.session_state.chat_context,
            prompt=prompt,
            uploaded_files=uploaded_files_list # Pass the list from uploader
        )

        if error_msg:
            st.error(error_msg)
            # Optional: Remove the user message from history if API call prep failed?
            if len(st.session_state.display_messages) > 0:
                st.session_state.display_messages.pop()
            st.stop()

        # --- Process and Display Gemini's Streaming Response ---
        with st.chat_message("assistant"):
            response_placeholder = st.empty() # Use empty placeholder for stream
            full_response_text = ""
            try:
                if stream_response:
                    for chunk in stream_response:
                        # Handle potential API errors during streaming (e.g., safety filters)
                        if not hasattr(chunk, 'text'):
                           # Check for reasons like safety ratings
                            reason = chunk.prompt_feedback.block_reason if chunk.prompt_feedback else "Unknown reason"
                            if reason != 0: # 0 usually means OK or not specified
                                filter_info = chunk.prompt_feedback
                                full_response_text += f"\n\n⚠️ **Content filtered by API:** Reason: {reason} \n Safety Ratings: {filter_info.safety_ratings}"
                                st.warning(f"Part of the response may have been filtered due to: {reason}", icon="🛡️")
                           continue # Skip chunks without text

                        full_response_text += chunk.text
                        response_placeholder.markdown(full_response_text + "▌") # Append and show cursor

                    response_placeholder.markdown(full_response_text) # Final display without cursor
                else:
                     # This case should be caught by error_msg check earlier, but just in case
                     full_response_text = "Assistant Error: No response received."
                     response_placeholder.markdown(full_response_text)

            except Exception as stream_err:
                full_response_text += f"\n\nAn error occurred during streaming: {stream_err}"
                response_placeholder.error(full_response_text)

        # --- Update Histories after Successful Response ---
        # 1. Add final Assistant message to display history
        st.session_state.display_messages.append({"role": "assistant", "content": full_response_text})

        # 2. Update the API chat context
        # - Add the user turn parts (we prepared them earlier in get_gemini_response)
        api_user_parts = []
        if prompt: api_user_parts.append(prompt)
        # We need the file parts again here for the API context history
        processed_file_parts = []
        if uploaded_files_list:
             for uploaded_file in uploaded_files_list:
                 try:
                     bytes_data_hist = uploaded_file.getvalue() # Read again if necessary
                     processed_file_parts.append({"mime_type": uploaded_file.type, "data": bytes_data_hist})
                 except Exception as e:
                      print(f"Error re-reading file {uploaded_file.name} for history: {e}")
        api_user_parts.extend(processed_file_parts)

        st.session_state.chat_context.append({"role": "user", "parts": api_user_parts})

        # - Add the assistant turn parts (must match API response structure)
        # Gemini responses usually are [{"text": "..."}] for simple text. Check API docs if complex.
        st.session_state.chat_context.append({"role": "model", "parts": [{"text": full_response_text}]})


        # --- Clear uploaded files *list* after processing ---
        # This prevents the same files from being attached to the *next* message
        # unless the user explicitly re-uploads them or keeps them in the widget.
        # Streamlit's file uploader state can be tricky; clearing might require rerunning or more complex state handling.
        # For this version, let the user manage the uploader's state.
        # If you uncomment the below, it tries to clear the list used in this turn,
        # but the widget itself might retain the files visually.
        # uploaded_files_list = [] # Clear the list variable used in this turn

    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        # Optional: Attempt to rollback display/history if needed
        if st.session_state.display_messages and st.session_state.display_messages[-1]["role"] == "user":
            st.session_state.display_messages.pop() # Remove user msg from display if failure occurred after
        # History context update might be inconsistent here, might need more robust error handling logic

else:
    # Initial message or guidance when the chat input is empty
    if not st.session_state.display_messages:
        st.info("Enter a message and/or upload files to start chatting!")

# --- Optional: Display current file uploader state (for debugging) ---
# st.sidebar.write("Current Files in Uploader Widget:")
# st.sidebar.write(uploaded_files_list if uploaded_files_list else "None")
