# Debugging Output Issues

## Problem
Claude responds with "I apologize for the technical difficulties. The sandbox appears to have an issue with returning output" even though logs show successful execution.

## Root Cause
The output from E2B is not being properly formatted or sent to Claude API.

## Fixes Applied

### 1. Enhanced Logging in `code_executor.py`

**Added output inspection:**
```python
# For direct code execution
if execution.text:
    print(f"[E2B] execution.text: {execution.text[:100]}")

if execution.results:
    print(f"[E2B] execution.results: {execution.results}")

print(f"[E2B] Final output ({len(output)} chars): {output[:200]}")
```

**Added file execution logging:**
```python
if result.stdout:
    print(f"[E2B] File stdout: {result.stdout[:100]}")

print(f"[E2B] File execution output ({len(output)} chars): {output[:200]}")
```

### 2. Better Output Messages

**Changed from:**
```python
output = "(no output)"  # Ambiguous
```

**To:**
```python
output = "Code executed successfully with no printed output."  # Clear
```

### 3. Debug Logging in `claude_client.py`

**Added before sending to Claude:**
```python
print(f"[CLAUDE] Tool {tool_name} returned: success={result.get('success')}, output_len={len(str(result.get('output', '')))}")
print(f"[CLAUDE] Sending to Claude: {result_content[:100]}")
```

### 4. Fixed Duplicate Code

Removed duplicate formatting logic that was causing issues.

### 5. Increased Sandbox Timeout

**Changed from:**
```yaml
timeout_seconds: 60  # 1 minute
```

**To:**
```yaml
timeout_seconds: 3600  # 1 hour
```

This prevents sandbox expiration during long conversations.

---

## How to Debug Output Issues

### Step 1: Check Terminal Logs

When you run code, you should see:

```
[DB] Logged tool_call #X: execute_python (iteration 0)
[E2B] execution.text: print('hello') output here
[E2B] Final output (13 chars): hello world
[CLAUDE] Tool execute_python returned: success=True, output_len=13
[CLAUDE] Sending to Claude: hello world
[DB] Updated tool_call #X: status=success
```

### Step 2: Identify the Problem

**Case 1: No E2B output logs**
```
[DB] Logged tool_call #X: execute_python
[CLAUDE] Tool execute_python returned: success=True, output_len=0
[CLAUDE] Sending to Claude: Code executed successfully with no output.
```

**Problem:** E2B didn't capture any output
**Possible causes:**
- Code doesn't produce output (no print statements)
- Code has errors but they're being suppressed
- E2B sandbox issue

**Case 2: E2B has output but Claude doesn't receive it**
```
[E2B] Final output (50 chars): some important output
[CLAUDE] Tool execute_python returned: success=True, output_len=0
[CLAUDE] Sending to Claude: Code executed successfully with no output.
```

**Problem:** Output lost between E2B and Claude
**Possible causes:**
- Result dict structure wrong
- Output being overwritten
- Formatting issue

**Case 3: Output sent but Claude still complains**
```
[E2B] Final output (50 chars): some important output
[CLAUDE] Sending to Claude: some important output
```

**Problem:** Claude API issue or tool_result format issue
**Check:**
- Is output being sent as string or JSON?
- Is tool_use_id matching?
- Is content properly formatted?

### Step 3: Query Database

```bash
sqlite3 data/chats.db

-- Check recent tool calls
SELECT 
    id,
    tool_name,
    status,
    json_extract(tool_output, '$.output_length') as output_len,
    error_msg,
    execution_time_ms
FROM tool_calls
ORDER BY timestamp DESC
LIMIT 10;

-- Check specific tool call
SELECT 
    tool_input,
    tool_output,
    error_msg
FROM tool_calls
WHERE id = X;
```

### Step 4: Check E2B Output Format

The E2B `exec_cell` returns:
- `execution.text` - Print statements and stdout
- `execution.results` - Expression values (last line if not None)
- `execution.error` - Any errors

Example:
```python
# Code: print("hello"); 1+1
execution.text = "hello\n"
execution.results = [2]
# Final output = "hello\n2"
```

### Step 5: Manual Test

Create a simple test to verify:

```python
# In Python console
from src.code_executor import CodeExecutor
from src.database import Database

db = Database("data/chats.db")
executor = CodeExecutor(db=db)

# Test
result = executor.execute_python(
    chat_id="test",
    sandbox_id=None,
    code="print('hello world'); 1+1",
    message_id="test",
    iteration=0
)

print("Result:", result)
# Should show: {'success': True, 'output': 'hello world\n2', ...}
```

---

## Expected Terminal Output (Working)

```
[APP] User message saved with ID: msg-123
[DB] Logged thinking event #1
[DB] Logged tool_call #1: execute_python (iteration 0)

[E2B] execution.text: Hello, World!

[E2B] execution.results: [42]
[E2B] Final output (22 chars): Hello, World!
42
[E2B] Code executed successfully in 234.5ms

[CLAUDE] Tool execute_python returned: success=True, output_len=22
[CLAUDE] Sending to Claude: Hello, World!
42

[DB] Updated tool_call #1: status=success
```

---

## Common Issues & Solutions

### Issue 1: "(no output)" Confusion

**Before:**
```python
output = "(no output)"  # Claude thinks there's an error
```

**After:**
```python
output = "Code executed successfully with no printed output."
```

### Issue 2: Empty Output

**Cause:** Code doesn't print anything
```python
# This produces no output
x = 1 + 1
```

**Solution:** Ensure code has print or returns value
```python
# This produces output
x = 1 + 1
print(x)  # or just: 1+1
```

### Issue 3: Sandbox Expired

**Logs show:**
```
Sandbox ip926cefpt8l0n8fx6gz3 failed because it cannot be found
```

**Solution:** Increased timeout to 3600 seconds (1 hour)

### Issue 4: Network Errors

**Logs show:**
```
WebSocket received error while receiving messages
```

**Solution:** This is cosmetic from background thread, doesn't affect execution

---

## Verification Checklist

After fix, verify:
- [ ] Terminal shows E2B output logs
- [ ] Terminal shows Claude receiving output
- [ ] Database shows output_length > 0
- [ ] Claude responds with actual content (not error message)
- [ ] Execution timeline shows output in UI
- [ ] No sandbox expiration errors

---

## If Issues Persist

1. **Enable full debug mode:**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Check E2B API status:**
   - Visit https://e2b.dev/status
   - Check if sandboxes are available

3. **Test with simple code:**
   ```python
   User: "Run this: print('test')"
   ```
   
   Should see in logs:
   ```
   [E2B] execution.text: test
   ```

4. **Check API key permissions:**
   - Ensure E2B_API_KEY is valid
   - Check quota hasn't expired

5. **Report issue:**
   - Copy terminal logs
   - Copy database query results
   - Include test case that fails
