# Change Log

## v0.5.0 - Batch Evaluation (2025-11-13)

### 🎉 Major Features

#### Batch Evaluation System
- **Module**: `src/evaluator/batch_evaluator.py`
- **Command**: `python main.py batch-evaluate`
- **Features**:
  - Multiple task input methods (task-ids, file, split)
  - Sequential and parallel execution
  - JSON and CSV output formats
  - Comprehensive summary statistics
  - Automatic port management
  - Graceful interrupt handling

#### Result Collection & Reporting
- Per-task metrics: success, steps, time, score, passes/fails
- Summary statistics: success rate, averages, timestamp
- Multiple export formats (JSON, CSV)
- Formatted console output with tables

#### Documentation
- `BATCH_EVALUATION.md`: Comprehensive user guide
- `QUICKSTART_BATCH.md`: Quick start guide
- `BATCH_IMPLEMENTATION.md`: Implementation details
- Updated main `README.md` with batch features

### 📝 Changes
- Added `src/evaluator/` module
- Updated `main.py` with `batch-evaluate` command
- Enhanced CLI with extensive options
- Added example `test_tasks.txt`

---

## v0.4.2 - Field Type Clarification (2025-11-13)

### 🐛 Fixes
- Added explicit system prompt clarification for "most-liked" vs "liked" fields
- Differentiated numeric `like_count` from boolean `liked` field
- Provided clear examples of wrong vs correct approaches

### 📝 Changes
- Updated `src/white_agent/agent.py` system prompt
- Added `FIELD_TYPE_CLARIFICATION_v0.4.2.md` documentation

---

## v0.4.1 - Improved Conversation Compression (2025-11-13)

### ✨ Enhancements
- Implemented three-layer retention strategy for conversation history
- Always retain system prompt and initial task message
- Intelligently summarize middle conversation with key reminders
- Keep recent 12 messages (6 rounds) for current context
- Increased `MAX_MESSAGES` to 20

### 📝 Changes
- Modified `src/white_agent/agent.py` compression logic
- Added `IMPROVED_COMPRESSION_v0.4.1.md` documentation

---

## v0.4.0 - Conversation History Compression (2025-11-13)

### ✨ Enhancements
- Implemented conversation history compression to manage token limits
- Added basic message summarization
- Set `MAX_MESSAGES` threshold of 12
- Retained system prompt and recent messages

### 📝 Changes
- Modified `src/white_agent/agent.py`
- Added `CONVERSATION_COMPRESSION_v0.4.0.md` documentation
- Added `num_retries=3` to litellm.completion for rate limit handling

---

## v0.3.3 - Data Analysis Guidance (2025-11-13)

### ✨ Enhancements
- Added general data analysis guidance to white agent system prompt
- Instructions for finding "most/highest/best" items
- Emphasis on gathering ALL items and comparing numeric metrics

### 📝 Changes
- Updated `src/white_agent/agent.py` system prompt
- Added `DATA_ANALYSIS_GUIDANCE_v0.3.3.md` documentation

---

## v0.3.2 - Concise Answer Format (2025-11-13)

### 🐛 Fixes
- Updated white agent to provide concise, direct answers
- Added explicit examples of good vs bad answer formats
- Prevents verbose answers that fail AppWorld evaluation

### 📝 Changes
- Modified `src/white_agent/agent.py` system prompt
- Added `CONCISE_ANSWER_FIX_v0.3.2.md` documentation

---

## v0.3.1 - Answer Submission & Timeout Fix (2025-11-13)

### 🐛 Fixes
- Fixed `apis.supervisor.complete_task()` to include `answer` parameter
- Increased A2A client timeout from 30s to 300s to prevent ReadTimeout errors
- Proper answer submission for question-style tasks

### 📝 Changes
- Modified `src/green_agent/agent.py` to pass `answer` to `complete_task`
- Updated `src/util/a2a_client.py` timeout configuration
- Added `ANSWER_SUBMISSION_FIX_v0.3.1.md` documentation

---

## v0.3.0 - Prompt Engineering & Error Handling (2025-11-13)

### ✨ Enhancements
- Added comprehensive system prompt for white agent
- Improved initial message from green agent
- Added retry mechanism for JSON format errors
- Enhanced guidance on credential retrieval and API usage

### 📝 Changes
- Modified `src/white_agent/agent.py` with system prompt
- Updated `src/green_agent/agent.py` initial message
- Added `PROMPT_ENGINEERING_v0.3.0.md` documentation

---

## v0.2.2 - Critical API Result Capture Fix (2025-11-13)

### 🐛 Fixes
- Fixed `world.execute()` to capture actual API return values
- Added explicit `print()` statements for API results
- Prevents "Execution successful." placeholder returns

### 📝 Changes
- Modified `src/green_agent/agent.py` code generation for API calls
- Updated both regular API calls and answer submission
- Added `CRITICAL_FIX_v0.2.2.md` documentation

---

## v0.2.1 - Meta-API Spec Fix (2025-11-13)

### 🐛 Fixes
- Fixed `get_meta_api_specs()` parameter definitions
- Corrected `app_name` as required parameter for `show_api_descriptions` and `show_api_doc`
- Fixed return type examples to use valid JSON

### 📝 Changes
- Modified `src/green_agent/agent.py`
- Added `UPDATES_v0.2.1.md` documentation

---

## v0.2.0 - Progressive API Discovery (2025-11-13)

### ✨ Enhancements
- Implemented progressive API discovery mechanism
- Provided meta-APIs: `show_app_descriptions`, `show_api_descriptions`, `show_api_doc`
- White agent discovers APIs dynamically instead of receiving all docs upfront
- Follows AgentBeats Tool Delivery Approach II

### 📝 Changes
- Major refactor of `src/green_agent/agent.py`
- Added `get_meta_api_specs()` function
- Updated communication protocol
- Enhanced initial message format

---

## v0.1.0 - Initial Implementation (2025-11-12)

### 🎉 Initial Features
- Green agent implementation with AppWorld integration
- White agent implementation with OpenAI/LiteLLM
- A2A client utilities
- Basic launcher for single task evaluation
- CLI commands: `green`, `white`, `launch`, `list-tasks`

### 📝 Components
- `src/green_agent/`: Assessment manager
- `src/white_agent/`: Target agent
- `src/util/`: A2A communication utilities
- `src/launcher.py`: Evaluation coordinator
- `main.py`: CLI entry point

### 🐛 Known Issues
- Evaluation result parsing incomplete
- No system prompt for white agent
- Missing conversation history management
- No batch evaluation support


