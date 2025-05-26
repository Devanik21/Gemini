import streamlit as st
import google.generativeai as genai
import os
import time
from datetime import datetime
import pandas as pd

# Custom modules
from config import (
    DEFAULT_MODEL_NAME, FILE_ANALYSIS_MODEL_NAME, DEFAULT_GENERATION_CONFIG,
    SUPPORTED_TRANSLATION_LANGUAGES, SUPPORTED_FILE_UPLOAD_TYPES,
    CHAT_MODES, FILE_CHAT_MODES, UPLOAD_DIR
)
from styles import (
    get_gradient_title_style, get_animated_greeting_style,
    get_theme_styling, get_file_upload_title_style, get_footer_style
)
from prompts import get_chat_mode_system_prompt, get_file_chat_system_prompt
from file_utils import export_to_pdf, export_to_json

# Page settings
st.set_page_config(page_title="Gemini", layout="wide", page_icon="💎")

# --- Helper Functions ---
def initialize_model(model_name, generation_config, history=None):
    if history is None:
        history = []
    return genai.GenerativeModel(model_name=model_name, generation_config=generation_config).start_chat(history=history)

# Mode selection
app_mode = st.radio("Choose Mode:", ["Chat", "File Upload(Beta)"])

if app_mode == "Chat":
    st.markdown(get_gradient_title_style(), unsafe_allow_html=True)

    name = st.text_input("Please enter your name", value=" ")
    if name.strip():
        st.markdown(get_animated_greeting_style(name.strip()), unsafe_allow_html=True)

    # Initialize session data for settings and themes
    if "settings" not in st.session_state:
        st.session_state.settings = {
            "temperature": 0.7,
            "top_k": 40,
            "top_p": 0.95,
            "max_tokens": DEFAULT_GENERATION_CONFIG["max_output_tokens"]
        }

    if "theme" not in st.session_state:
        st.session_state.theme = "light"

    if "favorites" not in st.session_state:
        st.session_state.favorites = []

    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = {}

    if "api_key" not in st.session_state:
        st.session_state.api_key = None

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Apply theme initially
    st.markdown(get_theme_styling(st.session_state.theme), unsafe_allow_html=True)

    # Theme toggle function
    def toggle_theme():
        st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
        st.markdown(get_theme_styling(st.session_state.theme), unsafe_allow_html=True)
        st.rerun() # Rerun to apply style changes immediately

    # Sidebar - API, Chat Mode, Clear, Settings
    with st.sidebar:
        st.header("🔐 Gemini API Settings")
        # Use a single API key input, store in session state
        current_api_key = st.text_input("Enter your Gemini API key:", type="password", value=st.session_state.api_key or "")
        if current_api_key != st.session_state.api_key:
            st.session_state.api_key = current_api_key
            if current_api_key:
                try:
                    genai.configure(api_key=current_api_key)
                    st.success("API key configured!", icon="✅")
                    # Re-initialize chat if API key changes and is valid
                    if "chat" in st.session_state: del st.session_state.chat
                except Exception as e:
                    st.error(f"Invalid API Key: {e}")
                    st.session_state.api_key = None # Reset if invalid
            else:
                st.warning("API key removed.", icon="ℹ️")

        st.markdown("---")
        chat_mode = st.selectbox(
            "🧠 Select Chat Mode",
            CHAT_MODES,
            index=CHAT_MODES.index(st.session_state.get("chat_mode", "Normal")) # Persist selection
        )
        st.session_state.chat_mode = chat_mode # Store selection

        st.markdown("---")
        # New feature: Save/Load conversation
        st.header("💾 Conversation Management")
        save_name = st.text_input("Conversation name:")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 Save Chat"):
                if save_name and len(st.session_state.messages) > 0:
                    st.session_state.conversation_history[save_name.strip()] = {
                        "messages": st.session_state.messages.copy(),
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    st.success(f"Saved as '{save_name}'")
                else:
                    st.error("Please enter a name and ensure chat has messages")
        
        with col2:
            if st.button("🧹 Clear Chat"):
                st.session_state.messages = []
                if "chat" in st.session_state:
                    del st.session_state.chat
                # No need to re-initialize chat here, it will be done before sending message if needed
                st.success("Chat history cleared!")

        # Load saved conversation
        if st.session_state.conversation_history:
            st.markdown("---")
            st.subheader("📚 Saved Conversations")
            selected_chat = st.selectbox("Select a conversation:", 
                                        options=list(st.session_state.conversation_history.keys()),
                                        format_func=lambda x: f"{x} ({st.session_state.conversation_history[x]['timestamp']})")
            
            if st.button("📂 Load Selected Chat"):
                if selected_chat:
                    st.session_state.messages = st.session_state.conversation_history[selected_chat]["messages"].copy()
                    if "chat" in st.session_state: del st.session_state.chat # Reset chat to use new history
                    # Chat will be re-initialized with new history on next message
                    st.success(f"Loaded conversation: {selected_chat}")
                    st.rerun()

        st.markdown("---")
        
        # Export options
        st.header("📤 Export Options")
        export_pdf = st.button("Export Last Response to PDF")
        export_json = st.button("Export All as JSON")
        
        # Theme toggle
        st.markdown("---")
        st.header("🎨 Appearance")
        if st.button("Toggle Dark/Light Mode"):
            toggle_theme()
        
        # Advanced model settings
        st.markdown("---")
        st.header("⚙️ Advanced Settings")
        with st.expander("Model Parameters"):
            st.session_state.settings["temperature"] = st.slider(
                "Temperature", min_value=0.0, max_value=1.0, 
                value=st.session_state.settings["temperature"], step=0.1,
                help="Higher values make output more random, lower values more deterministic"
            )
            st.session_state.settings["top_p"] = st.slider(
                "Top P", min_value=0.0, max_value=1.0, 
                value=st.session_state.settings["top_p"], step=0.05,
                help="Controls diversity via nucleus sampling"
            )
            st.session_state.settings["max_tokens"] = st.slider(
                "Max Output Tokens", min_value=256, max_value=8192, 
                value=st.session_state.settings["max_tokens"], step=256,
                help="Maximum length of generated text"
            )

        if not st.session_state.api_key:
            st.warning("Enter Gemini API key to begin", icon="⚠️")

    # Initialize chat model if API key is set and chat object doesn't exist or history is empty
    if st.session_state.api_key and ("chat" not in st.session_state or not st.session_state.chat.history):
        try:
            current_gen_config = {
                "max_output_tokens": st.session_state.settings["max_tokens"],
                "temperature": st.session_state.settings["temperature"],
                "top_p": st.session_state.settings["top_p"],
                "top_k": st.session_state.settings["top_k"] # Ensure top_k is part of settings if used
            }
            st.session_state.chat = initialize_model(DEFAULT_MODEL_NAME, current_gen_config, history=st.session_state.messages)
        except Exception as e:
            st.error(f"Failed to initialize chat model: {e}")

    # Show chat history
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
            # Add favorite button for assistant messages
            if msg["role"] == "assistant":
                if st.button("⭐ Favorite", key=f"fav_{i}"):
                    if msg["content"] not in [f["content"] for f in st.session_state.favorites]:
                        st.session_state.favorites.append({
                            "content": msg["content"],
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "mode": chat_mode
                        })
                        st.success("Added to favorites!")
                        time.sleep(1)
                        st.rerun()

    # Show favorites in a collapsed section
    if st.session_state.favorites:
        with st.expander("⭐ Your Favorites"):
            for i, fav in enumerate(st.session_state.favorites):
                st.markdown(f"**{i+1}. [{fav['mode']}] - {fav['timestamp']}**")
                st.markdown(fav["content"])
                if st.button("Remove", key=f"remove_fav_{i}"):
                    st.session_state.favorites.pop(i)
                    st.success("Removed from favorites!")
                    time.sleep(1)
                    st.rerun()
                st.markdown("---")

    # Chat input
    if st.session_state.api_key:
        # Add a typing effect toggle
        typing_effect = st.checkbox("Enable typing effect for responses", value=False)
        target_language = None # Initialize

        # Add language selection for Translation Mode
        if chat_mode == "Translation Helper":
            target_language = st.selectbox(
                "Translate to:", 
                SUPPORTED_TRANSLATION_LANGUAGES
            )
        
        # Add a file selection option to use with chat if files are uploaded
        selected_chat_file_info = None
        if "uploaded_files" in st.session_state and st.session_state.uploaded_files:
            st.markdown("### Use Uploaded Files")
            file_options = ["None"] + [f"{file['name']}" for file in st.session_state.uploaded_files]
            selected_chat_file = st.selectbox("Select a file to discuss:", file_options)
            if selected_chat_file_name != "None":
                selected_chat_file_info = next((f for f in st.session_state.uploaded_files if f['name'] == selected_chat_file_name), None)
                if selected_chat_file_info:
                    st.info(f"Context from '{selected_chat_file_info['name']}' can be used by the AI.")
        
        user_prompt = st.chat_input("Ask anything 💬")

        if user_prompt:
            st.chat_message("user").markdown(user_prompt)
            st.session_state.messages.append({"role": "user", "content": user_prompt})

            system_prompt = get_chat_mode_system_prompt(user_prompt, chat_mode, target_language, selected_chat_file_info)

            # Show a spinner while loading
            with st.spinner("Gemini is thinking..."):
                try:
                    # Ensure chat is initialized with current history and settings
                    if "chat" not in st.session_state or not st.session_state.chat.history:
                         current_gen_config = {
                            "max_output_tokens": st.session_state.settings["max_tokens"],
                            "temperature": st.session_state.settings["temperature"],
                            "top_p": st.session_state.settings["top_p"],
                            "top_k": st.session_state.settings["top_k"]
                        }
                         st.session_state.chat = initialize_model(DEFAULT_MODEL_NAME, current_gen_config, history=st.session_state.messages)
                    
                    # Update model generation config if settings changed
                    st.session_state.chat.model.generation_config = genai.types.GenerationConfig(
                        max_output_tokens=st.session_state.settings["max_tokens"],
                        temperature=st.session_state.settings["temperature"],
                        top_p=st.session_state.settings["top_p"],
                        top_k=st.session_state.settings["top_k"]
                    )

                    response = st.session_state.chat.send_message(system_prompt)
                    reply = response.text

                except genai.types.generation_types.BlockedPromptException as e:
                    st.error(f"Your prompt was blocked. Reason: {e}")
                    reply = "My apologies, I cannot respond to that prompt as it was blocked."
                except google.api_core.exceptions.PermissionDenied as e:
                    st.error(f"API Key Error: Permission denied. Please check your API key. Details: {e}")
                    reply = "Error: API permission issue."
                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}")
                    reply = f"Sorry, an error occurred: {str(e)}"

                # Typing effect simulation
                if typing_effect and reply:
                    with st.chat_message("assistant"):
                        message_placeholder = st.empty()
                        full_response = ""
                        for chunk in reply.split(): # Simple chunking by word
                            full_response += chunk + " "
                            message_placeholder.markdown(full_response + "▌")
                            time.sleep(0.03) # Adjust typing speed
                        message_placeholder.markdown(reply)
                elif reply:
                    st.chat_message("assistant").markdown(reply)

                if reply:
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                    st.session_state.last_reply = reply # Save last reply for PDF export

    # Export last response to PDF
    if export_pdf:
        if "last_reply" in st.session_state:
            filename = export_to_pdf(st.session_state.last_reply)
            with open(filename, "rb") as f:
                st.download_button(
                    label="📄 Download PDF",
                    data=f,
                    file_name=filename,
                    mime="application/pdf"
                )
        else:
            st.warning("No reply available to export yet.")

    # Export all conversation to JSON
    if export_json:
        if st.session_state.messages:
            filename = export_to_json(st.session_state.messages, chat_mode=chat_mode)
            with open(filename, "rb") as f:
                st.download_button(
                    label="📄 Download JSON",
                    data=f,
                    file_name=filename,
                    mime="application/json"
                )
        else:
            st.warning("No conversation available to export yet.")

    # Display system status in footer
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption(f"Theme: {st.session_state.theme.capitalize()}")
    with col2:
        st.caption(f"Mode: {chat_mode}")
    with col3:
        st.caption(f"Temperature: {st.session_state.settings['temperature']}")

else:  # File Upload mode
    st.markdown(get_file_upload_title_style(), unsafe_allow_html=True)

    # Initialize session state for uploaded files
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = []
    if "file_messages" not in st.session_state:
        st.session_state.file_messages = []
    if "api_key" not in st.session_state: # Ensure api_key is initialized for this mode too
        st.session_state.api_key = None

    # Apply theme initially
    if "theme" not in st.session_state: st.session_state.theme = "light" # Default theme
    st.markdown(get_theme_styling(st.session_state.theme), unsafe_allow_html=True)

    def toggle_file_mode_theme(): # Separate theme toggle if needed, or use global
        st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
        st.markdown(get_theme_styling(st.session_state.theme), unsafe_allow_html=True)
        st.rerun()

    # Initialize file_chat model
    if st.session_state.api_key and "file_chat" not in st.session_state:
        try:
            st.session_state.file_chat = initialize_model(
                FILE_ANALYSIS_MODEL_NAME,
                DEFAULT_GENERATION_CONFIG, # Use default or make specific config for file chat
                history=st.session_state.file_messages
            )
        except Exception as e:
            st.error(f"Failed to initialize file chat model: {e}")

    # Create upload directory if it doesn't exist
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

    # API Key field in sidebar for file mode
    with st.sidebar:
        st.header("🔐 Gemini API Settings")
        # Use the same API key logic as Chat mode for consistency
        current_api_key_file = st.text_input("Enter your Gemini API key:", type="password", value=st.session_state.api_key or "", key="file_api_key_input")
        if current_api_key_file != st.session_state.api_key:
            st.session_state.api_key = current_api_key_file
            if current_api_key_file:
                try:
                    genai.configure(api_key=current_api_key_file)
                    st.success("API key configured!", icon="✅")
                    if "file_chat" in st.session_state: del st.session_state.file_chat # Re-init on key change
                except Exception as e:
                    st.error(f"Invalid API Key: {e}")
                    st.session_state.api_key = None
            else:
                st.warning("API key removed.", icon="ℹ️")

        if not st.session_state.api_key:
            st.warning("Enter Gemini API key to begin", icon="⚠️")

        # Chat mode selection for file chat
        st.markdown("---")
        file_chat_mode = st.selectbox(
            "🧠 Select Chat Mode for Files",
            FILE_CHAT_MODES,
            index=FILE_CHAT_MODES.index(st.session_state.get("file_chat_mode", "Document Analysis"))
        )
        st.session_state.file_chat_mode = file_chat_mode

        # Clear file chat
        if st.button("🧹 Clear File Chat"):
            st.session_state.file_messages = []
            if "file_chat" in st.session_state:
                del st.session_state.file_chat
            st.success("File chat history cleared!")
            st.rerun() # Rerun to clear display

        # Theme toggle for file mode
        st.markdown("---")
        st.header("🎨 Appearance")
        if st.button("Toggle Dark/Light Mode", key="theme_toggle_file_mode"):
            toggle_file_mode_theme()

    # Two columns: File Upload and Chat
    col1, col2 = st.columns([1, 1]) # Adjusted column ratio for better balance

    with col1:
        st.subheader("📁 Upload Documents")
        st.markdown(f"Supported formats: {', '.join(SUPPORTED_FILE_UPLOAD_TYPES)}")

        uploaded_files_widget = st.file_uploader( # Renamed variable to avoid conflict
            "Choose files to upload:",
            accept_multiple_files=True,
            type=SUPPORTED_FILE_UPLOAD_TYPES
        )

        if uploaded_files_widget:
            st.success(f"{len(uploaded_files_widget)} file(s) selected for upload queue.")

            if st.button("Confirm Upload Files"):
                processed_count = 0
                for uploaded_file_item in uploaded_files_widget:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    # Sanitize filename slightly for safety, though Streamlit usually handles this
                    safe_original_name = "".join(c if c.isalnum() or c in ['.', '_', '-'] else '_' for c in uploaded_file_item.name)
                    filename = f"{timestamp}_{safe_original_name}"
                    file_path = os.path.join(UPLOAD_DIR, filename)

                    try:
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file_item.getbuffer())

                        file_info = {
                            "name": uploaded_file_item.name, # Store original name for display
                            "path": file_path,
                            "type": uploaded_file_item.type,
                            "size": uploaded_file_item.size,
                            "timestamp": timestamp # Use the one from filename for consistency
                        }
                        # Avoid duplicates if re-uploading the same batch without clearing
                        if not any(f['path'] == file_path for f in st.session_state.uploaded_files):
                            st.session_state.uploaded_files.append(file_info)
                        processed_count +=1
                    except Exception as e:
                        st.error(f"Error saving {uploaded_file_item.name}: {e}")
                if processed_count > 0:
                    st.success(f"Successfully processed {processed_count} files!")
                    st.rerun() # Rerun to update file list display

        # Display uploaded files
        if st.session_state.uploaded_files:
            st.markdown("### Your Uploaded Documents")
            files_to_remove = [] # For safe removal while iterating

            for i, file_info in enumerate(st.session_state.uploaded_files):
                with st.container(): # Use container for better layout of buttons
                    c1, c2, c3 = st.columns([4,1,1])
                    with c1:
                        st.write(f"**{file_info['name']}**")
                        st.caption(f"Size: {file_info['size']/(1024*1024):.2f} MB | Uploaded: {file_info['timestamp']}")
                    
                    viewable_types = ["txt", "csv", "json", "md", "html"]
                    file_ext = file_info['name'].split('.')[-1].lower()
                    if file_ext in viewable_types:
                        with c2:
                            if st.button("View", key=f"view_{file_info['path']}"): # Use path for unique key
                                try:
                                    with open(file_info['path'], 'r', encoding='utf-8', errors='replace') as f_view:
                                        content = f_view.read()
                                    st.text_area(f"Content: {file_info['name']}", value=content, height=300, key=f"view_area_{file_info['path']}")
                                except Exception as e:
                                    st.error(f"Could not read file {file_info['name']}: {e}")
                    with c3:
                        if st.button("Delete", key=f"delete_{file_info['path']}"):
                            files_to_remove.append(file_info)
                st.markdown("---")

            if files_to_remove:
                for file_to_remove in files_to_remove:
                    if os.path.exists(file_to_remove['path']):
                        try:
                            os.remove(file_to_remove['path'])
                        except Exception as e:
                            st.error(f"Error deleting file from disk {file_to_remove['name']}: {e}")
                    st.session_state.uploaded_files.remove(file_to_remove)
                st.success("Selected files deleted.")
                st.rerun()

            if st.button("Clear All Uploaded Files"):
                for file_info_clear in st.session_state.uploaded_files:
                    if os.path.exists(file_info_clear['path']):
                        try:
                            os.remove(file_info_clear['path'])
                        except Exception as e:
                             st.error(f"Error deleting file from disk {file_info_clear['name']}: {e}")
                st.session_state.uploaded_files = []
                st.success("All uploaded files cleared!")
                st.rerun()

        # Add basic file analysis options
        if st.session_state.uploaded_files:
            st.markdown("### Quick Analysis Tools")
            if not st.session_state.uploaded_files: # Should not happen if we are in this block, but defensive
                 st.info("No files uploaded to analyze.")
            else:
                file_options_analysis = [f"{file['name']}" for file in st.session_state.uploaded_files]
                # Ensure selected_file_analysis is valid or default to first if list changes
                current_selected_analysis = st.session_state.get("selected_file_for_analysis")
                if current_selected_analysis not in file_options_analysis and file_options_analysis:
                    st.session_state.selected_file_for_analysis = file_options_analysis[0]
                elif not file_options_analysis: # No files left
                     st.session_state.selected_file_for_analysis = None

                selected_file_name_analysis = st.selectbox(
                    "Select a file to analyze:",
                    file_options_analysis,
                    index=file_options_analysis.index(st.session_state.selected_file_for_analysis) if st.session_state.selected_file_for_analysis and st.session_state.selected_file_for_analysis in file_options_analysis else 0,
                    key="quick_analysis_selector_widget"
                )
                st.session_state.selected_file_for_analysis = selected_file_name_analysis


                if selected_file_name_analysis:
                    selected_file_info_analysis = next((f for f in st.session_state.uploaded_files if f['name'] == selected_file_name_analysis), None)
                    if selected_file_info_analysis:
                        file_ext_analysis = selected_file_info_analysis['name'].split('.')[-1].lower()

                        if file_ext_analysis == 'csv':
                            st.markdown("#### CSV Analysis")
                            if st.button("Analyze CSV"):
                                try:
                                    df = pd.read_csv(selected_file_info_analysis['path'])
                                    st.write("##### Preview (Top 5 rows)")
                                    st.dataframe(df.head())
                                    st.write("##### Summary Statistics")
                                    st.dataframe(df.describe(include='all')) # include='all' for mixed types
                                except Exception as e:
                                    st.error(f"Error analyzing CSV {selected_file_info_analysis['name']}: {e}")

                        elif file_ext_analysis in ['xlsx', 'xls']:
                            st.markdown("#### Excel Analysis")
                            if st.button("Analyze Excel"):
                                try:
                                    xls = pd.ExcelFile(selected_file_info_analysis['path'])
                                    if not xls.sheet_names:
                                        st.warning("Excel file contains no sheets.")
                                    else:
                                        sheet_name = st.selectbox("Select sheet:", xls.sheet_names, key=f"excel_sheet_{selected_file_info_analysis['path']}")
                                        df = pd.read_excel(selected_file_info_analysis['path'], sheet_name=sheet_name)
                                        st.write(f"##### Preview (Top 5 rows from sheet: {sheet_name})")
                                        st.dataframe(df.head())
                                except Exception as e:
                                    st.error(f"Error analyzing Excel file {selected_file_info_analysis['name']}: {e}")

                        elif file_ext_analysis in ['txt', 'md']:
                            st.markdown("#### Text Analysis")
                            if st.button("Analyze Text"):
                                try:
                                    with open(selected_file_info_analysis['path'], 'r', encoding='utf-8', errors='replace') as f_text:
                                        content = f_text.read()
                                    st.write(f"Character count: {len(content):,}")
                                    st.write(f"Word count: {len(content.split()):,}")
                                    st.write(f"Line count: {len(content.splitlines()):,}")
                                except Exception as e:
                                    st.error(f"Error analyzing text file {selected_file_info_analysis['name']}: {e}")
                    else:
                        st.warning("Selected file for analysis not found in session. Please re-select.")

    with col2:
        st.subheader("💬 Chat with Your Documents")

        if st.session_state.uploaded_files:
            file_options_chat = [f"{file['name']}" for file in st.session_state.uploaded_files]
            # Persist selected file for chat
            current_selected_chat_file = st.session_state.get("selected_chat_file_name_for_file_mode")
            if current_selected_chat_file not in file_options_chat and file_options_chat:
                st.session_state.selected_chat_file_name_for_file_mode = file_options_chat[0]
            elif not file_options_chat:
                st.session_state.selected_chat_file_name_for_file_mode = None

            selected_chat_file_name = st.selectbox(
                "Select a file to discuss:",
                file_options_chat,
                index=file_options_chat.index(st.session_state.selected_chat_file_name_for_file_mode) if st.session_state.selected_chat_file_name_for_file_mode and st.session_state.selected_chat_file_name_for_file_mode in file_options_chat else 0,
                key="file_chat_selector_widget"
            )
            st.session_state.selected_chat_file_name_for_file_mode = selected_chat_file_name

            if selected_chat_file_name:
                selected_file_to_chat_info = next((f for f in st.session_state.uploaded_files if f['name'] == selected_chat_file_name), None)
                if selected_file_to_chat_info:
                    st.info(f"Ask questions about '{selected_file_to_chat_info['name']}'")

                    for msg in st.session_state.file_messages:
                        with st.chat_message(msg["role"]):
                            st.markdown(msg["content"])

                    file_prompt = st.chat_input(f"Ask about {selected_file_to_chat_info['name']}...")

                    if file_prompt and st.session_state.api_key:
                        st.chat_message("user").markdown(file_prompt)
                        st.session_state.file_messages.append({"role": "user", "content": file_prompt})

                        system_prompt_file = get_file_chat_system_prompt(file_prompt, file_chat_mode, selected_file_to_chat_info['name'])

                        with st.spinner(f"Analyzing '{selected_file_to_chat_info['name']}'..."):
                            try:
                                if "file_chat" not in st.session_state or not st.session_state.file_chat.history :
                                     st.session_state.file_chat = initialize_model(
                                        FILE_ANALYSIS_MODEL_NAME,
                                        DEFAULT_GENERATION_CONFIG,
                                        history=st.session_state.file_messages
                                    )
                                # Ensure model config is up-to-date if it can be changed for file mode
                                # For now, using DEFAULT_GENERATION_CONFIG

                                response = st.session_state.file_chat.send_message(system_prompt_file)
                                reply = response.text

                            except genai.types.generation_types.BlockedPromptException as e:
                                st.error(f"Your prompt regarding the file was blocked. Reason: {e}")
                                reply = "My apologies, I cannot process that request for the file as it was blocked."
                            except Exception as e:
                                st.error(f"Error processing request for {selected_file_to_chat_info['name']}: {str(e)}")
                                reply = f"Sorry, an error occurred while processing your request for {selected_file_to_chat_info['name']}: {str(e)}"

                            if reply:
                                st.chat_message("assistant").markdown(reply)
                                st.session_state.file_messages.append({"role": "assistant", "content": reply})

                    if st.session_state.file_messages:
                        if st.button("Export File Chat History"):
                            export_filename = export_to_json(
                                st.session_state.file_messages,
                                filename_prefix="file_chat",
                                chat_mode=file_chat_mode,
                                original_filename=selected_file_to_chat_info['name']
                            )
                            try:
                                with open(export_filename, "rb") as f_export:
                                    st.download_button(
                                        label="📄 Download File Chat JSON",
                                        data=f_export,
                                        file_name=export_filename,
                                        mime="application/json"
                                    )
                            except FileNotFoundError:
                                st.error(f"Could not find exported file: {export_filename}")
                else:
                    st.warning("Selected file for chat not found. Please re-select or upload.")
        else:
            st.info("Upload files to start chatting about them.")
            st.markdown("""
            ##### Example Questions You Can Ask About Documents:
            - "Summarize the key points in this document."
            - "What are the main topics covered in chapter 3?"
            - "Extract all email addresses mentioned in the text."
            - "What is the conclusion of this research paper?"
            """)

st.markdown("---")
st.markdown(get_footer_style(), unsafe_allow_html=True)
        else:
            st.warning("Enter Gemini API key to begin", icon="⚠️")
        
        # Chat mode selection for file chat
        st.markdown("---")
        file_chat_mode = st.selectbox(
            "🧠 Select Chat Mode for Files",
            [
                "Document Analysis",
                "Normal",
                "Explain Like I'm 5",
                "Summarizer",
                "Q&A Expert"
            ]
        )
        
        # Clear file chat
        if st.button("🧹 Clear File Chat"):
            st.session_state.file_messages = []
            if "file_chat" in st.session_state:
                del st.session_state.file_chat
                
                # Reinitialize chat
                if "api_key" in st.session_state and st.session_state.api_key:
                    st.session_state.file_chat = genai.GenerativeModel(
                        model_name="gemini-2.0-flash",
                        generation_config={
                            "max_output_tokens": 8192,
                            "temperature": 0.7,
                            "top_p": 0.95,
                            "top_k": 40
                        }
                    ).start_chat(history=[])
            st.success("File chat history cleared!")
            st.rerun()
    
    # Two columns: File Upload and Chat
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # File uploader
        st.subheader("📁 Upload Documents")
        st.markdown("Supported formats: PDF, DOCX, TXT, CSV, JSON, MD, PPTX, XLSX, HTML")
        
        uploaded_files = st.file_uploader(
            "Choose files to upload:",
            accept_multiple_files=True,
            type=["pdf", "docx", "txt", "csv", "json", "md", "pptx", "xlsx", "html"]
        )
        
        if uploaded_files:
            st.success(f"{len(uploaded_files)} file(s) selected")
            
            # Process button
            if st.button("Upload Files"):
                for uploaded_file in uploaded_files:
                    # Create a unique filename with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{timestamp}_{uploaded_file.name}"
                    file_path = os.path.join(upload_dir, filename)
                    
                    # Save the file
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Add to session state
                    file_info = {
                        "name": uploaded_file.name,
                        "path": file_path,
                        "type": uploaded_file.type,
                        "size": uploaded_file.size,
                        "timestamp": timestamp
                    }
                    st.session_state.uploaded_files.append(file_info)
                
                st.success(f"Successfully uploaded {len(uploaded_files)} files!")
        
        # Display uploaded files
        if st.session_state.uploaded_files:
            st.markdown("### Your Uploaded Documents")
            
            for i, file_info in enumerate(st.session_state.uploaded_files):
                col_a, col_b, col_c = st.columns([3, 1, 1])
                
                with col_a:
                    st.write(f"**{file_info['name']}**")
                    st.caption(f"Size: {file_info['size']/1024:.1f} KB | Uploaded: {file_info['timestamp']}")
                
                with col_b:
                    # Determine if file is readable in-app
                    viewable_types = ["txt", "csv", "json", "md", "html"]
                    file_ext = file_info['name'].split('.')[-1].lower()
                    
                    if file_ext in viewable_types:
                        if st.button("View", key=f"view_{i}"):
                            with open(file_info['path'], 'r') as f:
                                content = f.read()
                                st.text_area("File Content", value=content, height=300)
                
                with col_c:
                    if st.button("Delete", key=f"delete_{i}"):
                        # Remove file from disk
                        if os.path.exists(file_info['path']):
                            os.remove(file_info['path'])
                        
                        # Remove from session state
                        st.session_state.uploaded_files.pop(i)
                        st.success(f"Deleted {file_info['name']}")
                        st.rerun()
                
                st.markdown("---")
            
            # Clear all button
            if st.button("Clear All Files"):
                # Remove all files from disk
                for file_info in st.session_state.uploaded_files:
                    if os.path.exists(file_info['path']):
                        os.remove(file_info['path'])
                
                # Clear session state
                st.session_state.uploaded_files = []
                st.success("All files cleared!")
                st.rerun()
                
        # Add basic file analysis options
        if st.session_state.uploaded_files:
            st.markdown("### Quick Analysis Tools")
            
            file_options = [f"{file['name']}" for file in st.session_state.uploaded_files]
            selected_file = st.selectbox("Select a file to analyze:", file_options, key="quick_analysis_selector")
            
            if selected_file:
                selected_index = file_options.index(selected_file)
                file_info = st.session_state.uploaded_files[selected_index]
                file_ext = file_info['name'].split('.')[-1].lower()
                
                # Show different analysis options based on file type
                if file_ext == 'csv':
                    st.markdown("#### CSV Analysis")
                    if st.button("Analyze CSV"):
                        try:
                            df = pd.read_csv(file_info['path'])
                            st.write("#### Preview")
                            st.dataframe(df.head())
                            st.write("#### Summary Statistics")
                            st.write(df.describe())
                        except Exception as e:
                            st.error(f"Error analyzing CSV: {e}")
                
                elif file_ext in ['xlsx', 'xls']:
                    st.markdown("#### Excel Analysis")
                    if st.button("Analyze Excel"):
                        try:
                            xls = pd.ExcelFile(file_info['path'])
                            sheet_name = st.selectbox("Select sheet:", xls.sheet_names)
                            df = pd.read_excel(file_info['path'], sheet_name=sheet_name)
                            st.write("#### Preview")
                            st.dataframe(df.head())
                        except Exception as e:
                            st.error(f"Error analyzing Excel file: {e}")
                
                elif file_ext == 'txt' or file_ext == 'md':
                    st.markdown("#### Text Analysis")
                    if st.button("Analyze Text"):
                        try:
                            with open(file_info['path'], 'r') as f:
                                content = f.read()
                                
                            st.write(f"Character count: {len(content)}")
                            st.write(f"Word count: {len(content.split())}")
                            st.write(f"Line count: {len(content.splitlines())}")
                        except Exception as e:
                            st.error(f"Error analyzing text: {e}")
    
    with col2:
        st.subheader("💬 Chat with Your Documents")
        
        # File selection for chat
        if st.session_state.uploaded_files:
            file_options = [f"{file['name']}" for file in st.session_state.uploaded_files]
            selected_chat_file = st.selectbox("Select a file to discuss:", file_options, key="file_chat_selector")
            
            if selected_chat_file:
                selected_index = file_options.index(selected_chat_file)
                file_info = st.session_state.uploaded_files[selected_index]
                
                st.info(f"Ask questions about '{selected_chat_file}'")
                
                # Display file chat history
                for msg in st.session_state.file_messages:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])
                
                # Chat input for file chat
                file_prompt = st.chat_input("Ask about your document...")
                
                if file_prompt and "api_key" in st.session_state and st.session_state.api_key:
                    # Display user message
                    st.chat_message("user").markdown(file_prompt)
                    st.session_state.file_messages.append({"role": "user", "content": file_prompt})
                    
                    # Prepare file-specific prompt based on chat mode
                    if file_chat_mode == "Document Analysis":
                        system_prompt = f"""
                        Analyze the following document named '{selected_chat_file}' 
                        with this question or request: {file_prompt}
                        
                        Provide a comprehensive analysis with key insights.
                        """
                    elif file_chat_mode == "Explain Like I'm 5":
                        system_prompt = f"""
                        Explain the content from the document '{selected_chat_file}' 
                        in simple terms that a 5-year old could understand.
                        
                        Question: {file_prompt}
                        """
                    elif file_chat_mode == "Summarizer":
                        system_prompt = f"""
                        Summarize the key points from '{selected_chat_file}' 
                        focusing on: {file_prompt}
                        """
                    elif file_chat_mode == "Q&A Expert":
                        system_prompt = f"""
                        Based on the document '{selected_chat_file}', 
                        answer this question in detail: {file_prompt}
                        """
                    else:  # Normal mode
                        system_prompt = f"""
                        Regarding the document '{selected_chat_file}': {file_prompt}
                        """
                    
                    # Get response
                    with st.spinner("Analyzing document..."):
                        if "file_chat" in st.session_state:
                            try:
                                response = st.session_state.file_chat.send_message(system_prompt)
                                reply = response.text
                                
                                # Display response
                                st.chat_message("assistant").markdown(reply)
                                st.session_state.file_messages.append({"role": "assistant", "content": reply})
                            except Exception as e:
                                st.error(f"Error processing request: {str(e)}")
                
                # Add export options for file chat
                if st.session_state.file_messages:
                    if st.button("Export File Chat"):
                        export_filename = f"file_chat_{selected_chat_file}_{datetime.now().strftime('%Y%m%d')}.json"
                        export_data = {
                            "filename": selected_chat_file,
                            "messages": st.session_state.file_messages,
                            "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "chat_mode": file_chat_mode
                        }
                        
                        with open(export_filename, "w") as f:
                            json.dump(export_data, f, indent=4)
                        
                        with open(export_filename, "rb") as f:
                            st.download_button(
                                label="📄 Download Chat History",
                                data=f,
                                file_name=export_filename,
                                mime="application/json"
                            )
        else:
            st.info("Upload files to start chatting about them")
            
            # Add a sample of what users can ask
            st.markdown("""
            ### Example Questions You Can Ask About Documents
            - "Summarize the key points in this document"
            - "What are the main topics covered?"
            - "Extract all dates mentioned in the text"
            - "Find all numerical data and statistics"
            - "Compare this with another document"
            - "What conclusions does this document make?"
            """)

# Add a footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888;">
    <p>Powered by Google Gemini API | App Version 1.0</p>
</div>
""", unsafe_allow_html=True)
