# Bug Fix: E2B Sandbox ID Attribute

## Issue

Error when executing Python code:
```
[E2B] System error: Execution error: 'CodeInterpreter' object has no attribute 'sandbox_id'
```

## Root Cause

The E2B `CodeInterpreter` object uses `.id` to access the sandbox ID, not `.sandbox_id`.

**Incorrect:**
```python
sandbox.sandbox_id  # ❌ AttributeError
```

**Correct:**
```python
sandbox.id  # ✅ Works
```

## Files Fixed

**src/code_executor.py:**
- Replaced all occurrences of `sandbox.sandbox_id` with `sandbox.id`
- Added logging when sandbox is created: `print(f"[E2B] Created new sandbox: {sandbox.id}")`
- Added logging when reconnecting: `print(f"[E2B] Reconnected to sandbox: {sandbox_id}")`
- Added error logging when reconnection fails

**Total changes:** 15 occurrences fixed

## Verification

After fix, you should see in terminal:
```
[E2B] Created new sandbox: sandbox_abc123xyz
[E2B] Creating /project/test.py
[E2B] Created file: /project/test.py in 45.2ms
[DB] Updated tool_call #1: status=success
```

## Testing

```python
# Simple test
User: "Create a file called test.py with print('hello')"

# Expected terminal output:
[E2B] Created new sandbox: sandbox_xxxxx
[DB] Logged tool_call #1: create_file
[E2B] Created file: /project/test.py in 45ms
[DB] Updated tool_call #1: status=success

# ✅ Success!
```

## Additional Improvements

Added better logging throughout:
1. Sandbox creation logged with ID
2. Sandbox reconnection logged
3. Reconnection failures logged with reason
4. All tool operations show timing

This makes debugging much easier!
