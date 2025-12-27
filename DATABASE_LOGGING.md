# Database Logging Implementation

## Overview

Complete audit trail system for Claude's thinking process and E2B tool executions. Everything is logged to SQLite database with timestamps, execution times, and status tracking.

## Why Database Logging?

### Problems Solved
1. ✅ **Verification** - Prove E2B is actually being called
2. ✅ **Debugging** - See exactly what happened and when
3. ✅ **Transparency** - Complete audit trail of all operations
4. ✅ **Analysis** - Query execution patterns, success rates, timing
5. ✅ **Replay** - Reconstruct what happened in any conversation

### Advantages Over Other Approaches
- ✅ **Persistent** - Never lose execution history
- ✅ **Queryable** - SQL gives powerful analysis capabilities
- ✅ **Verifiable** - Can check database directly
- ✅ **Real-time** - Logged as events happen
- ✅ **Separation of concerns** - Display logic separate from execution

---

## Database Schema

### New Tables Added

#### 1. thinking_events
Tracks Claude's thinking process:

```sql
CREATE TABLE thinking_events (
    id              INTEGER PRIMARY KEY,
    chat_id         TEXT NOT NULL,
    message_id      TEXT,           -- Links to specific message
    timestamp       DATETIME,
    thinking_text   TEXT NOT NULL,
    signature       TEXT,           -- For continuity
    iteration       INTEGER,        -- Which loop iteration
    FOREIGN KEY (chat_id) REFERENCES chats(id)
);
```

**Example Row:**
```
id: 1
chat_id: "abc-123"
message_id: "msg-456"
timestamp: 2025-12-27 14:30:15
thinking_text: "I'll create a web scraper with proper error handling..."
signature: "sig_abc123"
iteration: 0
```

#### 2. tool_calls
Tracks all tool executions (E2B operations):

```sql
CREATE TABLE tool_calls (
    id                  INTEGER PRIMARY KEY,
    chat_id             TEXT NOT NULL,
    message_id          TEXT,
    timestamp           DATETIME,
    iteration           INTEGER,
    
    tool_name           TEXT NOT NULL,  -- 'create_file', 'execute_python', etc.
    tool_input          JSON NOT NULL,  -- Complete input parameters
    
    status              TEXT DEFAULT 'pending',
    tool_output         JSON,
    error_msg           TEXT,
    
    sandbox_id          TEXT,
    execution_time_ms   INTEGER,
    
    FOREIGN KEY (chat_id) REFERENCES chats(id)
);
```

**Example Rows:**

Create File:
```
id: 1
tool_name: "create_file"
tool_input: {"path": "/project/scraper.py", "content": "import requests..."}
status: "success"
tool_output: {"success": true, "path": "/project/scraper.py"}
execution_time_ms: 45.2
```

Execute Python:
```
id: 2
tool_name: "execute_python"
tool_input: {"file_path": "/project/scraper.py"}
status: "error"
error_msg: "ModuleNotFoundError: No module named 'requests'"
execution_time_ms: 123.5
```

---

## Implementation Details

### 1. Database Methods (database.py)

**Logging Methods:**
```python
# Log thinking event
event_id = db.log_thinking(
    chat_id="abc-123",
    thinking_text="Planning the solution...",
    signature="sig_xyz",
    message_id="msg-456",
    iteration=0
)

# Log tool call start
tool_id = db.log_tool_call(
    chat_id="abc-123",
    tool_name="create_file",
    tool_input={"path": "/project/main.py", "content": "..."},
    message_id="msg-456",
    iteration=0
)

# Update tool call with result
db.update_tool_call(
    event_id=tool_id,
    status="success",
    tool_output={"success": True},
    sandbox_id="sandbox_123",
    execution_time_ms=45.2
)
```

**Query Methods:**
```python
# Get all events for a message
events = db.get_execution_events(
    chat_id="abc-123",
    message_id="msg-456"
)

# Get all tool calls with status
successful_calls = db.get_tool_calls(
    chat_id="abc-123",
    status="success"
)

# Get thinking events
thinking = db.get_thinking_events(
    chat_id="abc-123",
    message_id="msg-456"
)
```

---

### 2. CodeExecutor Integration (code_executor.py)

Every tool method now logs to database:

```python
def create_file(self, chat_id, sandbox_id, path, content, 
               message_id=None, iteration=0):
    # Log START
    event_id = self.db.log_tool_call(
        chat_id=chat_id,
        tool_name='create_file',
        tool_input={'path': path, 'content': content},
        message_id=message_id,
        iteration=iteration
    )
    
    start_time = time.time()
    
    try:
        # Execute
        sandbox.filesystem.write(path, content)
        execution_time = (time.time() - start_time) * 1000
        
        # Log SUCCESS
        self.db.update_tool_call(
            event_id=event_id,
            status='success',
            tool_output={'success': True, 'path': path},
            sandbox_id=sandbox.sandbox_id,
            execution_time_ms=execution_time
        )
        
        print(f"[E2B] Created file: {path} in {execution_time:.1f}ms")
        
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        
        # Log ERROR
        self.db.update_tool_call(
            event_id=event_id,
            status='error',
            error_msg=str(e),
            execution_time_ms=execution_time
        )
```

**All tool methods updated:**
- `create_file()` ✅
- `read_file()` ✅
- `list_files()` ✅
- `execute_python()` ✅

---

### 3. ClaudeClient Integration (claude_client.py)

Logs thinking events:

```python
def send_message(self, messages, chat_id=None, message_id=None, ...):
    while iteration < max_iterations:
        response = self.client.messages.create(...)
        
        # Log thinking events
        if self.db and chat_id:
            for block in response.content:
                if block.get('type') == 'thinking':
                    self.db.log_thinking(
                        chat_id=chat_id,
                        thinking_text=block.get('thinking', ''),
                        signature=block.get('signature'),
                        message_id=message_id,
                        iteration=iteration
                    )
```

---

### 4. App.py Integration

**Pass message_id through chain:**
```python
# Save user message and get ID
user_message = db.add_message(...)
message_id = user_message.id

# Pass to Claude API
response = claude_client.send_message(
    messages,
    chat_id=chat_id,
    message_id=message_id,
    ...
)

# Tool executor captures message_id in closure
def tool_exec(tool_name, tool_input):
    iteration_counter[0] += 1
    return code_executor.create_file(
        ...,
        message_id=message_id,
        iteration=iteration_counter[0]
    )
```

**Display execution timeline:**
```python
# Get all events from database
events = db.get_execution_events(chat_id, message_id)

# Display in expander
with st.expander("📊 Execution Timeline"):
    for event in events:
        if event['type'] == 'thinking':
            st.write(f"🤔 Thinking (Iteration {event['iteration']})")
            st.caption(event['timestamp'])
        elif event['type'] == 'tool_call':
            icon = "✅" if event['status'] == 'success' else "❌"
            st.write(f"{icon} {event['tool_name']} ({event['execution_time_ms']:.1f}ms)")
```

---

## Verification Methods

### 1. Terminal Logging

Every operation prints to console:
```
[DB] Logged tool_call #1: create_file (iteration 0)
[E2B] Created file: /project/main.py in 45.2ms
[DB] Updated tool_call #1: status=success
[DB] Logged thinking event #1 for chat abc123, iteration 0
```

### 2. Debug Mode (UI)

Enable in sidebar:
- Shows sandbox ID
- Lists recent tool calls
- Shows execution times
- Counts thinking events

### 3. Execution Timeline (UI)

Collapsible timeline showing:
- All thinking blocks
- All tool calls
- Timestamps
- Execution times
- Success/error status

### 4. Direct Database Queries

```sql
-- Total tool calls
SELECT COUNT(*) FROM tool_calls;

-- Success rate by tool
SELECT 
    tool_name,
    COUNT(*) as total,
    SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as successes,
    ROUND(100.0 * SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM tool_calls
GROUP BY tool_name;

-- Average execution time
SELECT 
    tool_name,
    ROUND(AVG(execution_time_ms), 2) as avg_ms,
    MIN(execution_time_ms) as min_ms,
    MAX(execution_time_ms) as max_ms
FROM tool_calls
WHERE status = 'success'
GROUP BY tool_name;

-- Recent failures
SELECT 
    tool_name,
    error_msg,
    timestamp
FROM tool_calls
WHERE status = 'error'
ORDER BY timestamp DESC
LIMIT 10;

-- Thinking vs tool usage
SELECT 
    (SELECT COUNT(*) FROM thinking_events) as thinking_count,
    (SELECT COUNT(*) FROM tool_calls) as tool_count;
```

---

## Example Output

### Terminal Output:
```
[APP] User message saved with ID: msg-789
[DB] Logged thinking event #1 for chat abc123, iteration 0
[DB] Logged tool_call #1: create_file (iteration 0)
[E2B] Creating /project/scraper.py
[E2B] Created file: /project/scraper.py in 45.2ms
[DB] Updated tool_call #1: status=success
[DB] Logged tool_call #2: execute_python (iteration 0)
[E2B] Error executing /project/scraper.py: ModuleNotFoundError
[DB] Updated tool_call #2: status=error
[DB] Logged tool_call #3: execute_python (iteration 1)
[E2B] Executed /project/scraper.py successfully in 234.5ms
[DB] Updated tool_call #3: status=success
```

### UI Timeline Display:
```
📊 Execution Timeline

🤔 Thinking (Iteration 0)
14:30:15

✅ 📝 create_file (Iteration 0) (45.2ms)
14:30:15

❌ ▶️ execute_python (Iteration 0) (123.5ms)
14:30:16
Error: ModuleNotFoundError: No module named 'requests'

✅ ▶️ execute_python (Iteration 1) (234.5ms)
14:30:18

────────────────────
Total events: 4
```

---

## Benefits Demonstrated

### 1. Complete Audit Trail
Every single operation is recorded with:
- Exact timestamp
- Execution time
- Success/failure status
- Full input parameters
- Complete error messages

### 2. Verifiable E2B Usage
Can prove E2B is being called by:
- Checking terminal logs
- Viewing debug panel
- Querying database directly
- Checking E2B dashboard (with delay)

### 3. Debugging Power
When something goes wrong:
- See exact sequence of events
- Identify which operation failed
- Check error messages
- Analyze timing patterns

### 4. Performance Analysis
```sql
-- Which operations are slowest?
SELECT tool_name, AVG(execution_time_ms) as avg_time
FROM tool_calls
WHERE status = 'success'
GROUP BY tool_name
ORDER BY avg_time DESC;

-- How many iterations typically needed?
SELECT MAX(iteration) + 1 as total_iterations, COUNT(*) as frequency
FROM (
    SELECT message_id, MAX(iteration) as iteration
    FROM tool_calls
    GROUP BY message_id
)
GROUP BY iteration
ORDER BY frequency DESC;
```

### 5. Usage Patterns
```sql
-- Most used tools
SELECT tool_name, COUNT(*) as usage_count
FROM tool_calls
GROUP BY tool_name
ORDER BY usage_count DESC;

-- When do we use thinking?
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as thinking_events
FROM thinking_events
GROUP BY date;
```

---

## Testing & Verification

### Immediate Verification (Before running app):

```bash
# Check database schema
sqlite3 data/chats.db ".schema thinking_events"
sqlite3 data/chats.db ".schema tool_calls"
```

### During Execution:

1. **Watch terminal** - See real-time logging
2. **Enable debug mode** - Check sidebar stats
3. **Expand timeline** - See all events
4. **Query database** - Direct verification

### Example Test Sequence:

```
1. User: "Create a file called test.py with print('hello')"
   
2. Check terminal:
   [DB] Logged tool_call #1: create_file
   [E2B] Created file: /project/test.py in 45.2ms
   [DB] Updated tool_call #1: status=success

3. Check timeline:
   ✅ 📝 create_file (45.2ms)

4. Query database:
   SELECT * FROM tool_calls WHERE tool_name='create_file';
   
5. ✅ VERIFIED: E2B was called!
```

---

## Conclusion

This implementation provides:
- ✅ Complete transparency
- ✅ Verifiable E2B usage
- ✅ Powerful debugging
- ✅ Performance analysis
- ✅ Audit trail
- ✅ Multiple verification methods

**No more uncertainty** - you can see exactly what happened, when it happened, and whether it succeeded!
