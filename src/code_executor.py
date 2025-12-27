"""
Code execution using E2B sandbox with stateful multi-file support.
"""

import os
import time
from typing import Dict, Any, Optional, List


class CodeExecutor:
    """Execute Python code in persistent E2B sandbox with multi-file support"""
    
    def __init__(self, timeout_seconds: int = 60, db=None):
        self.timeout_seconds = timeout_seconds
        self.api_key = os.getenv('E2B_API_KEY')
        self.db = db  # Database instance for logging
        
        if not self.api_key:
            raise ValueError("E2B_API_KEY not found in environment variables")
        
        # Cache of active sandboxes by chat_id
        self._sandboxes = {}
    
    def get_or_create_sandbox(self, chat_id: str, sandbox_id: Optional[str] = None):
        """
        Get existing sandbox or create new one for a chat.
        
        Args:
            chat_id: Chat ID to associate sandbox with
            sandbox_id: Optional existing sandbox ID to reconnect to
        
        Returns:
            Sandbox instance
        """
        try:
            from e2b_code_interpreter import CodeInterpreter
            
            # Check if sandbox already in memory
            if chat_id in self._sandboxes:
                return self._sandboxes[chat_id]
            
            # Try to reconnect to existing sandbox
            if sandbox_id:
                try:
                    sandbox = CodeInterpreter(sandbox_id=sandbox_id, api_key=self.api_key, timeout=self.timeout_seconds)
                    self._sandboxes[chat_id] = sandbox
                    print(f"[E2B] Reconnected to sandbox: {sandbox_id}")
                    return sandbox
                except Exception as e:
                    # Sandbox might have expired, create new one
                    print(f"[E2B] Failed to reconnect to {sandbox_id}: {str(e)}")
                    pass
            
            # Create new sandbox
            sandbox = CodeInterpreter(api_key=self.api_key, timeout=self.timeout_seconds)
            self._sandboxes[chat_id] = sandbox
            print(f"[E2B] Created new sandbox: {sandbox.id}")
            return sandbox
        
        except ImportError:
            raise ValueError("E2B code interpreter not installed. Run: pip install e2b-code-interpreter")
    
    def close_sandbox(self, chat_id: str):
        """Close and cleanup sandbox for a chat"""
        if chat_id in self._sandboxes:
            try:
                self._sandboxes[chat_id].close()
            except Exception:
                pass
            del self._sandboxes[chat_id]
    
    def _execute_with_retry(self, chat_id: str, sandbox_id: Optional[str], operation, operation_name: str):
        """
        Execute an operation with automatic retry on sandbox expiration.
        
        This handles the case where a sandbox has expired server-side but we still
        have a reference to it locally. On "Sandbox is not open" errors, we:
        1. Clear the stale sandbox
        2. Create a new sandbox
        3. Retry the operation once
        
        Args:
            chat_id: Chat ID
            sandbox_id: Current sandbox ID (may be stale)
            operation: Callable that takes sandbox as argument
            operation_name: Name for logging
        
        Returns:
            Tuple of (result, new_sandbox_id)
        """
        try:
            # Try with existing/new sandbox
            sandbox = self.get_or_create_sandbox(chat_id, sandbox_id)
            result = operation(sandbox)
            return result, sandbox.id
        
        except Exception as e:
            error_str = str(e).lower()
            
            # Check if it's a sandbox expiration error
            if any(keyword in error_str for keyword in ['sandbox is not open', 'sandbox not found', 'cannot be found']):
                print(f"[E2B] Sandbox expired for {operation_name}, creating new sandbox...")
                
                # Clear stale sandbox
                if chat_id in self._sandboxes:
                    del self._sandboxes[chat_id]
                
                # Create fresh sandbox and retry ONCE
                try:
                    sandbox = self.get_or_create_sandbox(chat_id, None)  # Force new sandbox
                    result = operation(sandbox)
                    print(f"[E2B] Successfully retried {operation_name} with new sandbox: {sandbox.id}")
                    return result, sandbox.id
                except Exception as retry_error:
                    # If retry also fails, raise that error
                    raise retry_error
            else:
                # Not a sandbox expiration error, just raise it
                raise
    
    def create_file(self, chat_id: str, sandbox_id: Optional[str], path: str, content: str,
                   message_id: Optional[str] = None, iteration: int = 0) -> Dict[str, Any]:
        """
        Create or overwrite a file in the sandbox.
        
        Args:
            chat_id: Chat ID
            sandbox_id: Sandbox ID (may be None for new sandbox)
            path: File path (e.g., "/home/user/utils.py")
            content: File content
            message_id: Message ID for logging
            iteration: Iteration number in agentic loop
        
        Returns:
            Dict with success status and sandbox_id
        """
        # Log start of tool call
        event_id = None
        if self.db:
            event_id = self.db.log_tool_call(
                chat_id=chat_id,
                tool_name='create_file',
                tool_input={'path': path, 'content': content},
                message_id=message_id,
                iteration=iteration
            )
        
        start_time = time.time()
        
        try:
            # Define the operation
            def create_operation(sandbox):
                # Ensure directory exists
                dir_path = os.path.dirname(path)
                if dir_path and dir_path != '/':
                    sandbox.process.start(f"mkdir -p {dir_path}")
                
                # Write file
                sandbox.filesystem.write(path, content)
                return True
            
            # Execute with automatic retry on sandbox expiration
            _, new_sandbox_id = self._execute_with_retry(
                chat_id, sandbox_id, create_operation, "create_file"
            )
            
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            
            result = {
                "success": True,
                "message": f"Created file: {path}",
                "sandbox_id": new_sandbox_id,
                "path": path
            }
            
            # Log success
            if self.db and event_id:
                self.db.update_tool_call(
                    event_id=event_id,
                    status='success',
                    tool_output=result,
                    sandbox_id=new_sandbox_id,
                    execution_time_ms=execution_time
                )
            
            print(f"[E2B] Created file: {path} in {execution_time:.1f}ms")
            return result
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = f"Failed to create file: {str(e)}"
            
            result = {
                "success": False,
                "error": error_msg,
                "sandbox_id": sandbox_id
            }
            
            # Log error
            if self.db and event_id:
                self.db.update_tool_call(
                    event_id=event_id,
                    status='error',
                    error_msg=error_msg,
                    execution_time_ms=execution_time
                )
            
            print(f"[E2B] Error creating file: {error_msg}")
            return result
    
    def read_file(self, chat_id: str, sandbox_id: Optional[str], path: str,
                 message_id: Optional[str] = None, iteration: int = 0) -> Dict[str, Any]:
        """
        Read a file from the sandbox.
        
        Args:
            chat_id: Chat ID
            sandbox_id: Sandbox ID
            path: File path
            message_id: Message ID for logging
            iteration: Iteration number
        
        Returns:
            Dict with file content or error
        """
        # Log start
        event_id = None
        if self.db:
            event_id = self.db.log_tool_call(
                chat_id=chat_id,
                tool_name='read_file',
                tool_input={'path': path},
                message_id=message_id,
                iteration=iteration
            )
        
        start_time = time.time()
        
        try:
            # Define the operation
            def read_operation(sandbox):
                return sandbox.filesystem.read(path)
            
            # Execute with automatic retry on sandbox expiration
            content, new_sandbox_id = self._execute_with_retry(
                chat_id, sandbox_id, read_operation, "read_file"
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            result = {
                "success": True,
                "content": content,
                "path": path,
                "sandbox_id": new_sandbox_id
            }
            
            # Log success
            if self.db and event_id:
                self.db.update_tool_call(
                    event_id=event_id,
                    status='success',
                    tool_output={'path': path, 'size': len(content)},
                    sandbox_id=new_sandbox_id,
                    execution_time_ms=execution_time
                )
            
            print(f"[E2B] Read file: {path} ({len(content)} chars) in {execution_time:.1f}ms")
            return result
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = f"Failed to read file: {str(e)}"
            
            result = {
                "success": False,
                "error": error_msg,
                "sandbox_id": sandbox_id
            }
            
            # Log error
            if self.db and event_id:
                self.db.update_tool_call(
                    event_id=event_id,
                    status='error',
                    error_msg=error_msg,
                    execution_time_ms=execution_time
                )
            
            print(f"[E2B] Error reading file: {error_msg}")
            return result
    
    def list_files(self, chat_id: str, sandbox_id: Optional[str], directory: str = "/home/user",
                  message_id: Optional[str] = None, iteration: int = 0) -> Dict[str, Any]:
        """
        List files in a directory.
        
        Args:
            chat_id: Chat ID
            sandbox_id: Sandbox ID
            directory: Directory to list (default: /home/user)
            message_id: Message ID for logging
            iteration: Iteration number
        
        Returns:
            Dict with file list or error
        """
        # Log start
        event_id = None
        if self.db:
            event_id = self.db.log_tool_call(
                chat_id=chat_id,
                tool_name='list_files',
                tool_input={'directory': directory},
                message_id=message_id,
                iteration=iteration
            )
        
        start_time = time.time()
        
        try:
            # Define the operation
            def list_operation(sandbox):
                # Use ls command to list files
                result = sandbox.process.start(f"find {directory} -type f 2>/dev/null || echo 'No files'")
                
                files = []
                if result.stdout:
                    files = [f.strip() for f in result.stdout.split('\n') if f.strip() and f.strip() != 'No files']
                
                return files
            
            # Execute with automatic retry on sandbox expiration
            files, new_sandbox_id = self._execute_with_retry(
                chat_id, sandbox_id, list_operation, "list_files"
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            output = {
                "success": True,
                "files": files,
                "directory": directory,
                "sandbox_id": new_sandbox_id
            }
            
            # Log success
            if self.db and event_id:
                self.db.update_tool_call(
                    event_id=event_id,
                    status='success',
                    tool_output={'file_count': len(files)},
                    sandbox_id=new_sandbox_id,
                    execution_time_ms=execution_time
                )
            
            print(f"[E2B] Listed files: {len(files)} files in {directory} ({execution_time:.1f}ms)")
            return output
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = f"Failed to list files: {str(e)}"
            
            output = {
                "success": False,
                "error": error_msg,
                "sandbox_id": sandbox_id
            }
            
            # Log error
            if self.db and event_id:
                self.db.update_tool_call(
                    event_id=event_id,
                    status='error',
                    error_msg=error_msg,
                    execution_time_ms=execution_time
                )
            
            print(f"[E2B] Error listing files: {error_msg}")
            return output
    
    def execute_python(self, chat_id: str, sandbox_id: Optional[str], 
                      code: Optional[str] = None, file_path: Optional[str] = None,
                      message_id: Optional[str] = None, iteration: int = 0) -> Dict[str, Any]:
        """
        Execute Python code or run a file.
        
        Args:
            chat_id: Chat ID
            sandbox_id: Sandbox ID
            code: Python code to execute (optional)
            file_path: Path to Python file to run (optional)
            message_id: Message ID for logging
            iteration: Iteration number
        
        Returns:
            Dict with execution result
        """
        # Log start
        event_id = None
        if self.db:
            event_id = self.db.log_tool_call(
                chat_id=chat_id,
                tool_name='execute_python',
                tool_input={'code': code, 'file_path': file_path},
                message_id=message_id,
                iteration=iteration
            )
        
        start_time = time.time()
        
        try:
            # Define the operation
            def execute_operation(sandbox):
                if file_path:
                    # Run a file
                    result = sandbox.process.start(f"cd /home/user && python {file_path}")
                    
                    output_parts = []
                    if result.stdout:
                        output_parts.append(result.stdout)
                    
                    if result.stderr:
                        # Check if stderr contains actual errors or just warnings
                        if result.exit_code != 0:
                            return {
                                "success": False,
                                "output": result.stdout or "",
                                "error": result.stderr,
                                "error_type": self._classify_error(result.stderr),
                                "file_path": file_path
                            }
                        else:
                            # stderr is just warnings, include it
                            output_parts.append(result.stderr)
                    
                    output = "\n".join(output_parts) if output_parts else ""
                    
                    return {
                        "success": True,
                        "output": output if output else f"File {file_path} executed successfully with no output.",
                        "error": None,
                        "file_path": file_path
                    }
                
                elif code:
                    # Execute code directly using notebook
                    execution = sandbox.notebook.exec_cell(code)
                    
                    # Check for errors
                    if execution.error:
                        error_msg = f"{execution.error.name}: {execution.error.value}"
                        return {
                            "success": False,
                            "output": "",
                            "error": error_msg,
                            "error_type": execution.error.name
                        }
                    else:
                        output_parts = []
                        
                        # Get stdout (print statements) - this is a list!
                        if execution.logs.stdout:
                            output_parts.extend(execution.logs.stdout)
                        
                        # Get stderr (warnings/errors) - this is a list!
                        if execution.logs.stderr:
                            output_parts.extend(execution.logs.stderr)
                        
                        # Get results (last expression value)
                        if execution.results:
                            for result in execution.results:
                                output_parts.append(result.text)
                        
                        output = "\n".join(output_parts) if output_parts else ""
                        
                        return {
                            "success": True,
                            "output": output if output else "Code executed successfully with no printed output.",
                            "error": None
                        }
                else:
                    raise ValueError("Either code or file_path must be provided")
            
            # Execute with automatic retry on sandbox expiration
            result_dict, new_sandbox_id = self._execute_with_retry(
                chat_id, sandbox_id, execute_operation, "execute_python"
            )
            
            # Add sandbox_id to result
            result_dict["sandbox_id"] = new_sandbox_id
            
            execution_time = (time.time() - start_time) * 1000
            
            # Handle execution result
            if not result_dict.get("success"):
                # Execution had an error
                error_msg = result_dict.get("error", "Unknown error")
                
                # Log error
                if self.db and event_id:
                    self.db.update_tool_call(
                        event_id=event_id,
                        status='error',
                        error_msg=error_msg,
                        sandbox_id=new_sandbox_id,
                        execution_time_ms=execution_time
                    )
                
                print(f"[E2B] Code execution error: {error_msg[:100]}")
                return result_dict
            else:
                # Execution succeeded
                # Log success
                if self.db and event_id:
                    self.db.update_tool_call(
                        event_id=event_id,
                        status='success',
                        tool_output={'output_length': len(result_dict.get('output', ''))},
                        sandbox_id=new_sandbox_id,
                        execution_time_ms=execution_time
                    )
                
                print(f"[E2B] Code executed successfully in {execution_time:.1f}ms")
                return result_dict
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = f"Execution error: {str(e)}"
            
            result_dict = {
                "success": False,
                "output": "",
                "error": error_msg,
                "error_type": "system",
                "sandbox_id": sandbox_id
            }
            
            # Log error
            if self.db and event_id:
                self.db.update_tool_call(
                    event_id=event_id,
                    status='error',
                    error_msg=error_msg,
                    execution_time_ms=execution_time
                )
            
            print(f"[E2B] System error: {error_msg}")
            return result_dict
    
    def _classify_error(self, error_msg: str) -> str:
        """Classify error type to help determine if it's fixable."""
        error_lower = error_msg.lower()
        
        environmental_keywords = [
            'network', 'connection', 'unreachable', 'dns',
            'no route to host', 'timeout', 'timed out',
            'ssl', 'certificate', 'url', 'socket',
            'permission denied', 'access denied'
        ]
        
        for keyword in environmental_keywords:
            if keyword in error_lower:
                return "environmental"
        
        return "code"
    
    def _detect_file_type(self, filename: str) -> str:
        """
        Detect file type from extension.
        
        Args:
            filename: Filename to analyze
        
        Returns:
            File type string (e.g., "python", "json", "text")
        """
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        
        type_map = {
            'py': 'python',
            'js': 'javascript',
            'ts': 'typescript',
            'jsx': 'javascript',
            'tsx': 'typescript',
            'html': 'html',
            'css': 'css',
            'json': 'json',
            'md': 'markdown',
            'txt': 'text',
            'csv': 'csv',
            'xml': 'xml',
            'yaml': 'yaml',
            'yml': 'yaml',
            'sh': 'bash',
            'sql': 'sql',
            'env': 'text'
        }
        
        return type_map.get(ext, 'text')
    
    def save_file(self, chat_id: str, sandbox_id: Optional[str], filepath: str,
                  description: str = "", message_id: Optional[str] = None,
                  iteration: int = 0) -> Dict[str, Any]:
        """
        Save a file from the E2B sandbox to persistent database storage.
        
        This is for files Claude wants to persist (project files, deliverables).
        NOT for temporary calculations or debug code.
        
        Args:
            chat_id: Chat ID
            sandbox_id: Sandbox ID (may be None for new sandbox)
            filepath: Path of file in sandbox (e.g., "calculator/main.py")
            description: Optional description of file purpose
            message_id: Message ID for logging
            iteration: Iteration number in agentic loop
        
        Returns:
            Dict with success status, action (created/updated), and file info
        """
        # File size limit (10MB)
        MAX_FILE_SIZE = 10 * 1024 * 1024
        
        # Log start of tool call
        event_id = None
        if self.db:
            event_id = self.db.log_tool_call(
                chat_id=chat_id,
                tool_name='save_file',
                tool_input={'filepath': filepath, 'description': description},
                message_id=message_id,
                iteration=iteration
            )
        
        start_time = time.time()
        
        print(f"[E2B] Saving file: {filepath} (description: '{description}')")
        
        try:
            # Define the operation
            def save_operation(sandbox):
                # 1. Read file content from sandbox
                try:
                    content = sandbox.filesystem.read(filepath)
                    print(f"[E2B] Read {len(content)} characters from {filepath}")
                except Exception as e:
                    print(f"[E2B] Failed to read file {filepath}: {str(e)}")
                    raise ValueError(f"File not found: {filepath}. Create it first with create_file.")
                
                # 2. Check file size
                size_bytes = len(content.encode('utf-8'))
                if size_bytes > MAX_FILE_SIZE:
                    print(f"[E2B] File too large: {size_bytes} bytes (max: {MAX_FILE_SIZE})")
                    raise ValueError(f"File too large ({size_bytes} bytes). Maximum: {MAX_FILE_SIZE} bytes (10MB)")
                
                # 3. Parse filepath
                filename = os.path.basename(filepath)
                directory = os.path.dirname(filepath)
                if directory and not directory.endswith('/'):
                    directory += '/'
                if not directory:
                    directory = None
                
                # 4. Detect file type
                file_type = self._detect_file_type(filename)
                
                print(f"[E2B] File details: name={filename}, dir={directory}, type={file_type}, size={size_bytes}")
                
                # 5. Check if file already exists in database (update vs create)
                if self.db:
                    existing = self.db.get_sandbox_file(chat_id, filepath)
                    
                    if existing:
                        # Update existing file
                        print(f"[E2B] Updating existing file in database: {filepath}")
                        self.db.update_sandbox_file(
                            existing.id,
                            content=content,
                            size_bytes=size_bytes
                        )
                        action = "updated"
                    else:
                        # Create new file
                        print(f"[E2B] Creating new file in database: {filepath}")
                        self.db.add_sandbox_file(
                            chat_id=chat_id,
                            filepath=filepath,
                            filename=filename,
                            directory=directory,
                            content=content,
                            description=description,
                            file_type=file_type,
                            size_bytes=size_bytes
                        )
                        action = "created"
                else:
                    print(f"[E2B] Warning: Database not available, file not saved to DB")
                    action = "created"
                
                return {
                    "action": action,
                    "filepath": filepath,
                    "filename": filename,
                    "size": size_bytes,
                    "file_type": file_type
                }
            
            # Execute with automatic retry on sandbox expiration
            result_data, new_sandbox_id = self._execute_with_retry(
                chat_id, sandbox_id, save_operation, "save_file"
            )
            
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            
            result = {
                "success": True,
                "message": f"File {result_data['action']}: {filepath}",
                "sandbox_id": new_sandbox_id,
                **result_data
            }
            
            # Log success
            if self.db and event_id:
                self.db.update_tool_call(
                    event_id=event_id,
                    status='success',
                    tool_output=result,
                    sandbox_id=new_sandbox_id,
                    execution_time_ms=execution_time
                )
            
            print(f"[E2B] File saved successfully: {filepath} ({result_data['action']}) in {execution_time:.1f}ms")
            return result
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = str(e)
            
            result = {
                "success": False,
                "error": error_msg,
                "sandbox_id": sandbox_id
            }
            
            # Log error
            if self.db and event_id:
                self.db.update_tool_call(
                    event_id=event_id,
                    status='error',
                    error_msg=error_msg,
                    execution_time_ms=execution_time
                )
            
            print(f"[E2B] Error saving file {filepath}: {error_msg}")
            return result
    
    def get_sandbox_id(self, chat_id: str) -> Optional[str]:
        """Get sandbox ID for a chat if it exists"""
        if chat_id in self._sandboxes:
            return self._sandboxes[chat_id].id
        return None
