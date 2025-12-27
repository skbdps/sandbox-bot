# Manual Fix Instructions

These instructions show exactly what to change to fix the output capture and directory issues.

---

## Issue 1: Output Not Being Captured

**Problem:** We were using `execution.text` and `execution.results` incorrectly.

**Solution:** Use `execution.logs.stdout` and `execution.logs.stderr` (which are lists!)

### File: `src/code_executor.py`

**Location:** Around line 443-467 in the `execute_python()` method

**FIND THIS CODE:**
```python
                else:
                    execution_time = (time.time() - start_time) * 1000
                    output_parts = []
                    
                    if execution.text:
                        output_parts.append(execution.text)
                        print(f"[E2B] execution.text: {execution.text[:100] if len(execution.text) > 100 else execution.text}")
                    
                    if execution.results:
                        print(f"[E2B] execution.results: {execution.results}")
                        for result in execution.results:
                            output_parts.append(str(result))
                    
                    output = "\n".join(output_parts) if output_parts else ""
                    
                    # Log what we're actually returning
                    print(f"[E2B] Final output ({len(output)} chars): {output[:200] if len(output) > 200 else output}")
                    
                    result_dict = {
                        "success": True,
                        "output": output if output else "Code executed successfully with no printed output.",
                        "error": None,
                        "sandbox_id": sandbox.id
                    }
```

**REPLACE WITH:**
```python
                else:
                    execution_time = (time.time() - start_time) * 1000
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
                    
                    result_dict = {
                        "success": True,
                        "output": output if output else "Code executed successfully with no printed output.",
                        "error": None,
                        "sandbox_id": sandbox.id
                    }
```

**Key Changes:**
1. `execution.text` → `execution.logs.stdout` (and use `.extend()` not `.append()`)
2. Added `execution.logs.stderr` 
3. `str(result)` → `result.text`
4. Removed debug logging

---

## Issue 2: `/project` Directory Doesn't Exist

**Problem:** E2B sandboxes don't have a `/project` directory by default.

**Solution:** Use `/home/user` which is the standard directory in E2B sandboxes.

### File: `src/claude_client.py`

#### Change 1: `create_file` tool description

**FIND (around line 22-49):**
```python
            {
                "name": "create_file",
                "description": """Create or overwrite a file in the project workspace.

Use this to:
- Create new Python files, modules, or scripts
- Save data files (JSON, CSV, TXT)
- Build multi-file projects with proper structure

The workspace is persistent across the conversation. Files you create remain available for import and execution.

Best practices:
- Use /project/ as the base directory (e.g., /project/main.py)
- Organize code into modules (e.g., /project/utils.py, /project/models.py)
- Create proper Python packages with __init__.py files""",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path starting with /project/ (e.g., /project/utils.py)"
                        },
                        "content": {
                            "type": "string",
                            "description": "Complete file content"
                        }
                    },
                    "required": ["path", "content"]
                }
            },
```

**REPLACE WITH:**
```python
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
```

**Changes:** All instances of `/project/` → `/home/user/`

---

#### Change 2: `read_file` tool description

**FIND (around line 51-69):**
```python
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
                            "description": "File path to read (e.g., /project/utils.py)"
                        }
                    },
                    "required": ["path"]
                }
            },
```

**REPLACE WITH:**
```python
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
```

**Changes:** `/project/utils.py` → `/home/user/utils.py`

---

#### Change 3: `list_files` tool description

**FIND (around line 70-87):**
```python
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
                            "description": "Directory to list (default: /project)"
                        }
                    }
                }
            },
```

**REPLACE WITH:**
```python
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
```

**Changes:** `/project` → `/home/user`

---

#### Change 4: `execute_python` tool description

**FIND (around line 88-120):**
```python
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
- No network access
- No GUI applications
- Files outside /project are not accessible""",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python code to execute directly (optional if file_path provided)"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Path to Python file to execute (optional if code provided). Relative to /project (e.g., 'main.py' or '/project/main.py')"
                        }
                    }
                }
            }
```

**REPLACE WITH:**
```python
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
            }
```

**Changes:** 
- Removed "No network access" (E2B has internet by default)
- `/project` → `/home/user`

---

#### Change 5: Result formatting for `list_files`

**FIND (around line 221-226):**
```python
                        elif tool_name == "list_files":
                            files = result.get('files', [])
                            if files:
                                result_content = f"Files in {result.get('directory', '/project')}:\n" + "\n".join(files)
                            else:
                                result_content = "No files found"
```

**REPLACE WITH:**
```python
                        elif tool_name == "list_files":
                            files = result.get('files', [])
                            if files:
                                result_content = f"Files in {result.get('directory', '/home/user')}:\n" + "\n".join(files)
                            else:
                                result_content = "No files found"
```

**Changes:** `/project` → `/home/user`

---

### File: `src/code_executor.py`

#### Change 6: Default directory for `list_files()`

**FIND (around line 232-245):**
```python
    def list_files(self, chat_id: str, sandbox_id: Optional[str], directory: str = "/project",
                  message_id: Optional[str] = None, iteration: int = 0) -> Dict[str, Any]:
        """
        List files in a directory.
        
        Args:
            chat_id: Chat ID
            sandbox_id: Sandbox ID
            directory: Directory to list
            message_id: Message ID for logging
            iteration: Iteration number
        
        Returns:
            Dict with file list or error
        """
```

**REPLACE WITH:**
```python
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
```

**Changes:** 
- `/project` → `/home/user`
- Updated docstring

---

## Optional Cleanup: Remove Excessive Debug Logging

These debug logs from the previous fix can be removed if they're too verbose:

### File: `src/code_executor.py`

**Lines ~342-344 (optional removal):**
```python
                if result.stdout:
                    output_parts.append(result.stdout)
                    print(f"[E2B] File stdout: {result.stdout[:100] if len(result.stdout) > 100 else result.stdout}")
```

**Remove the print statement, keep just:**
```python
                if result.stdout:
                    output_parts.append(result.stdout)
```

**Lines ~348-351 (optional removal):**
```python
                        execution_time = (time.time() - start_time) * 1000
                        error_msg = result.stderr
                        print(f"[E2B] File execution error (exit {result.exit_code}): {error_msg[:100]}")
```

**Remove the print statement, keep just:**
```python
                        execution_time = (time.time() - start_time) * 1000
                        error_msg = result.stderr
```

**Lines ~375-377 (optional removal):**
```python
                output = "\n".join(output_parts) if output_parts else ""
                
                print(f"[E2B] File execution output ({len(output)} chars): {output[:200] if len(output) > 200 else output}")
```

**Remove the print statement:**
```python
                output = "\n".join(output_parts) if output_parts else ""
```

---

## Summary of Changes

### Critical Fixes (MUST DO):
1. ✅ **Fix output capture** - Use `execution.logs.stdout/stderr` instead of `execution.text`
2. ✅ **Change directory** - Use `/home/user` instead of `/project`

### Files Modified:
- `src/code_executor.py` - 2 changes (output capture + default directory)
- `src/claude_client.py` - 5 changes (all tool descriptions)

### Total Changes: 7 critical changes

---

## Testing After Changes

**Test 1: Simple Print**
```
User: "Run this code: print('hello world')"
Expected terminal output:
[E2B] Code executed successfully
Expected Claude response: Should show "hello world"
```

**Test 2: File Creation**
```
User: "Create a file at /home/user/test.py with print('test')"
Expected: File created successfully
```

**Test 3: List Files**
```
User: "List files"
Expected: Shows files in /home/user
```

**Test 4: Expression Result**
```
User: "Run this: 2 + 2"
Expected: Should show "4"
```

---

## Why These Changes Work

### Output Capture
According to E2B's official documentation:
- `execution.logs.stdout` = List of strings (print statements)
- `execution.logs.stderr` = List of strings (errors/warnings)
- `execution.results` = List of Result objects (last expression)
- `result.text` = Text representation of a result

### Directory
According to E2B examples:
- All official examples use `/home/user` as the working directory
- This is the default home directory in E2B sandboxes
- E2B Desktop Sandbox also uses `/home/user`
