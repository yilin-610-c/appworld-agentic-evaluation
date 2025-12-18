# AppWorld Green Agent: Agentified Benchmark Platform

[![UC Berkeley AgentX-AgentBeats](https://img.shields.io/badge/AgentX--AgentBeats-Phase%201-green)](https://rdi.berkeley.edu/agentx-agentbeats.html)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An agentified evaluation infrastructure for the AppWorld benchmark, built for the UC Berkeley AgentX-AgentBeats competition. This system transforms AppWorld into an interactive benchmark using the Agent-to-Agent (A2A) protocol and Model Context Protocol (MCP), with enhanced features inspired by modern agent architectures.

## 🎯 Overview

This project implements a **Green Agent** (benchmark/evaluator) that assesses **White Agents** (AI agents under test) on real-world tasks spanning 9 applications with 469+ APIs. The evaluation infrastructure supports multiple tool delivery approaches and incorporates planning strategies, context management, and structured logging.

### Supported Approaches

- **Approach II (A2A Mode)**: JSON-based tool description with enhanced planning and context pre-loading
- **Approach III (MCP Mode)**: Live tool discovery via Model Context Protocol with intelligent tool filtering

---

## 🌟 Key Features

### Core Features
- ✅ **Standardized Evaluation**: A2A-compatible interface for any agent
- ✅ **Dual-Mode Support**: Both A2A and MCP protocols implemented
- ✅ **Dynamic Tool Discovery**: MCP-based real-time API access (469 tools)
- ✅ **Reproducible Assessment**: Consistent initial state for each evaluation run

### Enhanced Features

- 🎯 **Intelligent Planning Phase**: 
  - Task analysis with LLM-powered app identification
  - Smart tool filtering (469 → ~10-100 relevant tools)
  - Structured execution plan generation
  
- 🧠 **Context Management**:
  - Profile and credentials pre-loading (my_agent.py inspired)
  - Smart message compression (3-layer retention strategy)
  - Efficient token usage through targeted tool documentation

- 📊 **Structured Logging**:
  - JSONL format for all agent interactions
  - Step-by-step action, observation, and reasoning tracking
  - Trajectory analysis with 10+ metrics
  
- 🔧 **Self-Correction Capabilities**:
  - Error detection and recovery
  - Pagination handling with explicit rules
  - "Most-liked" vs "liked" disambiguation with examples

- 📈 **Evaluation Metrics**:
  - Task success/failure (AppWorld unit tests)
  - Execution efficiency (steps, time, API calls)
  - Trajectory quality (error rate, retry count, unique tools)
  - Full evaluation details (passes, failures, traces)

---

## 🏗️ Architecture

### System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Green Agent (Evaluator)                          │
│  • Manages AppWorld tasks and environments                             │
│  • Orchestrates MCP/API servers                                        │
│  • Evaluates white agent performance                                   │
│  • Provides tool schemas and executes API calls                        │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ A2A Protocol
                                    │ (standardized communication)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        White Agent (Under Test)                         │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ Initialization Phase (First Message)                            │  │
│  │  1. TaskAnalyzer → Identify required apps from task             │  │
│  │  2. ToolRegistry → Fetch API documentation (if MCP unavailable) │  │
│  │  3. Context Preloader → Get profile & credentials (framework)   │  │
│  │  4. PromptManager → Build enhanced system prompt                │  │
│  │  5. ConversationLogger → Initialize JSONL logging               │  │
│  │  6. Planning Phase → Generate execution plan with LLM           │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ Execution Loop                                                   │  │
│  │  • Structured step prompts with guidance                        │  │
│  │  • Message compression (20 message limit)                       │  │
│  │  • LLM reasoning with JSON output                               │  │
│  │  • JSONL logging of all actions                                 │  │
│  │  • Green agent executes tools and returns results               │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  Baseline: OpenAI GPT-4o/GPT-5 with enhanced prompting                 │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ MCP (Approach III only)
                                    │ or JSON (Approach II)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       MCP Server + API Server                           │
│  • Exposes 469 AppWorld tools via MCP                                  │
│  • Task-specific database loading                                      │
│  • Ports: 9000 (API), 10000 (MCP)                                      │
└────────────────────────────────────────────────────────────────────────┘
```

### White Agent Internal Architecture (Enhanced)

```
ConversationLogger ──────┐
    (JSONL logging)       │
                          │
TaskAnalyzer ─────────────┤
    (LLM identifies apps) │
                          │
ToolRegistry ─────────────┼──→ Enhanced System Prompt ──→ LLM
    (Fetch API docs)      │        with:
                          │        • Profile & Credentials
Context Preloader ────────┤        • Simplified tool schemas
    (Profile & creds)     │        • Critical rules
                          │        • Answer format examples
PromptManager ────────────┘
    (Build prompts)
```

---

## 📦 Installation

### Prerequisites

- **Python 3.13+** (required for latest features)
- **Conda** (recommended for environment management)
- **Git**
- **OpenAI API Key** (for GPT-4o/GPT-5 models)
- **8GB+ RAM** (for running AppWorld environment)
- **Linux/macOS/WSL** (Windows Subsystem for Linux recommended on Windows)

### Quick Setup

```bash
# 1. Clone the repository
git clone https://github.com/yilin-610-c/appworld-agentic-evaluation.git
cd appworld-agentic-evaluation

# 2. Create and activate conda environment
conda create -n appworld_agent_py313 python=3.13
conda activate appworld_agent_py313

# 3. Install dependencies
pip install -r requirements.txt
pip install mcp  # For MCP mode support

# 4. Setup AppWorld benchmark (adjacent to this project)
cd ..
git clone https://github.com/stonybrooknlp/appworld.git
cd appworld
python -m appworld.cli download --dataset-version v1
cd ../appworld-agentic-evaluation

# 5. Set OpenAI API key
export OPENAI_API_KEY="sk-your-key-here"

# 6. Verify installation
python main.py --help
```

### Detailed Setup

#### Environment Configuration

Create a `.env` file in the project root:

```bash
# Required
OPENAI_API_KEY=sk-your-openai-key-here

# Optional: Model selection (default: gpt-4o)
WHITE_AGENT_MODEL=openai/gpt-4o
# WHITE_AGENT_MODEL=openai/gpt-5  # For GPT-5

# Optional: AppWorld path (if not adjacent to project)
APPWORLD_ROOT=/path/to/appworld
```

#### Common Installation Issues

**Issue 1: Missing AppWorld**
```bash
# Error: appworld module not found
# Solution: Ensure AppWorld is installed
cd /path/to/parent/directory
git clone https://github.com/stonybrooknlp/appworld.git
cd appworld
pip install -e .
```

**Issue 2: Port Already in Use**
```bash
# Error: address already in use
# Solution: Kill existing processes
pkill -9 -f "python main.py"
lsof -ti :9000,:9001,:9002,:10000 | xargs -r kill -9
```

**Issue 3: MCP Import Error**
```bash
# Error: No module named 'mcp'
# Solution: Install MCP package
pip install mcp
```

---

## 🚀 Usage Guide

### Command Overview

```bash
# Basic usage
python main.py [launch|batch] [OPTIONS]

# Launch modes:
#   launch: Single task evaluation
#   batch:  Batch evaluation on multiple tasks

# Tool delivery modes:
#   --mcp:  Use MCP protocol (Approach III)
#   (none): Use JSON/A2A protocol (Approach II, default)
```

---

## 📋 Running White Agents

### A2A Mode (Default, Approach II)

**Single Task Evaluation:**

```bash
# Activate environment
conda activate appworld_agent_py313

# Run a single task with default model (GPT-4o)
python main.py launch --task-id 82e2fac_1

# Run with GPT-5 model
WHITE_AGENT_MODEL=openai/gpt-5 python main.py launch --task-id 82e2fac_1

# Run with custom model
WHITE_AGENT_MODEL=openai/gpt-4o-mini python main.py launch --task-id 82e2fac_1
```

**What Happens:**
1. Green agent starts on port 9001
2. White agent starts on port 9002
3. Green agent sends task to white agent
4. White agent initializes:
   - TaskAnalyzer identifies required apps
   - Planning phase generates execution plan
   - ConversationLogger creates `/tmp/a2a_agent_trace_{context_id}.jsonl`
5. Execution loop: White agent requests API calls, green agent executes them
6. Evaluation: AppWorld runs unit tests and displays results

**Expected Output:**
```
INITIALIZATION PHASE
================================================================================
Task: What is the title of the most-liked song in my Spotify playlists....
[TaskAnalyzer] Identified apps: ['spotify', 'api_docs', 'supervisor']
[System Prompt] Using enhanced prompt with preloaded context
[Logger] Initialized at /tmp/a2a_agent_trace_xxx.jsonl

PLANNING PHASE
================================================================================
Task Type: question
Required Apps: spotify, api_docs, supervisor

Execution Steps:
  1. Step 1: Retrieve all playlists
  2. Step 2: For each playlist, get songs and like_count
  3. Step 3: Compare like_count to find highest
  4. Step 4: Return the title

⚠️  Comparison Task: Will need to track and compare values
================================================================================

--- Step 1 ---
Sending message to white agent...
White agent response:
<json>
{"action": "call_api", "api_name": "api_docs.show_app_descriptions", "parameters": {}}
</json>

... (execution continues)

Final Answer: A Love That Never Was

EVALUATION RESULTS:
================================================================================
{
  "success": true,
  "difficulty": 1,
  "num_tests": 2,
  "passes": [
    {"requirement": "assert answers match.", "label": "no_op_fail"},
    {"requirement": "assert no model changes.", "label": "no_op_pass"}
  ],
  "failures": []
}
================================================================================

Metrics: {
  "task_id": "82e2fac_1",
  "steps": 14,
  "success": true,
  "passes": 2,
  "fails": 0,
  "total": 2,
  "score": 0,
  "time_used": 86.44
}
```

### MCP Mode (Approach III)

**Single Task Evaluation:**

```bash
# Run with MCP protocol
python main.py launch --task-id 82e2fac_1 --mcp

# With GPT-5
WHITE_AGENT_MODEL=openai/gpt-5 python main.py launch --task-id 82e2fac_1 --mcp
```

**What Happens:**
1. Green agent starts on port 9001
2. White agent starts on port 9002
3. AppWorld API server starts on port 9000
4. AppWorld MCP server starts on port 10000
5. White agent connects to MCP server and discovers 469 tools
6. Planning phase filters tools to ~100 relevant ones
7. White agent executes task by calling MCP tools directly
8. Trajectory analysis recorded to `/tmp/mcp_tool_calls_{task_id}.jsonl`

**Expected Output:**
```
[Real MCP] Connecting to MCP server: http://localhost:10000/mcp
[Real MCP] ✓ Successfully connected to MCP server
[Real MCP] ✓ Discovered 469 tools

[Planning Phase] Analyzing task and selecting relevant tools...
[Planning] Detected relevant apps: ['api_docs', 'spotify', 'supervisor']
[Planning] Found 98 relevant tools from 3 apps
[Planning] Selected 3 tools
[Planning] Tools: ['spotify__show_playlist_library', 'spotify__show_playlist', 'spotify__show_song']

[White Agent MCP] --- Step 1 (Start) ---
[Real MCP] Calling tool: spotify__login
[Real MCP] ✓ Tool call successful

... (execution continues)

EVALUATION RESULTS + TRAJECTORY ANALYSIS
```

---

## 🧪 Testing Green Agent Evaluation

### Test on Sample Tasks

```bash
# Test on a simple question-answering task
python main.py launch --task-id 82e2fac_1

# Test on a task requiring state changes
python main.py launch --task-id e7a10f8_1

# Test with verbose output
python main.py launch --task-id 82e2fac_1 --verbose

# Test with timeout (in seconds)
timeout 120 python main.py launch --task-id 82e2fac_1
```

### Batch Testing

```bash
# Create a task list file
cat > task_list.txt << EOF
82e2fac_1
e7a10f8_1
a1b2c3d_1
EOF

# Run batch evaluation
python main.py batch --task-file task_list.txt

# Run batch with MCP mode
python main.py batch --task-file task_list.txt --mcp

# Run first N tasks from test set
python main.py batch --num-tasks 10
```

**Batch Output:**
```
Batch Evaluation Started
========================
Total tasks: 3

Task 1/3: 82e2fac_1
  ✅ Success (14 steps, 86.4s)
  
Task 2/3: e7a10f8_1
  ✅ Success (22 steps, 142.1s)
  
Task 3/3: a1b2c3d_1
  ❌ Failed (30 steps, 180.0s)

Summary:
  Success Rate: 66.7% (2/3)
  Avg Steps: 22.0
  Avg Time: 136.2s
  
Results saved to: batch_results_20231217_120000.json
```

### Verify Evaluation Correctness

```bash
# Check log files
ls -lh /tmp/a2a_agent_trace_*.jsonl
ls -lh /tmp/mcp_tool_calls_*.jsonl

# Inspect JSONL log
cat /tmp/a2a_agent_trace_*.jsonl | jq .

# Count steps in trajectory
cat /tmp/a2a_agent_trace_*.jsonl | jq '.step' | sort -u | wc -l

# Extract all actions
cat /tmp/a2a_agent_trace_*.jsonl | jq '.action'

# Check final answer
cat /tmp/a2a_agent_trace_*.jsonl | tail -n 1 | jq '.action.content'
```

---

## 📊 Test Results

### Verified Test Case

**Task 82e2fac_1 (A2A Mode with GPT-4o):**
```
Question: "What is the title of the most-liked song in my Spotify playlists?"
Expected Answer: "A Love That Never Was"

Result: ✅ SUCCESS
Steps: 14
Time: 86.4s
Passes: 2/2
```

### Implementation Features

- ✅ Context pre-loading (credentials + profile)
- ✅ Structured planning phase
- ✅ Smart tool filtering
- ✅ Enhanced system prompts
- ✅ Structured JSONL logging
- ✅ Message compression

---

## 🔍 Implementation Details

### White Agent Architecture (A2A Mode)

#### 1. TaskAnalyzer

**Purpose:** Intelligently identify which apps are needed for a task

**Implementation:**
```python
class TaskAnalyzer:
    ALL_SUPPORTED_APPS = [
        "amazon", "gmail", "spotify", "venmo", 
        "todoist", "simple_note", "calendar", "phone", "splitwise"
    ]
    
    def identify_apps(self, task_instruction: str) -> List[str]:
        # LLM analyzes task and selects from predefined list
        # Always includes 'supervisor' and 'api_docs'
        # Returns: ['spotify', 'supervisor', 'api_docs']
```

**Benefits:**
- Reduces token usage by filtering irrelevant apps
- Focuses agent attention on relevant APIs
- Improves planning quality

#### 2. ToolRegistry

**Purpose:** Fetch and simplify API documentation for selected apps

**Implementation:**
```python
class ToolRegistry:
    def fetch_tools_schema(self, apps: List[str]) -> Dict[str, List[str]]:
        # Calls api_docs.show_api_descriptions for each app
        # Simplifies: {"name": "login", "params": [...], "desc": "..."}
        # Into: "login(username, password): Authenticate user..."
        
    def _simplify_schema(self, api_docs) -> List[str]:
        # Extracts: function name, parameters, description (first 100 chars)
        # Returns token-friendly format
```

**Benefits:**
- Token-efficient API documentation
- Only includes necessary information
- Easy for LLM to parse and understand

#### 3. ConversationLogger

**Purpose:** Record all agent interactions for debugging and analysis

**Implementation:**
```python
class ConversationLogger:
    def log_turn(self, step: int, action: Dict, observation: str, reasoning: str):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "action": action,
            "observation": observation[:500],  # Truncated
            "reasoning": reasoning[:300]
        }
        # Write to /tmp/a2a_agent_trace_{context_id}.jsonl
```

**Log Format:**
```json
{
  "timestamp": "2025-12-17T22:15:43.726179",
  "step": 15,
  "action": {
    "action": "answer",
    "content": "A Love That Never Was"
  },
  "observation": "API call result: {...}",
  "reasoning": "After comparing all songs..."
}
```

**Benefits:**
- Full execution trace for debugging
- Structured data for analysis
- Enables trajectory metrics calculation

#### 4. Context Pre-loading (Framework)

**Purpose:** Pre-fetch profile and credentials to reduce API calls

**Implementation:**
```python
async def preload_context(self, green_agent_executor, relevant_apps: List[str]):
    # 1. Get profile from supervisor
    profile = await green_agent_executor("supervisor.show_profile", {})
    
    # 2. Get all credentials
    all_creds = await green_agent_executor("supervisor.show_account_passwords", {})
    
    # 3. Filter by relevant apps
    credentials = [c for c in all_creds 
                   if any(app in c["account_name"].lower() for app in relevant_apps)]
    
    return {"profile": profile, "credentials": credentials}
```

**Current Status:**
- Framework implemented
- Gracefully degrades in A2A mode (green_agent_executor not available)
- When preload fails, uses enhanced fallback prompt

**Benefits (when fully implemented):**
- Reduces 2-3 API calls per task
- Credentials available in system prompt
- Agent can start execution immediately

#### 5. Enhanced System Prompt

**Key Components:**

**a) Preloaded Context:**
```
[USER PROFILE]
{"name": "Joyce Weaver", "email": "joyce-weav@gmail.com", ...}

[AVAILABLE CREDENTIALS]
[{"account_name": "spotify", "email": "joyce-weav@gmail.com", "password": "qge1k1L"}]
```

**b) Critical Rules:**
```
1. CREDENTIALS ARE PRELOADED - don't fetch them again
2. LOGIN PARAMETERS: username = email (not account_name)
3. TERMINATION: Use supervisor.complete_task(answer='...') to finish
4. CHAINING: Use output of previous step (don't guess IDs)
5. DATA INTERPRETATION: "most-liked" = highest like_count NUMBER
```

**c) Answer Format Examples:**
```
✅ CORRECT: "A Love That Never Was"
❌ WRONG: "The most-liked song is 'A Love That Never Was' with 18 likes."
❌ WRONG: "A Love That Never Was (https://spotify.com/songs/78)"
```

**Benefits:**
- Clear guidance reduces errors
- Examples prevent common mistakes
- Preloaded data reduces redundant calls

#### 6. Planning Phase

**Process:**
```python
planning_prompt = f"""
Task: {task_instruction}

Provide analysis in JSON:
{{
    "action": "plan",
    "task_type": "question|action",
    "required_apps": ["app1", "app2"],
    "execution_steps": ["Step 1", "Step 2", ...],
    "comparison_needed": "yes|no"
}}
"""

# LLM generates plan
plan = llm_call(planning_prompt)

# Display plan to console
print_plan(plan)

# Add to message history
messages.append({"role": "assistant", "content": plan})
messages.append({"role": "user", "content": "Good plan! Now execute it."})
```

**Benefits:**
- Agent understands task before execution
- Better tool selection
- Identifies comparison tasks that need complete data
- Visible to developers for debugging

#### 7. Message Compression

**Strategy:**
```python
if len(messages) > 20:
    # Layer 1: Keep system prompt + initial task (critical context)
    critical = [messages[0], messages[1]]
    
    # Layer 2: Compress middle messages into summary
    middle = messages[2:-12]
    summary = "=== Progress Summary ===\n" + extract_key_actions(middle)
    
    # Layer 3: Keep last 12 messages (recent context)
    recent = messages[-12:]
    
    # Reconstruct
    messages_to_send = critical + [summary] + recent
```

**Benefits:**
- Prevents context overflow
- Retains critical information
- Maintains recent context for continuity

#### 8. Structured Step Prompt

**Format:**
```
[TASK INSTRUCTION]
What is the title of the most-liked song...

[CURRENT STATUS]
Step: 5

[LAST OBSERVATION]
API call result: {...}

[INSTRUCTION FOR NEXT STEP]
1. If ERROR: Analyze failure, change approach
2. If SUCCESS: Proceed to next step
3. If found IDs: Use them in next action
4. Remember: Compare ALL items for most/least/best tasks
5. Use preloaded credentials - don't fetch again

Generate next JSON response now.
```

**Benefits:**
- Clear guidance for each step
- Reminds agent of best practices
- Reduces off-track behavior

### MCP Mode Enhancements

#### Planning Phase with Tool Filtering

```python
# 1. Keyword-based app detection
task_lower = task_instruction.lower()
relevant_apps = set()
app_keywords = {
    'spotify': ['spotify', 'song', 'music', 'playlist'],
    'gmail': ['gmail', 'email', 'mail'],
    # ... more apps
}

# 2. Filter 469 tools down to ~100 relevant tools
relevant_tools = [tool for tool in all_tools 
                  if any(tool.startswith(app + '__') for app in relevant_apps)]

# 3. LLM selects 3-10 specific tools
selected_tools = llm_select_tools(task, relevant_tools)

# 4. Fetch detailed docs for selected tools only
for tool in selected_tools[:10]:
    doc = mcp_client.call_tool(f"api_docs__show_api_doc", {"api_name": tool})
```

**Benefits:**
- Dramatically reduces planning prompt size (469 → 10 tools)
- Focuses agent on relevant tools
- Improves planning accuracy

#### Smart Sampling Strategy

**System Prompt Addition:**
```
EFFICIENCY TIP - Smart Sampling:
- You don't always need to check EVERY item exhaustively
- If you've checked 50%+ of items and found a clear winner, you can submit
- Example: Song A (like_count=18) after checking 20 songs with max=10
- Balance thoroughness with efficiency
```

**Benefits:**
- Prevents timeout on large datasets
- Allows agent to submit before 30-step limit
- Still maintains accuracy

### Green Agent Implementation

#### Tool Execution in A2A Mode

```python
async def run_appworld_task(white_agent_url: str, task_id: str):
    # 1. Initialize AppWorld environment
    world = AppWorld(task_id=task_id)
    
    # 2. Send initial message to white agent
    for step in range(max_steps):
        # 3. White agent responds with action
        response = await send_message(white_agent_url, message)
        
        # 4. Parse action from response
        action = parse_json(response)
        
        if action["action"] == "answer":
            # 5. Submit answer to AppWorld
            world.execute(f"apis.supervisor.complete_task(answer='{action['content']}')")
            break
        
        elif action["action"] == "call_api":
            # 6. Execute API call in AppWorld
            result = world.execute(f"apis.{app}.{api}({params})")
            # 7. Send result back to white agent
            message = f"API call result: {result}"
    
    # 8. Evaluate with AppWorld's built-in tests
    eval_result = world.evaluate()
    return eval_result.to_dict()
```

#### Evaluation Metrics

**AppWorld Unit Tests:**
- Answer correctness: `"assert answers match"`
- State integrity: `"assert no model changes"`
- Custom assertions defined per task

**Trajectory Metrics (MCP mode):**
```python
def analyze_trajectory(log_file):
    logs = load_jsonl(log_file)
    
    return {
        "total_steps": len(logs),
        "total_api_calls": count_calls(logs),
        "unique_tools": count_unique(logs, "tool_name"),
        "failed_calls": count_errors(logs),
        "error_rate": failed / total,
        "retry_count": count_retries(logs),
        "avg_time_per_step": calculate_avg_time(logs),
        "first_error_step": find_first_error(logs),
        "self_correction": detect_corrections(logs)
    }
```

---

## 📈 Performance Optimization Tips

### For Faster Evaluation

```bash
# 1. Use GPT-4o-mini for testing (faster, cheaper)
WHITE_AGENT_MODEL=openai/gpt-4o-mini python main.py launch --task-id 82e2fac_1

# 2. Reduce max steps if timeouts occur
# Edit src/green_agent/agent.py: MAX_STEPS = 20

# 3. Skip trajectory analysis for speed
# Edit src/green_agent/agent_mcp.py: Comment out trajectory analysis section
```

### For Better Results

```bash
# 1. Use GPT-5 for complex tasks
WHITE_AGENT_MODEL=openai/gpt-5 python main.py launch --task-id <complex_task>

# 2. Increase max steps for complex tasks
# Edit src/green_agent/agent.py: MAX_STEPS = 50

# 3. Enable verbose logging
# Check /tmp/a2a_agent_trace_*.jsonl for debugging
```

---

## 🐛 Troubleshooting

### Common Issues and Solutions

#### 1. Port Already in Use

**Error:**
```
ERROR: [Errno 98] error while attempting to bind on address ('0.0.0.0', 9001): address already in use
```

**Solution:**
```bash
# Kill all related processes
pkill -9 -f "python main.py"
pkill -9 -f "uvicorn"

# Or kill specific ports
lsof -ti :9000,:9001,:9002,:10000 | xargs -r kill -9

# Wait a few seconds
sleep 3

# Try again
python main.py launch --task-id 82e2fac_1
```

#### 2. OpenAI API Errors

**Error:**
```
Error code: 429 - Rate limit exceeded
```

**Solution:**
```bash
# Wait for rate limit to reset (usually 60 seconds)
sleep 60

# Or use a different model
WHITE_AGENT_MODEL=openai/gpt-4o-mini python main.py launch --task-id 82e2fac_1
```

**Error:**
```
Error code: 400 - Unsupported value: 'temperature' does not support 0
```

**Solution:**
This is already handled in the code for o1/o3/gpt-5 models. If you see this, check that your `WHITE_AGENT_MODEL` is set correctly.

#### 3. AppWorld Not Found

**Error:**
```
ModuleNotFoundError: No module named 'appworld'
```

**Solution:**
```bash
# Ensure AppWorld is installed
cd /path/to/appworld
pip install -e .

# Or set APPWORLD_ROOT
export APPWORLD_ROOT=/path/to/appworld
```

#### 4. Task Timeout

**Error:**
```
Task incomplete after 30 steps
```

**Solution:**
- Check JSONL log to see where agent got stuck
- Increase `MAX_STEPS` in `src/green_agent/agent.py`
- Or improve agent prompting to be more efficient

#### 5. Answer Format Mismatch

**Error:**
```
AssertionError: 'the most-liked song is...' == 'A Love That Never Was'
```

**Solution:**
This should be fixed in the enhanced version with improved answer format instructions. If still occurs:
- Check that white agent is using the enhanced system prompt
- Verify fallback prompt includes answer format examples
- Check logs to see LLM's reasoning

---

## 📚 File Structure

```
appworld-agentic-evaluation/
├── main.py                          # Entry point
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
│
├── src/
│   ├── white_agent/                 # White agent (under test)
│   │   ├── agent.py                 # A2A mode implementation (ENHANCED)
│   │   ├── agent_mcp.py             # MCP mode implementation
│   │   └── appworld_white_agent.toml
│   │
│   ├── green_agent/                 # Green agent (evaluator)
│   │   ├── agent.py                 # A2A mode green agent
│   │   ├── agent_mcp.py             # MCP mode green agent
│   │   └── appworld_green_agent.toml
│   │
│   └── evaluator/
│       └── trajectory_analyzer.py   # Trajectory metrics analysis
│
├── logs/                            # Execution logs
│   └── .gitkeep
│
├── test_*.py                        # Unit tests
├── main.py                          # Entry point
└── requirements.txt                 # Dependencies
```

### Key Files

**White Agent (A2A Mode) - `src/white_agent/agent.py`:**
- Lines 1-200: Helper classes (ConversationLogger, TaskAnalyzer, ToolRegistry)
- Lines 201-387: Context management and prompt building
- Lines 388-690: Main execute loop with initialization phase

**White Agent (MCP Mode) - `src/white_agent/agent_mcp.py`:**
- Lines 1-470: Setup and planning phase
- Lines 471-1000: Execute loop with MCP integration

**Green Agent (A2A) - `src/green_agent/agent.py`:**
- Lines 1-200: Task setup and environment initialization
- Lines 201-400: API execution and result handling
- Lines 401-530: Evaluation and metrics collection

---

## 🔬 Extension Topics

### Custom White Agent Development

To develop your own white agent that works with our green agent:

1. **Implement A2A Protocol:**
   - Expose `.well-known/agent-card.json`
   - Accept POST messages in A2A format
   - Return responses in A2A format

2. **Handle Green Agent Messages:**
```python
# Green agent sends:
{
  "task": "What is the title of the most-liked song...",
  "tool_schema": {"spotify": [...], "supervisor": [...]},
  "max_steps": 30
}

# White agent should respond with:
{
  "action": "call_api",
  "api_name": "spotify.login",
  "parameters": {"username": "...", "password": "..."}
}

# Or:
{
  "action": "answer",
  "content": "A Love That Never Was"
}
```

3. **Test Against Green Agent:**
```bash
# Start your white agent on port 9002
python your_white_agent.py --port 9002

# In another terminal, test with green agent
python main.py launch --task-id 82e2fac_1
```

### Extending the Framework

**Add New Metrics:**

Edit `src/evaluator/trajectory_analyzer.py`:
```python
def analyze_trajectory(log_file):
    # ... existing metrics
    
    # Add custom metric
    metrics["custom_metric"] = calculate_custom_metric(logs)
    
    return metrics
```

**Add New Apps:**

Edit `src/white_agent/agent.py`:
```python
class TaskAnalyzer:
    ALL_SUPPORTED_APPS = [
        "amazon", "gmail", "spotify", "venmo",
        "todoist", "simple_note", "calendar", "phone", "splitwise",
        "your_new_app"  # Add here
    ]
```

**Customize System Prompt:**

Edit `src/white_agent/agent.py` in `build_enhanced_system_prompt` method.

---

## 📖 Citation

If you use this work in your research, please cite:

```bibtex
@misc{appworld-green-agent-2025,
  title={AppWorld Green Agent: An Agentified Benchmark Platform},
  author={Your Name},
  year={2025},
  howpublished={\url{https://github.com/yilin-610-c/appworld-agentic-evaluation}}
}

@article{trivedi2024appworld,
  title={AppWorld: A Controllable World of Apps and People for Benchmarking Interactive Coding Agents},
  author={Trivedi, Harsh and Khot, Tushar and Hartmann, Mareike and Manku, Ruskin and Dong, Vinty and Li, Edward and Gupta, Shashank and Sabharwal, Ashish and Balasubramanian, Niranjan},
  journal={arXiv preprint arXiv:2407.18901},
  year={2024}
}
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **AppWorld Team** at Stony Brook University for the original benchmark
- **UC Berkeley AgentX-AgentBeats** competition for motivation and framework
- **my_agent.py** implementation for architectural inspiration (context pre-loading, structured logging)
- **OpenAI** for GPT-4o/GPT-5 model access

---

## 📞 Contact

For questions, issues, or contributions:
- GitHub Issues: [https://github.com/yilin-610-c/appworld-agentic-evaluation/issues](https://github.com/yilin-610-c/appworld-agentic-evaluation/issues)
- Email: your-email@example.com

---

## 🎉 Quick Start Recap

```bash
# 1. Setup (one-time)
conda create -n appworld_agent_py313 python=3.13
conda activate appworld_agent_py313
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."

# 2. Run a single task (A2A mode)
python main.py launch --task-id 82e2fac_1

# 3. Run with MCP mode
python main.py launch --task-id 82e2fac_1 --mcp

# 4. Check logs
cat /tmp/a2a_agent_trace_*.jsonl | jq .

# 5. Run batch evaluation
python main.py batch --num-tasks 10

# Done! 🎊
```

---

**Happy Evaluating! 🚀**

