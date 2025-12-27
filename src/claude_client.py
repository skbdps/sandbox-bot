"""
Claude API client wrapper.
"""

from typing import List, Dict, Any, Optional, Callable
from anthropic import Anthropic


class ClaudeClient:
    """Wrapper for Claude API"""
    
    def __init__(self, api_key: str, model: str, max_tokens: int, extended_thinking: bool, db=None):
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.extended_thinking = extended_thinking
        self.db = db  # Database instance for logging
        
        # Define tools for multi-file code execution
        self.tools = [
            {
                "name": "create_file",
                "description": """Create or overwrite a file in the project workspace.

Use this to:
- Create new Python files, modules, or scripts
- Save data files (JSON, CSV, TXT)
- Build multi-file projects with proper structure

The workspace is persistent across the conversation. Files you create remain available for import and execution.

Best practices:
- Use /home/user/ as the base directory (e.g., /home/user/main.py)
- Organize code into modules (e.g., /home/user/utils.py, /home/user/models.py)
- Create proper Python packages with __init__.py files""",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path starting with /home/user/ (e.g., /home/user/utils.py)"
                        },
                        "content": {
                            "type": "string",
                            "description": "Complete file content"
                        }
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "read_file",
                "description": """Read the contents of a file from the project workspace.

Use this to:
- Review code you've written
- Check file contents before editing
- Debug by examining current state""",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path to read (e.g., /home/user/utils.py)"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "list_files",
                "description": """List all files in the project workspace.

Use this to:
- See what files exist in the project
- Check project structure
- Find files before editing""",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "Directory to list (default: /home/user)"
                        }
                    }
                }
            },
            {
                "name": "execute_python",
                "description": """Execute Python code or run a file in the project workspace.

The workspace is persistent - you can:
- Import from files you've created
- Build on previous executions
- Test multi-file projects

Supports:
- Direct code execution (for quick tests)
- File execution (for running complete programs)
- pip install for packages
- 60 second timeout

Limitations:
- No GUI applications
- Files outside /home/user are not accessible""",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python code to execute directly (optional if file_path provided)"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Path to Python file to execute (optional if code provided). Relative to /home/user (e.g., 'main.py' or '/home/user/main.py')"
                        }
                    }
                }
            },
            {
                "name": "save_file",
                "description": """Save a file from the sandbox to persistent storage.

Use this to preserve important files that should outlive the current session:
- Project files (main.py, utils.py, models.py, config.json)
- Multi-file applications with proper structure
- Deliverables (analysis results, generated reports, data outputs)

Do NOT use for:
- Temporary calculations or quick tests
- Debug code that won't be reused  
- Intermediate steps in data processing

The file must already exist in the sandbox (created with create_file or execute_python).
Files are saved with their directory structure preserved (e.g., 'project/utils.py' maintains hierarchy).

When working on projects, save each file after creating it to ensure persistence.

Example workflow:
1. create_file("/home/user/calculator/utils.py", utility_code)
2. save_file("calculator/utils.py", "Utility functions for calculator")
3. create_file("/home/user/calculator/main.py", main_code)  
4. save_file("calculator/main.py", "Main calculator application")

Saved files will:
- Persist even if the sandbox expires
- Be available for download by the user
- Maintain project directory structure
- Can be updated by saving again with same filepath""",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "filepath": {
                            "type": "string",
                            "description": "Path of file in sandbox to save (e.g., 'calculator/main.py' or '/home/user/main.py'). Can be relative or absolute."
                        },
                        "description": {
                            "type": "string",
                            "description": "Optional description of what this file does or why it's important (helps organize saved files)"
                        }
                    },
                    "required": ["filepath"]
                }
            }
        ]
    
    def send_message(self, messages: List[Dict[str, Any]], 
                    chat_id: Optional[str] = None,
                    message_id: Optional[str] = None,
                    tool_executor: Optional[Callable] = None,
                    max_iterations: int = 10) -> Dict[str, Any]:
        """
        Send a message to Claude with optional tool execution support.
        
        Args:
            messages: List of messages in Claude API format
            chat_id: Chat ID for logging
            message_id: Message ID for logging
            tool_executor: Optional function to execute tools
            max_iterations: Maximum tool use iterations
        
        Returns:
            Response dict with content blocks and execution history
        """
        iteration = 0
        all_tool_calls = []  # Track all tool executions
        current_messages = messages.copy()
        
        while iteration < max_iterations:
            try:
                # Build request parameters
                request_params = {
                    "model": self.model,
                    "max_tokens": self.max_tokens,
                    "messages": current_messages
                }
                
                # Add extended thinking if enabled
                if self.extended_thinking:
                    request_params["thinking"] = {"type": "enabled","budget_tokens":5000}
                
                # Add tools if executor provided
                if tool_executor:
                    request_params["tools"] = self.tools
                
                response = self.client.messages.create(**request_params)
                
                # Convert response to dict format
                content = [self._content_block_to_dict(block) for block in response.content]
                
                # Log thinking events
                if self.db and chat_id:
                    for block in content:
                        if block.get('type') == 'thinking':
                            self.db.log_thinking(
                                chat_id=chat_id,
                                thinking_text=block.get('thinking', ''),
                                signature=block.get('signature'),
                                message_id=message_id,
                                iteration=iteration
                            )
                
                # Check for tool use
                tool_use_blocks = [b for b in content if b.get('type') == 'tool_use']
                
                # If no tool use, we're done
                if not tool_use_blocks or not tool_executor:
                    return {
                        "content": content,
                        "usage": {
                            "input_tokens": response.usage.input_tokens,
                            "output_tokens": response.usage.output_tokens
                        },
                        "tool_calls": all_tool_calls
                    }
                
                # Execute each tool
                tool_results = []
                for tool_use in tool_use_blocks:
                    tool_name = tool_use['name']
                    tool_input = tool_use['input']
                    
                    # Execute tool
                    result = tool_executor(tool_name, tool_input)
                    
                    # DEBUG: Log the raw result
                    print(f"[CLAUDE] Tool {tool_name} returned: success={result.get('success')}, output_len={len(str(result.get('output', '')))}")
                    if not result.get('success'):
                        print(f"[CLAUDE] Error: {result.get('error', 'Unknown')}")
                    
                    # Track execution
                    all_tool_calls.append({
                        "iteration": iteration + 1,
                        "tool": tool_name,
                        "input": tool_input,
                        "result": result
                    })
                    
                    # Format result for Claude
                    if result.get("success"):
                        # Success - provide clean output
                        if tool_name == "create_file":
                            result_content = result.get("message", "File created successfully")
                        elif tool_name == "read_file":
                            result_content = f"File contents:\n\n{result.get('content', '')}"
                        elif tool_name == "list_files":
                            files = result.get('files', [])
                            if files:
                                result_content = f"Files in {result.get('directory', '/home/user')}:\n" + "\n".join(files)
                            else:
                                result_content = "No files found"
                        elif tool_name == "execute_python":
                            output = result.get("output", "")
                            # Be explicit about empty output vs actual output
                            if output and output != "(no output)":
                                result_content = output
                            else:
                                result_content = "Code executed successfully with no output."
                            print(f"[CLAUDE] Sending to Claude: {result_content[:100]}")
                        elif tool_name == "save_file":
                            filepath = result.get('filepath', 'file')
                            action = result.get('action', 'saved')
                            result_content = f"File {action}: {filepath} ({result.get('size', 0)} bytes)"
                            print(f"[CLAUDE] File saved: {filepath} ({action})")
                        else:
                            result_content = str(result)
                    else:
                        # Error - provide error message
                        result_content = result.get("error", "Unknown error")
                        print(f"[CLAUDE] Sending error to Claude: {result_content[:100]}")
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use['id'],
                        "content": result_content
                    })
                
                # Add assistant message with tool use
                current_messages.append({
                    "role": "assistant",
                    "content": content
                })
                
                # Add tool results as user message
                current_messages.append({
                    "role": "user",
                    "content": tool_results
                })
                
                iteration += 1
            
            except Exception as e:
                raise Exception(f"Claude API error: {str(e)}")
        
        # Max iterations reached - return last response
        return {
            "content": content,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            },
            "tool_calls": all_tool_calls,
            "max_iterations_reached": True
        }
    
    def _content_block_to_dict(self, block: Any) -> Dict[str, Any]:
        """Convert content block to dict"""
        if hasattr(block, 'type'):
            if block.type == 'text':
                return {
                    "type": "text",
                    "text": block.text
                }
            elif block.type == 'thinking':
                result = {
                    "type": "thinking",
                    "thinking": block.thinking
                }
                # Capture signature if present
                if hasattr(block, 'signature'):
                    result['signature'] = block.signature
                return result
            elif block.type == 'tool_use':
                return {
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                }
        
        # Fallback
        return {"type": "text", "text": str(block)}
