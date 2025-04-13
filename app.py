import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
import os
import json
import time
from datetime import datetime
import tempfile
import pandas as pd

# Page settings
st.set_page_config(page_title="Gemini", layout="wide", page_icon="💎")

# Mode selection
app_mode = st.radio("Choose Mode:", ["Chat", "File Upload"])

if app_mode == "Chat":
    # Gradient-styled title using HTML
    gradient_title = """
    <style>
    @keyframes gradient {
      0% {background-position: 0%;}
      100% {background-position: 100%;}
    }
    .animated-gradient {
      font-size: 64px;
      font-weight: bold;
      text-align: center;
      background: linear-gradient(90deg, #4f46e5, #ec4899, #4f46e5);
      background-size: 200%;
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      animation: gradient 3s infinite linear;
      font-family: "Segoe UI", sans-serif;
    }
    </style>

    <h1 class='animated-gradient'> Gemini</h1>
    """
    st.markdown(gradient_title, unsafe_allow_html=True)


    # Blurry Gradient Background Style
    # Add this after st.set_page_config(...)


    name = st.text_input("Please enter your name", value=" ")

    if name.strip():
        st.markdown(f"""
            <style>
            @keyframes gradientShift {{
                0% {{ background-position: 0%; }}
                100% {{ background-position: 100%; }}
            }}
            .animated-greeting {{
                font-size: 36px;
                font-weight: bold;
                text-align: center;
                background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899);
                background-size: 300%;
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                animation: gradientShift 4s linear infinite;
                font-family: "Segoe UI", sans-serif;
                margin-top: 10px;
            }}
            </style>

            <h3 class='animated-greeting'>Hello, {name}, ready to explore ideas? ⚡</h3>
        """, unsafe_allow_html=True)


    # Initialize session data for settings and themes
    if "settings" not in st.session_state:
        st.session_state.settings = {
            "temperature": 0.7,
            "top_k": 40,
            "top_p": 0.95,
            "max_tokens": 8192
        }

    if "theme" not in st.session_state:
        st.session_state.theme = "light"

    if "favorites" not in st.session_state:
        st.session_state.favorites = []

    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = {}

    # Name input


    # Theme toggle function
    def toggle_theme():
        st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
        # Apply theme changes
        if st.session_state.theme == "dark":
            st.markdown("""
            <style>
            .main {background-color: #0e1117; color: #ffffff;}
            .sidebar .sidebar-content {background-color: #262730; color: #ffffff;}
            </style>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <style>
            .main {background-color: #ffffff; color: #31333F;}
            .sidebar .sidebar-content {background-color: #f0f2f6; color: #31333F;}
            </style>
            """, unsafe_allow_html=True)

    # Sidebar - API, Chat Mode, Clear, Settings
    with st.sidebar:
        st.header("🔐 Gemini API Settings")
        api_key = st.text_input("Enter your Gemini API key:", type="password")

        st.markdown("---")
        chat_mode = st.selectbox(
            "🧠 Select Chat Mode",
                [
            "Normal",
            "Deep Research",
            "Creative",
            "Explain Like I'm 5",
            "Code Helper",
            "Debate Mode",
            "Translation Helper",
            "Summarizer",
            "Emotional Support",           # Friendly, comforting responses
            "Idea Generator",              # Brainstorming new ideas
            "Tech News Brief",             # Explains current tech news
            "Quiz Me!",                    # Asks questions based on a topic
            "Interview Coach",            # Gives mock interview questions & feedback
            "Grammar & Style Fixer",      # Proofreads and improves writing
            "Homework Buddy",             # Helps with assignments step by step
            "Productivity Coach",         # Time management, focus tips
            "Philosopher Mode",           # Deep, reflective answers
            "Roast Me (Light Humor)",     # Playfully sarcastic or teasing replies
            "Storyteller",                # Makes up short stories or fables
            "Fitness & Diet Guide",       # Health advice & planning
            "Career Advisor",             # Helps with resumes, career paths
        ]
        )

        st.markdown("---")
        # New feature: Save/Load conversation
        st.header("💾 Conversation Management")
        save_name = st.text_input("Conversation name:")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 Save Chat"):
                if save_name and len(st.session_state.messages) > 0:
                    st.session_state.conversation_history[save_name] = {
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
        
        if api_key:
            genai.configure(api_key=api_key)
            st.success("API key set successfully!", icon="✅")
        else:
            st.warning("Enter Gemini API key to begin", icon="⚠️")

    # Initialize session
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "chat" not in st.session_state and api_key:
        st.session_state.chat = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config={
                "max_output_tokens": st.session_state.settings["max_tokens"],
                "temperature": st.session_state.settings["temperature"],
                "top_p": st.session_state.settings["top_p"],
                "top_k": st.session_state.settings["top_k"]
            }
        ).start_chat(history=[])

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

    # PDF Export Function
    def export_to_pdf(text, filename="gemini_response.pdf"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", size=12)

        for line in text.split("\n"):
            pdf.multi_cell(0, 10, line)

        pdf.output(filename)
        return filename

    # Export to JSON Function
    def export_to_json(chat_history, filename="gemini_chat_export.json"):
        export_data = {
            "messages": chat_history,
            "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "chat_mode": chat_mode
        }
        
        with open(filename, "w") as f:
            json.dump(export_data, f, indent=4)
        
        return filename

    # Chat input
    if api_key:
        # Add a typing effect toggle
        typing_effect = st.checkbox("Enable typing effect for responses", value=False)
        
        # Add language selection for Translation Mode
        if chat_mode == "Translation Helper":
            target_language = st.selectbox(
                "Translate to:", 
                ["Spanish", "French", "German", "Italian", "Portuguese", "Russian", "Japanese", "Chinese", "Arabic", "Hindi"]
            )
        
        # Add a file selection option to use with chat if files are uploaded
        if "uploaded_files" in st.session_state and st.session_state.uploaded_files:
            st.markdown("### Use Uploaded Files")
            file_options = ["None"] + [f"{file['name']}" for file in st.session_state.uploaded_files]
            selected_chat_file = st.selectbox("Select a file to discuss:", file_options)
            
            if selected_chat_file != "None":
                st.info(f"You can ask questions about '{selected_chat_file}' in your chat.")
        
        user_prompt = st.chat_input("Ask anything 💬")

        if user_prompt:
            st.chat_message("user").markdown(user_prompt)
            st.session_state.messages.append({"role": "user", "content": user_prompt})

            # Prepare system prompt for different modes
            if chat_mode == "Deep Research":
                system_prompt = f"""
    You are a high-level research assistant writing in-depth academic responses. 
    Structure the output as a formal article (~8000 tokens) with:
    1. Executive Summary
    2. Introduction
    3. History & Evolution
    4. Concepts & Frameworks
    5. Current State
    6. Challenges
    7. Applications
    8. Comparisons
    9. Future Outlook
    10. Conclusion
    11. References (Optional)

    Query:
    \"\"\"{user_prompt}\"\"\"
    """
            elif chat_mode == "Creative":
                system_prompt = f"You are a wildly creative storyteller and ideator. Think like a novelist or futurist. Respond creatively to: {user_prompt}"
            elif chat_mode == "Explain Like I'm 5":
                system_prompt = f"Explain this like I'm 5 years old: {user_prompt}"
            elif chat_mode == "Code Helper":
                system_prompt = f"You are a coding assistant. Explain, debug, or generate code for this prompt: {user_prompt}"
            elif chat_mode == "Debate Mode":
                system_prompt = f"""
    You are a balanced debate assistant. For the topic provided:
    1. Present a strong case for the position (Pro)
    2. Present a strong case against the position (Con)
    3. Analyze the strongest points from both sides
    4. Provide a balanced conclusion

    Topic: {user_prompt}
    """
            elif chat_mode == "Translation Helper":
                system_prompt = f"Translate the following text to {target_language}. Provide both the translation and any cultural notes or context that might be helpful: {user_prompt}"
            elif chat_mode == "Summarizer":
                system_prompt = f"""
    Summarize the following text in three different ways:
    1. Executive summary (2-3 sentences)
    2. Bullet point summary (5-7 key points)
    3. Detailed summary (3-4 paragraphs)

    Text to summarize:
    \"\"\"{user_prompt}\"\"\"
    """
            elif chat_mode == "Emotional Support":
                system_prompt = f"You are a kind and empathetic listener. Offer supportive and comforting responses to: {user_prompt}"
            elif chat_mode == "Idea Generator":
                system_prompt = f"You are a brainstorming engine. Generate fresh, unique, and useful ideas related to: {user_prompt}"
            elif chat_mode == "Tech News Brief":
                system_prompt = f"You are a tech journalist. Summarize and explain the latest technology news about: {user_prompt}"
            elif chat_mode == "Quiz Me!":
                system_prompt = f"You are a quizmaster. Ask the user 3-5 interactive quiz questions based on: {user_prompt}"
            elif chat_mode == "Interview Coach":
                system_prompt = f"You are an expert interview coach. Ask mock questions or provide feedback related to: {user_prompt}"
            elif chat_mode == "Grammar & Style Fixer":
                system_prompt = f"You are an English editor. Improve grammar, sentence structure, and writing style of the following text: {user_prompt}"
            elif chat_mode == "Homework Buddy":
                system_prompt = f"You are a helpful tutor. Break down and explain each step to solve: {user_prompt}"
            elif chat_mode == "Productivity Coach":
                system_prompt = f"You are a productivity guru. Give practical advice, time management tips, and focus strategies for: {user_prompt}"
            elif chat_mode == "Philosopher Mode":
                system_prompt = f"You are a wise philosopher. Reflect deeply and insightfully about: {user_prompt}"
            elif chat_mode == "Roast Me (Light Humor)":
                system_prompt = f"You are a stand-up comedian. Lightly roast the user in a humorous way based on: {user_prompt}"
            elif chat_mode == "Storyteller":
                system_prompt = f"You are a master storyteller. Create an original and imaginative short story inspired by: {user_prompt}"
            elif chat_mode == "Fitness & Diet Guide":
                system_prompt = f"You are a certified fitness coach and nutritionist. Provide customized fitness and diet advice for: {user_prompt}"
            elif chat_mode == "Career Advisor":
                system_prompt = f"You are a career development expert. Give tailored advice regarding jobs, resume, or growth about: {user_prompt}"
            else:
                system_prompt = user_prompt


            # Show a spinner while loading
            with st.spinner("Gemini is thinking..."):
                # Update model parameters before sending
                if "chat" in st.session_state:
                    # Get response from Gemini
                    response = st.session_state.chat.send_message(system_prompt)
                    reply = response.text

                    # Typing effect simulation
                    if typing_effect:
                        with st.chat_message("assistant"):
                            message_placeholder = st.empty()
                            full_response = ""
                            # Simulate typing with chunks of text
                            for chunk in reply.split():
                                full_response += chunk + " "
                                message_placeholder.markdown(full_response + "▌")
                                time.sleep(0.05)  # Adjust typing speed
                            message_placeholder.markdown(reply)
                    else:
                        st.chat_message("assistant").markdown(reply)

                    st.session_state.messages.append({"role": "assistant", "content": reply})

                    # Save last reply to export
                    st.session_state.last_reply = reply

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
            filename = export_to_json(st.session_state.messages)
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
    # Create a fancy title for file upload screen
    st.markdown("""
    <style>
    @keyframes gradient {
      0% {background-position: 0%;}
      100% {background-position: 100%;}
    }
    .upload-gradient {
      font-size: 40px;
      font-weight: bold;
      text-align: center;
      background: linear-gradient(90deg, #3b82f6, #10b981, #3b82f6);
      background-size: 200%;
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      animation: gradient 3s infinite linear;
      font-family: "Segoe UI", sans-serif;
      margin-bottom: 20px;
    }
    </style>

    <h2 class='upload-gradient'>Document Upload & Analysis</h2>
    """, unsafe_allow_html=True)
    
    # Initialize session state for uploaded files
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = []
    
    # Initialize session data for file chat
    if "file_messages" not in st.session_state:
        st.session_state.file_messages = []
    
    # Initialize chat for file mode if not exists
    if "file_chat" not in st.session_state and "api_key" in st.session_state and st.session_state.api_key:
        st.session_state.file_chat = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config={
                "max_output_tokens": 8192,
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40
            }
        ).start_chat(history=[])
        
    # Create upload directory if it doesn't exist
    upload_dir = "uploaded_files"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    # API Key field in sidebar for file mode
    with st.sidebar:
        st.header("🔐 Gemini API Settings")
        api_key = st.text_input("Enter your Gemini API key:", type="password", key="file_api_key")
        
        if api_key:
            genai.configure(api_key=api_key)
            st.session_state.api_key = api_key
            st.success("API key set successfully!", icon="✅")
            
            # Initialize chat for file mode if not exists
            if "file_chat" not in st.session_state:
                st.session_state.file_chat = genai.GenerativeModel(
                    model_name="gemini-2.0-flash",
                    generation_config={
                        "max_output_tokens": 8192,
                        "temperature": 0.7,
                        "top_p": 0.95,
                        "top_k": 40
                    }
                ).start_chat(history=[])
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
