# Claude Chatbot POC

A proof-of-concept chatbot with Claude API integration, featuring multi-chat support, file uploads, extended thinking display, and intelligent context management.

## Features

✅ **Multi-Chat Support** - Manage multiple conversation threads
✅ **File Upload** - Support for PDFs, images, code files, and documents
✅ **Extended Thinking** - View Claude's reasoning process (collapsible)
✅ **Multi-File Code Execution** - Build complete projects with multiple Python files
✅ **Persistent Workspace** - Sandboxes persist across conversation, files remain available
✅ **Agentic Iteration** - Claude creates, edits, tests, and debugs code automatically
✅ **Project Structure** - Create proper modules, packages, and multi-file applications
✅ **Complete Audit Trail** - All thinking and tool executions logged to database
✅ **Execution Timeline** - View complete history of what Claude did with timestamps
✅ **Debug Mode** - Verify E2B calls and inspect execution events in database
✅ **Context Management** - Configurable token limit (default 20K)
✅ **Cost Tracking** - Real-time estimation of API costs
✅ **SQLite Storage** - Persistent chat history and metadata
✅ **Clean UI** - Streamlit-based interface with file tree display

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Streamlit UI (app.py)                │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │  Chat Area  │  │   Sidebar    │  │  File      │ │
│  │  Messages   │  │  Chat List   │  │  Upload    │ │
│  │  Thinking   │  │  File Tree   │  │  Manager   │ │
│  └─────────────┘  └──────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────┘
           │                     │                │
           ▼                     ▼                ▼
  ┌──────────────┐      ┌──────────────┐   ┌────────────┐
  │ ClaudeClient │      │   Database   │   │FileHandler │
  │  API Wrapper │      │   SQLite     │   │  Uploads   │
  └──────────────┘      └──────────────┘   └────────────┘
           │                                        
           ▼                                        
  ┌──────────────────────────────────────┐         
  │       CodeExecutor (E2B)             │         
  │  ┌────────────────────────────────┐  │         
  │  │  Persistent Sandbox per Chat   │  │         
  │  │  /project/                     │  │         
  │  │    ├── main.py                 │  │         
  │  │    ├── utils.py                │  │         
  │  │    └── ...                     │  │         
  │  └────────────────────────────────┘  │         
  └──────────────────────────────────────┘         
```

**Key Components:**
- **app.py**: Main Streamlit application, UI rendering, message handling
- **ClaudeClient**: Manages Claude API calls, tool use loop, thinking capture
- **CodeExecutor**: E2B sandbox management, file operations, code execution
- **Database**: SQLite with chat/message/file models, sandbox_id tracking
- **FileHandler**: Upload management, file conversion for Claude API

**Data Flow:**
1. User sends message → Saved to database
2. Build conversation history → Apply context limits
3. Call Claude with tools (create_file, read_file, list_files, execute_python)
4. Claude decides which tools to use → Agentic iteration
5. Display results + save responses → Update sandbox_id if changed
6. Conversation continues with persistent sandbox state

## Project Structure

```
claude-chatbot-poc/
├── app.py                 # Main Streamlit application
├── config.yaml            # Configuration (model, limits, tools)
├── requirements.txt       # Python dependencies
├── .env                   # API keys (not in repo)
├── README.md              # This file
│
├── src/
│   ├── __init__.py
│   ├── database.py        # SQLAlchemy models & CRUD
│   ├── claude_client.py   # Claude API wrapper with tools
│   ├── code_executor.py   # E2B sandbox management
│   ├── file_handler.py    # File upload & conversion
│   └── utils.py           # Token estimation, helpers
│
└── data/
    ├── chats.db           # SQLite database (created on first run)
    └── uploads/           # User-uploaded files (by chat_id)
        └── {chat_id}/
            └── files...
```

## Prerequisites

- Python 3.8+
- Anthropic API key
- E2B API key (for code execution - free tier available)

## Installation

1. **Clone or download this repository**

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Get API Keys:**

   **Anthropic API Key:**
   - Go to https://console.anthropic.com/
   - Create an account or sign in
   - Generate an API key

   **E2B API Key (for code execution):**
   - Go to https://e2b.dev/
   - Sign up for free account (100 executions/month free)
   - Get your API key from the dashboard

4. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env and add both API keys:
# ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
# E2B_API_KEY=e2b_your-actual-key-here
```

5. **Run the application:**
```bash
streamlit run app.py
```

## Configuration

All settings can be customized in `config.yaml`:

### Key Settings

```yaml
# Context limit (tokens to keep in conversation)
context:
  max_tokens: 20000

# Claude model and settings
claude:
  model: "claude-sonnet-4-20250514"
  extended_thinking: true

# File upload limits
files:
  max_size_mb: 50
  allowed_extensions: [pdf, txt, md, py, ...]

# Cost tracking
costs:
  input_cost_per_million: 3.00
  output_cost_per_million: 15.00
```

## Usage

### Starting a New Chat

1. Click **"➕ New Chat"** in the sidebar
2. Type your message in the chat input
3. View Claude's response with thinking process

### Uploading Files

1. Use the **"📎 Upload Files"** section on the right
2. Select files (PDFs, images, code, etc.)
3. Files are automatically included in context
4. Remove files with the 🗑️ button

### Managing Chats

- **Switch chats**: Click on any chat in the sidebar
- **Delete chat**: Click "🗑️ Delete Chat" button (also cleans up sandbox)
- **View costs**: See estimated costs below chat title
- **Project files**: Expand "📁 Project Files" in sidebar to see created files

### Viewing Multi-File Projects

When Claude creates files, you can:
1. See the file tree in the sidebar under "📁 Project Files"
2. View file creation/editing in expanders during the conversation
3. Files persist - Claude can import them in later messages
4. Each chat has its own isolated sandbox/workspace

### Verification & Debugging

**Database Logging:**
Every action is logged to SQLite database for complete audit trail:
- All thinking events with timestamps
- Every tool call (create_file, execute_python, etc.)
- Execution times in milliseconds
- Success/error status for each operation
- Sandbox IDs for tracking

**Debug Mode:**
Enable debug mode in sidebar (🐛 Debug Mode checkbox) to see:
- Current sandbox ID
- Recent tool calls with execution times
- Count of thinking events
- Real-time verification of E2B calls

**Execution Timeline:**
After each response, expand "📊 Execution Timeline" to see:
- Complete chronological log of all events
- Thinking blocks by iteration
- Tool calls with success/error status
- Execution times for each operation
- Timestamps for everything

**Terminal Verification:**
Check your terminal/console to see real-time logging:
```
[DB] Logged thinking event #1 for chat abc123, iteration 0
[E2B] Creating /project/main.py
[DB] Logged tool_call #1: create_file (iteration 0)
[E2B] Created file: /project/main.py in 45.2ms
[DB] Updated tool_call #1: status=success
```

**Direct Database Queries:**
You can query the SQLite database directly:
```bash
sqlite3 data/chats.db

-- See all E2B tool calls
SELECT * FROM tool_calls WHERE tool_name IN ('create_file', 'execute_python');

-- Check success rate
SELECT 
    tool_name, 
    COUNT(*) as total,
    SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as successes,
    ROUND(AVG(execution_time_ms), 2) as avg_time_ms
FROM tool_calls
GROUP BY tool_name;

-- View thinking events
SELECT COUNT(*) FROM thinking_events;
```

### Code Execution & Multi-File Projects

The POC includes **persistent sandboxes** for building complex multi-file applications:

**How it works:**
1. Each chat gets its own persistent E2B sandbox
2. Claude can create multiple files (utils.py, main.py, models.py, etc.)
3. Files persist across the conversation - imports work properly
4. Claude tests code, finds errors, edits specific files, and iterates
5. You see all file operations and execution results

**What Claude can do:**
- ✅ Create multi-file Python projects with proper structure
- ✅ Write modular code across multiple files
- ✅ Import from files created in the same conversation
- ✅ Edit specific files when debugging
- ✅ Run complete programs with dependencies
- ✅ Install packages with pip
- ✅ Build complex applications (web scrapers, APIs, data processors, etc.)

**Example workflow:**
```
You: "Build a web scraper with logging and error handling"

Claude creates:
📁 /project/
  ├── scraper.py      # Main scraping logic
  ├── logger.py       # Logging configuration  
  ├── utils.py        # Helper functions
  └── main.py         # Entry point

Then:
- Runs main.py to test
- Finds error in utils.py
- Edits only utils.py to fix
- Re-runs and verifies it works
```

**Example prompts:**
- "Build a CLI tool to analyze CSV files with proper error handling"
- "Create a REST API server with separate routes and models"
- "Build a data pipeline with extraction, transformation, and loading modules"
- "Write a web scraper that saves data to JSON and handles rate limiting"

**Tools Claude uses:**
- `create_file` - Create or overwrite files
- `read_file` - Read file contents
- `list_files` - See project structure
- `execute_python` - Run code or execute files

**Limitations:**
- No network access from sandbox (can't fetch URLs)
- 60 second timeout per execution
- Can't access local files outside /project directory
- Sandbox persists for session but may expire after hours of inactivity

### Context Management

The POC automatically manages context to stay within the 20K token limit:
- Keeps most recent messages
- Includes files marked as "in context"
- Shows warnings if approaching limit

## File Support

### Text Files
- `.txt`, `.md`, `.py`, `.js`, `.json`, `.csv`
- Sent as text to Claude

### PDFs
- `.pdf`
- Converted to base64 and sent as documents
- Claude extracts text automatically

### Images
- `.png`, `.jpg`, `.jpeg`, `.webp`
- Converted to base64
- ~750 tokens per image

## Cost Estimates

Based on Claude Sonnet 4.5 pricing:
- **Input**: $3.00 per million tokens
- **Output**: $15.00 per million tokens

Typical costs:
- Simple message: ~$0.10
- Message with file: ~$0.15-0.30
- 100 messages: ~$10-15

## Project Structure

```
claude-chatbot-poc/
├── app.py                  # Main Streamlit application
├── config.yaml             # Configuration settings
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create from .env.example)
├── src/
│   ├── database.py        # SQLAlchemy models & operations
│   ├── claude_client.py   # Claude API wrapper
│   ├── file_handler.py    # File processing
│   └── utils.py           # Helper functions
└── data/
    ├── chats.db           # SQLite database (auto-created)
    └── uploads/           # Uploaded files
        └── chat_*/        # Per-chat file storage
```

## Database Schema

### Chats Table
- `id`, `title`, `created_at`, `last_updated`
- `message_count`, `total_tokens`

### Messages Table
- `id`, `chat_id`, `role`, `content` (JSON)
- `timestamp`, `token_count`

### Files Table
- `id`, `chat_id`, `filename`, `file_path`
- `file_type`, `size_bytes`, `in_context`
- `token_estimate`, `uploaded_at`

## Troubleshooting

### "ANTHROPIC_API_KEY not found"
- Ensure `.env` file exists with your API key
- Check the key is valid and active

### "E2B_API_KEY not found"
- Add your E2B API key to `.env` file
- Get a free key at https://e2b.dev/
- Code execution will be disabled without this key

### Code execution not working
- Verify E2B_API_KEY is set correctly in `.env`
- Check you haven't exceeded free tier quota (100/month)
- Try restarting the app

### Files not uploading
- Check file type is in `allowed_extensions` in config.yaml
- Verify file size is under `max_size_mb` limit

### "Context too large" errors
- Reduce `max_tokens` in config.yaml
- Remove some files from context
- Clear older messages (delete and recreate chat)

### Database errors
- Delete `data/chats.db` to reset (loses all data)
- Check file permissions in `data/` directory

## Limitations (POC)

⚠️ **This is a proof-of-concept. Known limitations:**

- No user authentication
- No conversation search
- No export functionality (but can copy code from file tree)
- Basic error handling
- No prompt caching (could reduce costs)
- E2B free tier: 100 sandbox hours/month
- Sandboxes may expire after hours of inactivity
- No file download from sandbox (view-only in UI)
- Project files lost if sandbox expires (shown in conversation history though)

## Future Enhancements

Potential improvements:
- File download from sandbox
- Persistent file storage beyond sandbox lifetime
- File editing UI
- Export chats + project files to ZIP
- Prompt caching for cost optimization
- Better file chunking for large documents
- Chat tagging and categorization
- Usage analytics dashboard
- Support for more languages (JavaScript, TypeScript, etc.)
- Terminal access to sandbox
- Git integration in sandbox

## License

MIT License - Feel free to modify and use as needed.

## Support

For issues or questions:
- Check the troubleshooting section
- Review Claude API documentation: https://docs.anthropic.com
- Verify your API key and quota
