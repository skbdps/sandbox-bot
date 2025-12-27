"""
Claude Chatbot POC - Main Streamlit Application
"""

import os
import yaml
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

from src.database import Database
from src.claude_client import ClaudeClient
from src.file_handler import FileHandler
from src.code_executor import CodeExecutor
from src.utils import (
    estimate_tokens, estimate_file_tokens, calculate_cost,
    format_token_count, format_cost, get_file_type, truncate_text,
    get_context_messages, estimate_message_tokens
)

# Load environment variables
load_dotenv()

# Load configuration
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)


def code_block_with_copy(code: str, language: str = 'python', label: str = None):
    """Display a code block with a copy button"""
    import hashlib
    # Create unique key from code hash
    key = hashlib.md5(code.encode()).hexdigest()[:8]
    
    # Create columns for code and copy button
    col1, col2 = st.columns([12, 1])
    
    with col1:
        if label:
            st.caption(label)
        st.code(code, language=language)
    
    with col2:
        # Use Streamlit's button with custom styling
        if st.button("📋", key=f"copy_{key}", help="Copy to clipboard"):
            # Use JavaScript to copy to clipboard
            st.components.v1.html(
                f"""
                <script>
                    const code = `{code.replace('`', '\\`')}`;
                    navigator.clipboard.writeText(code).then(function() {{
                        console.log('Copied to clipboard');
                    }}, function(err) {{
                        console.error('Could not copy text: ', err);
                    }});
                </script>
                """,
                height=0,
            )
            st.toast("📋 Copied to clipboard!", icon="✅")


def init_session_state():
    """Initialize Streamlit session state"""
    if 'db' not in st.session_state:
        st.session_state.db = Database(config['database']['path'])
    
    if 'file_handler' not in st.session_state:
        st.session_state.file_handler = FileHandler(config['storage']['uploads_dir'])
    
    if 'code_executor' not in st.session_state and config['code_execution']['enabled']:
        try:
            st.session_state.code_executor = CodeExecutor(
                timeout_seconds=config['code_execution']['timeout_seconds'],
                db=st.session_state.db  # Pass database instance
            )
        except ValueError as e:
            # E2B not configured - disable code execution
            st.warning(f"⚠️ Code execution disabled: {str(e)}")
            st.session_state.code_executor = None
    
    if 'claude_client' not in st.session_state:
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            st.error("❌ ANTHROPIC_API_KEY not found in environment variables!")
            st.stop()
        
        st.session_state.claude_client = ClaudeClient(
            api_key=api_key,
            model=config['claude']['model'],
            max_tokens=config['claude']['max_tokens'],
            extended_thinking=config['claude']['extended_thinking'],
            db=st.session_state.db  # Pass database instance
        )
    
    if 'current_chat_id' not in st.session_state:
        st.session_state.current_chat_id = None
    
    if 'uploaded_files_temp' not in st.session_state:
        st.session_state.uploaded_files_temp = []


def create_new_chat():
    """Create a new chat"""
    chat = st.session_state.db.create_chat(title="New Chat")
    st.session_state.current_chat_id = chat.id
    st.session_state.uploaded_files_temp = []
    st.rerun()


def switch_chat(chat_id: str):
    """Switch to a different chat"""
    st.session_state.current_chat_id = chat_id
    st.session_state.uploaded_files_temp = []
    st.rerun()


def delete_current_chat():
    """Delete the current chat"""
    if st.session_state.current_chat_id:
        chat_id = st.session_state.current_chat_id
        
        # Close sandbox if exists
        if st.session_state.code_executor:
            st.session_state.code_executor.close_sandbox(chat_id)
        
        # Delete files from disk
        st.session_state.file_handler.delete_chat_files(chat_id)
        
        # Delete from database
        st.session_state.db.delete_chat(chat_id)
        
        # Switch to another chat or create new
        chats = st.session_state.db.get_all_chats()
        if chats:
            st.session_state.current_chat_id = chats[0].id
        else:
            create_new_chat()
        
        st.rerun()


def render_sidebar():
    """Render the sidebar with chat list"""
    with st.sidebar:
        st.title("💬 Chats")
        
        # New chat button
        if st.button("➕ New Chat", use_container_width=True):
            create_new_chat()
        
        # Debug mode toggle
        debug_mode = st.checkbox("🐛 Debug Mode", value=False)
        
        st.divider()
        
        # Chat list
        chats = st.session_state.db.get_all_chats()
        
        if not chats:
            st.info("No chats yet. Create one!")
            return
        
        for chat in chats:
            is_active = chat.id == st.session_state.current_chat_id
            
            # Chat button
            button_label = f"{'🟢' if is_active else '⚪'} {truncate_text(chat.title, 25)}"
            
            if st.button(button_label, key=f"chat_{chat.id}", use_container_width=True):
                if not is_active:
                    switch_chat(chat.id)
            
            # Show metadata for active chat
            if is_active:
                st.caption(f"💬 {chat.message_count} msgs | 🕒 {chat.last_updated.strftime('%m/%d %H:%M')}")
                
                # Show saved project files from database
                with st.expander("📁 Project Files", expanded=False):
                    try:
                        # Query database for saved files
                        saved_files = st.session_state.db.get_sandbox_files(chat.id)
                        
                        if saved_files:
                            # Group files by directory for hierarchical display
                            file_tree = {}
                            for file in saved_files:
                                dir_name = file.directory or ''
                                if dir_name not in file_tree:
                                    file_tree[dir_name] = []
                                file_tree[dir_name].append(file)
                            
                            # Display hierarchically
                            for directory in sorted(file_tree.keys()):
                                dir_files = file_tree[directory]
                                
                                # Show directory header if not root
                                if directory:
                                    st.markdown(f"**📂 {directory}**")
                                
                                # Show files in this directory
                                for file in sorted(dir_files, key=lambda f: f.filename):
                                    col1, col2, col3 = st.columns([3, 1, 1])
                                    
                                    with col1:
                                        indent = "    " if directory else "  "
                                        st.text(f"{indent}📄 {file.filename}")
                                    
                                    with col2:
                                        # Preview button (shows in modal)
                                        if st.button("👁️", key=f"view_{file.id}", help="Preview file"):
                                            st.session_state.preview_file = file
                                    
                                    with col3:
                                        # Download button
                                        st.download_button(
                                            "⬇️",
                                            data=file.content,
                                            file_name=file.filename,
                                            mime="text/plain",
                                            key=f"dl_{file.id}",
                                            help=f"Download {file.filename}"
                                        )
                            
                            # Show file preview modal if file selected
                            if hasattr(st.session_state, 'preview_file') and st.session_state.preview_file:
                                preview_file = st.session_state.preview_file
                                with st.container():
                                    st.markdown("---")
                                    st.markdown(f"### 📄 {preview_file.filename}")
                                    if preview_file.description:
                                        st.caption(preview_file.description)
                                    st.caption(f"Type: {preview_file.file_type} | Size: {preview_file.size_bytes} bytes")
                                    code_block_with_copy(preview_file.content, language=preview_file.file_type)
                                    if st.button("Close Preview", key="close_preview"):
                                        st.session_state.preview_file = None
                                        st.rerun()
                            
                            # Summary
                            total_size = sum(f.size_bytes or 0 for f in saved_files)
                            st.caption(f"**{len(saved_files)} file(s)** | Total: {total_size:,} bytes")
                        
                        else:
                            st.caption("No saved files yet")
                            st.caption("💡 Use `save_file` tool to persist files")
                    
                    except Exception as e:
                        st.caption(f"⚠️ Error loading files")
                        st.caption(f"Details: {str(e)}")
                        print(f"[APP] Error loading sidebar files: {str(e)}")
                
                # Debug panel
                if debug_mode:
                    with st.expander("🐛 Debug Info", expanded=True):
                        if chat.sandbox_id:
                            st.text(f"Sandbox: {chat.sandbox_id[:12]}...")
                        else:
                            st.text("Sandbox: None")
                        
                        # Show recent tool calls
                        tool_calls = st.session_state.db.get_tool_calls(chat.id)
                        if tool_calls:
                            st.write(f"**Tool Calls:** {len(tool_calls)}")
                            for tc in tool_calls[-5:]:  # Last 5
                                status_icon = "✅" if tc.status == 'success' else "❌"
                                st.text(f"{status_icon} {tc.tool_name} ({tc.execution_time_ms:.0f}ms)")
                        
                        # Show thinking events
                        thinking = st.session_state.db.get_thinking_events(chat.id)
                        if thinking:
                            st.write(f"**Thinking Events:** {len(thinking)}")


def render_file_upload():
    """Render file upload section"""
    st.subheader("📎 Upload Files")
    
    uploaded_files = st.file_uploader(
        "Choose files",
        accept_multiple_files=True,
        type=config['files']['allowed_extensions'],
        key="file_uploader"
    )
    
    if uploaded_files:
        for file in uploaded_files:
            # Check if already uploaded
            if file.name not in [f['name'] for f in st.session_state.uploaded_files_temp]:
                file_type = get_file_type(file.name)
                
                # Save file
                file_path = st.session_state.file_handler.save_file(
                    file.read(),
                    file.name,
                    st.session_state.current_chat_id
                )
                
                # Estimate tokens
                token_estimate = estimate_file_tokens(
                    file_path,
                    file_type,
                    config['context']['token_estimation_ratio']
                )
                
                # Add to database
                db_file = st.session_state.db.add_file(
                    chat_id=st.session_state.current_chat_id,
                    filename=file.name,
                    file_path=file_path,
                    file_type=file_type,
                    size_bytes=file.size,
                    token_estimate=token_estimate
                )
                
                # Add to temp list
                st.session_state.uploaded_files_temp.append({
                    'id': db_file.id,
                    'name': file.name,
                    'size': file.size,
                    'type': file_type,
                    'tokens': token_estimate
                })
    
    # Display uploaded files
    files = st.session_state.db.get_files(st.session_state.current_chat_id)
    
    if files:
        st.write("**Files in this chat:**")
        for file in files:
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                status = "✅" if file.in_context else "⚪"
                st.write(f"{status} {truncate_text(file.filename, 30)}")
            
            with col2:
                st.caption(f"{format_token_count(file.token_estimate)} tokens")
            
            with col3:
                if st.button("🗑️", key=f"delete_file_{file.id}"):
                    st.session_state.file_handler.delete_file(file.file_path)
                    st.session_state.db.delete_file(file.id)
                    st.rerun()


def render_messages():
    """Render chat messages"""
    messages = st.session_state.db.get_messages(st.session_state.current_chat_id)
    
    for msg in messages:
        # Skip tool_result messages (they're shown in execution display)
        if msg.role == "user" and isinstance(msg.content, list):
            if any(block.get('type') == 'tool_result' for block in msg.content):
                continue
        
        with st.chat_message(msg.role):
            # Show timestamp
            st.caption(f"🕐 {msg.timestamp.strftime('%I:%M %p')}")
            
            content = msg.content
            
            if msg.role == "user":
                # For user messages, extract files and show indicators
                if isinstance(content, list):
                    # Separate file blocks and text blocks
                    text_blocks = []
                    file_count = 0
                    
                    for block in content:
                        block_type = block.get('type')
                        
                        if block_type == 'document':
                            file_count += 1
                            st.caption("📄 PDF Document")
                        elif block_type == 'image':
                            file_count += 1
                            st.caption("🖼️ Image")
                        elif block_type == 'text':
                            # Check if this is file content or user input
                            # File content is usually longer, user input is last
                            text_blocks.append(block.get('text', ''))
                    
                    # Show only the last text block (user's actual question)
                    # The earlier text blocks are file contents
                    if text_blocks:
                        st.markdown(text_blocks[-1])
                
                elif isinstance(content, str):
                    st.markdown(content)
            
            elif msg.role == "assistant":
                # For assistant messages, show thinking, tool use, and text
                if isinstance(content, list):
                    has_tool_use = any(block.get('type') == 'tool_use' for block in content)
                    
                    for block in content:
                        if block.get('type') == 'thinking':
                            # Show thinking in expander
                            if config['code_execution']['ui']['show_thinking']:
                                with st.expander("🤔 View Thinking Process"):
                                    st.markdown(block.get('thinking', ''))
                        
                        elif block.get('type') == 'tool_use':
                            # Show code execution
                            if config['code_execution']['ui']['show_code_attempts']:
                                with st.expander("⚙️ Code Execution", expanded=True):
                                    code = block['input'].get('code', '')
                                    if code:
                                        code_block_with_copy(code, language='python')
                        
                        elif block.get('type') == 'tool_result_display':
                            # Show execution result (persisted data)
                            tool_name = block.get('tool_name')
                            tool_input = block.get('tool_input', {})
                            result = block.get('result', {})
                            iteration = block.get('iteration', 0)
                            
                            if tool_name == 'create_file':
                                with st.expander(f"📝 Created file: {tool_input.get('path', '')}", expanded=False):
                                    content = tool_input.get('content', '')
                                    if content:
                                        code_block_with_copy(content, language='python')
                                    if result.get('success'):
                                        st.success("✅ File created successfully")
                                    else:
                                        st.error(f"❌ Error: {result.get('error')}")
                            
                            elif tool_name == 'read_file':
                                with st.expander(f"📖 Read file: {tool_input.get('path', '')}", expanded=False):
                                    if result.get('success'):
                                        content = result.get('content', '')
                                        if content:
                                            code_block_with_copy(content, language='python')
                                    else:
                                        st.error(f"❌ Error: {result.get('error')}")
                            
                            elif tool_name == 'list_files':
                                directory = tool_input.get('directory', '/home/user')
                                with st.expander(f"📂 Listed files in {directory}", expanded=False):
                                    if result.get('success'):
                                        files = result.get('files', [])
                                        if files:
                                            for f in files:
                                                st.text(f)
                                        else:
                                            st.info("No files found")
                                    else:
                                        st.error(f"❌ Error: {result.get('error')}")
                            
                            elif tool_name == 'execute_python':
                                code = tool_input.get('code')
                                file_path = tool_input.get('file_path')
                                
                                if file_path:
                                    title = f"▶️ Executed: {file_path}"
                                else:
                                    title = f"▶️ Executed code (Iteration {iteration})"
                                
                                with st.expander(title, expanded=True):
                                    if code:
                                        code_block_with_copy(code, language='python', label="📝 Code:")
                                    
                                    if result.get('success'):
                                        st.success("✅ Success")
                                        output = result.get('output', '(no output)')
                                        if output and output != '(no output)':
                                            code_block_with_copy(output, language='text', label="💾 Output:")
                                        else:
                                            st.text(output)
                                    else:
                                        st.error("❌ Error")
                                        error = result.get('error', 'Unknown error')
                                        if error:
                                            code_block_with_copy(error, language='text', label="⚠️ Error:")
                            
                            elif tool_name == 'save_file':
                                filepath = tool_input.get('filepath', '')
                                with st.expander(f"💾 Saved: {filepath}", expanded=False):
                                    if result.get('success'):
                                        action = result.get('action', 'saved')
                                        st.success(f"✅ File {action}")
                                        
                                        # Show file details
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            st.caption(f"📄 Type: {result.get('file_type', 'unknown')}")
                                        with col2:
                                            st.caption(f"📊 Size: {result.get('size', 0)} bytes")
                                        
                                        # Show description if provided
                                        description = tool_input.get('description')
                                        if description:
                                            st.info(f"📝 {description}")
                                    else:
                                        st.error(f"❌ Error: {result.get('error')}")
                        
                        elif block.get('type') == 'text':
                            st.markdown(block.get('text', ''))
                
                elif isinstance(content, str):
                    st.markdown(content)


def send_message(user_input: str):
    """Send a message to Claude with multi-file tool support"""
    if not user_input.strip():
        return
    
    # Get files in context
    files = st.session_state.db.get_files(st.session_state.current_chat_id)
    files_in_context = [f for f in files if f.in_context]
    
    # Build message content
    message_content = []
    
    # Add files (only if this is the first message or files are new)
    for file in files_in_context:
        claude_format = st.session_state.file_handler.convert_to_claude_format(
            file.file_path,
            file.file_type
        )
        if claude_format:
            message_content.append(claude_format)
    
    # Add user text
    message_content.append({
        "type": "text",
        "text": user_input
    })
    
    # Display user message IMMEDIATELY
    with st.chat_message("user"):
        # Show file indicators
        for file in files_in_context:
            if file.file_type == 'pdf':
                st.caption(f"📄 {file.filename}")
            elif file.file_type in ['png', 'jpg', 'jpeg', 'webp']:
                st.caption(f"🖼️ {file.filename}")
            else:
                st.caption(f"📎 {file.filename}")
        
        # Show user's text
        st.markdown(user_input)
    
    # Save user message and get message_id
    user_msg_tokens = estimate_message_tokens(
        message_content,
        config['context']['token_estimation_ratio']
    )
    
    user_message = st.session_state.db.add_message(
        chat_id=st.session_state.current_chat_id,
        role="user",
        content=message_content,
        token_count=user_msg_tokens
    )
    message_id = user_message.id  # Get message ID for logging
    
    print(f"[APP] User message saved with ID: {message_id}")
    
    # Get conversation history
    all_messages = st.session_state.db.get_messages(st.session_state.current_chat_id)
    
    # Convert to Claude API format and apply context limit
    claude_messages = []
    for msg in all_messages[:-1]:  # Exclude the message we just added
        # Skip tool_result messages that are already in conversation
        if msg.role == "user" and isinstance(msg.content, list):
            if any(block.get('type') == 'tool_result' for block in msg.content):
                continue
        
        # Filter out tool_result_display blocks (display-only, not valid for API)
        content = msg.content
        if isinstance(content, list):
            # Remove tool_result_display blocks before sending to API
            content = [block for block in content if block.get('type') != 'tool_result_display']
        
        claude_messages.append({
            "role": msg.role,
            "content": content
        })
    
    # Apply context window limit
    claude_messages = get_context_messages(
        claude_messages,
        config['context']['max_tokens'],
        config['context']['token_estimation_ratio']
    )
    
    # Add current message
    claude_messages.append({
        "role": "user",
        "content": message_content
    })
    
    # Call Claude API with multi-file tool support
    with st.chat_message("assistant"):
        # Create placeholder for execution details
        execution_placeholder = st.container()
        response_placeholder = st.container()
        
        # Initialize response to None
        response = None
        error_occurred = False
        error_message = None
        
        with st.spinner("🤔 Claude is thinking..."):
            try:
                # Get current chat to access sandbox_id
                chat = st.session_state.db.get_chat(st.session_state.current_chat_id)
                current_sandbox_id = chat.sandbox_id if chat else None
                
                # Setup tool executor if available
                tool_executor = None
                iteration_counter = [0]  # Use list to allow modification in closure
                
                if st.session_state.code_executor:
                    # Create closure to capture chat_id, sandbox_id, and message_id
                    def tool_exec(tool_name: str, tool_input: dict):
                        """Execute a tool and update sandbox_id"""
                        nonlocal current_sandbox_id
                        current_iteration = iteration_counter[0]
                        iteration_counter[0] += 1
                        
                        if tool_name == "create_file":
                            result = st.session_state.code_executor.create_file(
                                st.session_state.current_chat_id,
                                current_sandbox_id,
                                tool_input['path'],
                                tool_input['content'],
                                message_id=message_id,
                                iteration=current_iteration
                            )
                        elif tool_name == "read_file":
                            result = st.session_state.code_executor.read_file(
                                st.session_state.current_chat_id,
                                current_sandbox_id,
                                tool_input['path'],
                                message_id=message_id,
                                iteration=current_iteration
                            )
                        elif tool_name == "list_files":
                            directory = tool_input.get('directory', '/home/user')
                            result = st.session_state.code_executor.list_files(
                                st.session_state.current_chat_id,
                                current_sandbox_id,
                                directory,
                                message_id=message_id,
                                iteration=current_iteration
                            )
                        elif tool_name == "execute_python":
                            code = tool_input.get('code')
                            file_path = tool_input.get('file_path')
                            result = st.session_state.code_executor.execute_python(
                                st.session_state.current_chat_id,
                                current_sandbox_id,
                                code=code,
                                file_path=file_path,
                                message_id=message_id,
                                iteration=current_iteration
                            )
                        elif tool_name == "save_file":
                            result = st.session_state.code_executor.save_file(
                                st.session_state.current_chat_id,
                                current_sandbox_id,
                                tool_input['filepath'],
                                tool_input.get('description', ''),
                                message_id=message_id,
                                iteration=current_iteration
                            )
                        else:
                            result = {"success": False, "error": f"Unknown tool: {tool_name}"}
                        
                        # Update sandbox_id if it changed
                        if result.get('sandbox_id') and result['sandbox_id'] != current_sandbox_id:
                            current_sandbox_id = result['sandbox_id']
                            st.session_state.db.update_chat(
                                st.session_state.current_chat_id,
                                sandbox_id=current_sandbox_id
                            )
                        
                        return result
                    
                    tool_executor = tool_exec
                
                response = st.session_state.claude_client.send_message(
                    claude_messages,
                    chat_id=st.session_state.current_chat_id,
                    message_id=message_id,
                    tool_executor=tool_executor,
                    max_iterations=config['code_execution']['max_iterations']
                )
            
            except Exception as e:
                error_occurred = True
                error_message = str(e)
                print(f"[APP] Error during message processing: {error_message}")
                import traceback
                traceback.print_exc()
                # Don't return - continue to display what we have
        
        # Display error if one occurred
        if error_occurred:
            with response_placeholder:
                st.error(f"❌ Error: {error_message}")
                
                # Check if it's a sandbox issue
                if "Sandbox is not open" in error_message or "Sandbox" in error_message:
                    st.warning("💡 **Sandbox Issue Detected**")
                    st.info("""
                    The sandbox connection was lost or expired. This can happen if:
                    - The sandbox timed out
                    - There's a stale sandbox ID in the database
                    
                    **To fix:**
                    1. Start a new chat (sidebar)
                    2. Or clear database: `rm -f data/chats.db` and restart
                    """)
        
        # After spinner completes, display execution details (PERSISTENT)
        # Even if error occurred, show what we got
        if response:
            with execution_placeholder:
                # Display tool calls if any
                if response.get('tool_calls'):
                    for tool_call in response['tool_calls']:
                        tool_name = tool_call['tool']
                        tool_input = tool_call['input']
                        result = tool_call['result']
                        iteration = tool_call['iteration']
                        
                        if tool_name == "create_file":
                            with st.expander(f"📝 Created file: {tool_input['path']}", expanded=False):
                                content = tool_input.get('content', '')
                                if content:
                                    code_block_with_copy(content, language='python')
                                if result.get('success'):
                                    st.success("✅ File created successfully")
                                else:
                                    st.error(f"❌ Error: {result.get('error')}")
                        
                        elif tool_name == "read_file":
                            with st.expander(f"📖 Read file: {tool_input['path']}", expanded=False):
                                if result.get('success'):
                                    content = result.get('content', '')
                                    if content:
                                        code_block_with_copy(content, language='python')
                                else:
                                    st.error(f"❌ Error: {result.get('error')}")
                        
                        elif tool_name == "list_files":
                            with st.expander(f"📂 Listed files in {tool_input.get('directory', '/home/user')}", expanded=False):
                                if result.get('success'):
                                    files = result.get('files', [])
                                    if files:
                                        for f in files:
                                            st.text(f)
                                    else:
                                        st.info("No files found")
                                else:
                                    st.error(f"❌ Error: {result.get('error')}")
                        
                        elif tool_name == "execute_python":
                            code = tool_input.get('code')
                            file_path = tool_input.get('file_path')
                            
                            if file_path:
                                title = f"▶️ Executed: {file_path}"
                            else:
                                title = f"▶️ Executed code (Iteration {iteration})"
                            
                            with st.expander(title, expanded=True):
                                if code:
                                    code_block_with_copy(code, language='python', label="📝 Code:")
                                
                                if result.get('success'):
                                    st.success("✅ Success")
                                    output = result.get('output', '(no output)')
                                    if output and output != '(no output)':
                                        code_block_with_copy(output, language='text', label="💾 Output:")
                                    else:
                                        st.text(output)
                                else:
                                    st.error("❌ Error")
                                    error = result.get('error', 'Unknown error')
                                    if error:
                                        code_block_with_copy(error, language='text', label="⚠️ Error:")
                        
                        elif tool_name == "save_file":
                            filepath = tool_input.get('filepath', '')
                            with st.expander(f"💾 Saved: {filepath}", expanded=False):
                                if result.get('success'):
                                    action = result.get('action', 'saved')
                                    st.success(f"✅ File {action}")
                                    
                                    # Show file details
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.caption(f"📄 Type: {result.get('file_type', 'unknown')}")
                                    with col2:
                                        st.caption(f"📊 Size: {result.get('size', 0)} bytes")
                                    
                                    # Show description if provided
                                    description = tool_input.get('description')
                                    if description:
                                        st.info(f"📝 {description}")
                                else:
                                    st.error(f"❌ Error: {result.get('error')}")
            
            # Display response content (PERSISTENT)
            with response_placeholder:
                # Check if max iterations reached
                if response.get('max_iterations_reached'):
                    st.warning(f"⚠️ Maximum iterations ({config['code_execution']['max_iterations']}) reached.")
                
                # Display thinking and final response
                for block in response['content']:
                    if block.get('type') == 'thinking':
                        if config['code_execution']['ui']['show_thinking']:
                            with st.expander("🤔 View Thinking Process"):
                                st.markdown(block.get('thinking', ''))
                    elif block.get('type') == 'text':
                        st.markdown(block.get('text', ''))
            
            # Display execution timeline from database (PERSISTENT)
            events = st.session_state.db.get_execution_events(
                st.session_state.current_chat_id,
                message_id=message_id
            )
            
            if events:
                with st.expander("📊 Execution Timeline", expanded=False):
                    for event in events:
                        if event['type'] == 'thinking':
                            st.write(f"**🤔 Thinking** (Iteration {event['iteration']})")
                            st.caption(f"{event['timestamp'].strftime('%H:%M:%S')}")
                            with st.expander("View thinking", expanded=False):
                                thinking_preview = event['thinking_text'][:200] + "..." if len(event['thinking_text']) > 200 else event['thinking_text']
                                st.text(thinking_preview)
                        
                        elif event['type'] == 'tool_call':
                            status_icon = "✅" if event['status'] == 'success' else "❌"
                            tool_icon = {
                                'create_file': '📝',
                                'read_file': '📖',
                                'list_files': '📂',
                                'execute_python': '▶️'
                            }.get(event['tool_name'], '⚙️')
                            
                            exec_time = f" ({event['execution_time_ms']:.1f}ms)" if event['execution_time_ms'] else ""
                            st.write(f"{status_icon} {tool_icon} **{event['tool_name']}** (Iteration {event['iteration']}){exec_time}")
                            st.caption(f"{event['timestamp'].strftime('%H:%M:%S')}")
                            
                            if event['status'] == 'error':
                                st.error(f"Error: {event['error_msg']}")
                    
                    st.divider()
                    st.caption(f"Total events: {len(events)}")
            
            # Save assistant message (with tool_use blocks if any)
            assistant_tokens = response['usage']['output_tokens']
            
            # Embed execution results in content for persistence
            enriched_content = list(response['content'])  # Make a copy
            
            if response.get('tool_calls'):
                # For each tool_use block, add corresponding execution result
                for tool_call in response['tool_calls']:
                    # Find the matching tool_use block
                    tool_use_id = None
                    for block in enriched_content:
                        if block.get('type') == 'tool_use' and block.get('name') == tool_call['tool']:
                            tool_use_id = block.get('id')
                            break
                    
                    # Add execution result block after the tool_use block
                    result_block = {
                        "type": "tool_result_display",
                        "tool_use_id": tool_use_id,
                        "tool_name": tool_call['tool'],
                        "tool_input": tool_call['input'],
                        "result": tool_call['result'],
                        "iteration": tool_call['iteration']
                    }
                    enriched_content.append(result_block)
            
            st.session_state.db.add_message(
                chat_id=st.session_state.current_chat_id,
                role="assistant",
                content=enriched_content,
                token_count=assistant_tokens
            )
            
            # Save tool_result messages if any tool calls occurred
            if response.get('tool_calls'):
                # Find the tool_use blocks in the response
                tool_use_blocks = [b for b in response['content'] if b.get('type') == 'tool_use']
                
                if tool_use_blocks:
                    # Create tool_result content
                    tool_results = []
                    for tool_use, tool_call in zip(tool_use_blocks, response['tool_calls']):
                        result = tool_call['result']
                        
                        # Format result content
                        if result.get('success'):
                            if tool_call['tool'] == 'create_file':
                                result_content = result.get('message', 'File created')
                            elif tool_call['tool'] == 'read_file':
                                result_content = result.get('content', '')
                            elif tool_call['tool'] == 'list_files':
                                files = result.get('files', [])
                                result_content = '\n'.join(files) if files else 'No files'
                            elif tool_call['tool'] == 'execute_python':
                                result_content = result.get('output', '(no output)')
                            elif tool_call['tool'] == 'save_file':
                                filepath = result.get('filepath', 'file')
                                action = result.get('action', 'saved')
                                result_content = f"File {action}: {filepath}"
                            else:
                                result_content = str(result)
                        else:
                            result_content = result.get('error', 'Unknown error')
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use['id'],
                            "content": result_content
                        })
                    
                    # Save tool results as user message (for conversation history)
                    st.session_state.db.add_message(
                        chat_id=st.session_state.current_chat_id,
                        role="user",
                        content=tool_results,
                        token_count=0  # Tool results don't count toward user tokens
                    )
            
            # Update chat title if it's "New Chat"
            if chat and chat.title == "New Chat":
                # Use first message preview as title
                title = truncate_text(user_input, 40)
                st.session_state.db.update_chat(
                    st.session_state.current_chat_id,
                    title=title
                )
    
    # Rerun to update sidebar
    st.rerun()


def render_chat_area():
    """Render the main chat area"""
    if not st.session_state.current_chat_id:
        st.info("👈 Create or select a chat to get started!")
        return
    
    # Chat header
    chat = st.session_state.db.get_chat(st.session_state.current_chat_id)
    
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title(chat.title)
    
    with col2:
        if st.button("🗑️ Delete Chat"):
            delete_current_chat()
    
    # Show cost estimate
    if config['costs']['show_cost_estimate']:
        total_cost = calculate_cost(
            chat.total_tokens // 2,  # Rough input/output split
            chat.total_tokens // 2,
            config['costs']['input_cost_per_million'],
            config['costs']['output_cost_per_million']
        )
        st.caption(f"💰 Estimated cost: {format_cost(total_cost)} | 🎯 {format_token_count(chat.total_tokens)} tokens")
    
    st.divider()
    
    # Messages
    render_messages()
    
    # Chat input
    user_input = st.chat_input("Type your message...")
    if user_input:
        send_message(user_input)


def main():
    """Main application"""
    st.set_page_config(
        page_title=config['ui']['page_title'],
        page_icon=config['ui']['page_icon'],
        layout="wide"
    )
    
    # Initialize
    init_session_state()
    
    # Create initial chat if none exist
    chats = st.session_state.db.get_all_chats()
    if not chats:
        create_new_chat()
    elif not st.session_state.current_chat_id:
        st.session_state.current_chat_id = chats[0].id
    
    # Layout
    render_sidebar()
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        render_chat_area()
    
    with col2:
        render_file_upload()


if __name__ == "__main__":
    main()
