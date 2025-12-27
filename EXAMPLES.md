# Multi-File Code Execution Examples

## Example 1: Web Scraper with Logging

**User:** Build a web scraper that extracts product data with proper logging and error handling

**Claude's workflow:**

### Step 1: Create project structure
```
📝 Created file: /project/logger.py
📝 Created file: /project/scraper.py
📝 Created file: /project/utils.py
📝 Created file: /project/main.py
```

### Step 2: Test the code
```
▶️ Executed: main.py
❌ Error: ModuleNotFoundError: No module named 'requests'
```

### Step 3: Fix dependencies
```
▶️ Executed code (Iteration 2)
!pip install requests beautifulsoup4
✅ Success
```

### Step 4: Re-test
```
▶️ Executed: main.py
✅ Success
Initialized logger
Scraping https://example.com...
Found 15 products
Saved to products.json
```

**Result:** Working multi-file web scraper with:
- `logger.py` - Logging configuration
- `scraper.py` - Scraping logic with error handling
- `utils.py` - Helper functions for parsing
- `main.py` - Entry point

---

## Example 2: REST API Server

**User:** Create a simple REST API with separate routes and models

**Claude's workflow:**

### Files created:
```
📁 /project/
  ├── models.py      # Data models
  ├── routes.py      # API endpoints
  ├── database.py    # Database connection
  └── server.py      # Flask app
```

### Execution:
```
▶️ Executed: server.py
✅ Success
* Running on http://127.0.0.1:5000
* Routes:
  - GET  /users
  - POST /users
  - GET  /users/<id>
```

**Result:** Working Flask API with proper separation of concerns

---

## Example 3: Data Processing Pipeline

**User:** Build an ETL pipeline for processing CSV data

**Claude's workflow:**

### Files created:
```
📁 /project/
  ├── extract.py     # Data extraction
  ├── transform.py   # Data transformation
  ├── load.py        # Data loading
  ├── config.py      # Configuration
  └── pipeline.py    # Main pipeline orchestrator
```

### Execution flow:
```
▶️ Executed: pipeline.py

📖 Read file: extract.py
[Claude verifies extraction logic]

📖 Read file: transform.py
[Claude finds bug in data cleaning]

📝 Created file: /project/transform.py
[Claude fixes the bug]

▶️ Executed: pipeline.py
✅ Success
Extracted 1000 rows
Transformed 1000 rows
Loaded to database
Pipeline completed in 2.3s
```

---

## Example 4: CLI Tool with Tests

**User:** Create a CLI tool to analyze JSON files with proper error handling and tests

**Claude's workflow:**

### Files created:
```
📁 /project/
  ├── analyzer.py         # Core analysis logic
  ├── cli.py              # Command-line interface
  ├── validators.py       # Input validation
  ├── test_analyzer.py    # Unit tests
  └── README.md           # Usage documentation
```

### Test and iterate:
```
▶️ Executed: test_analyzer.py
❌ Error in test_validate_json_schema

📝 Created file: /project/validators.py
[Fixed validation logic]

▶️ Executed: test_analyzer.py
✅ All 8 tests passed
```

---

## Example 5: Machine Learning Experiment

**User:** Build a simple ML model to classify data with train/test split

**Claude's workflow:**

### Files created:
```
📁 /project/
  ├── data_loader.py      # Data loading utilities
  ├── preprocessor.py     # Feature engineering
  ├── model.py            # Model definition
  ├── trainer.py          # Training loop
  ├── evaluator.py        # Metrics calculation
  └── experiment.py       # Main experiment runner
```

### Execution:
```
▶️ Executed code
!pip install scikit-learn pandas numpy
✅ Installed dependencies

▶️ Executed: experiment.py
✅ Success
Loading data...
Preprocessing...
Training model...
Epoch 1/10: loss=0.234
Epoch 10/10: loss=0.045
Evaluation:
  Accuracy: 0.94
  F1-Score: 0.92
```

---

## Key Advantages

### 1. **Proper Code Organization**
- Modular design with separation of concerns
- Easy to understand and maintain
- Follows Python best practices

### 2. **Iterative Development**
- Claude creates initial structure
- Tests and finds errors
- Edits only the problematic files
- Continues until working

### 3. **Real Imports Work**
```python
# In main.py, this actually works:
from scraper import WebScraper
from logger import setup_logging
from utils import parse_html

# Files persist across the conversation!
```

### 4. **Complex Project Patterns**
- MVC architecture
- Factory patterns  
- Dependency injection
- Package structures with `__init__.py`

### 5. **Full Development Workflow**
```
Create → Test → Debug → Fix → Re-test → Success
```

All within a single conversation!

---

## Comparison with Single-File Approach

### Old Approach (Single File)
```python
# Everything in one massive block
def scrape():
    ...
    
def log():
    ...
    
def parse():
    ...
    
def save():
    ...

# Run everything
scrape()
```

**Issues:**
- ❌ Hard to debug specific parts
- ❌ Can't reuse components
- ❌ Poor organization
- ❌ Doesn't scale

### New Approach (Multi-File)
```
📁 /project/
  ├── scraper.py
  ├── logger.py
  ├── parser.py
  └── main.py
```

**Benefits:**
- ✅ Clear separation of concerns
- ✅ Easy to test individual modules
- ✅ Professional code structure
- ✅ Scales to complex projects
- ✅ Can edit specific files when debugging

---

## Usage Tips

1. **Be specific about structure:**
   ```
   "Build a web scraper with separate files for scraping, logging, and utilities"
   ```

2. **Let Claude organize:**
   ```
   "Create a proper Python package structure for this project"
   ```

3. **Request tests:**
   ```
   "Build this with unit tests in a separate file"
   ```

4. **Iterate naturally:**
   ```
   "The parser is failing, can you fix the parser.py file?"
   ```

5. **View project state:**
   - Check sidebar "📁 Project Files" to see all files
   - Files persist for the entire conversation
   - Each chat has isolated workspace

---

## What Makes This Special

This POC demonstrates **true agentic coding** that matches Claude.ai's capabilities:

✅ Multi-file project creation
✅ Proper code organization
✅ Iterative debugging (edit specific files)
✅ Professional development patterns
✅ Complex application architectures

Most POCs only handle single-file execution. This one handles **real software engineering workflows**.
