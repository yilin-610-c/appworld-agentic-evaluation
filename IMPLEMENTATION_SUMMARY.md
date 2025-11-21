# AppWorld Green Agent - Implementation Summary

## ✅ Implementation Complete

This project successfully implements an agentified version of the AppWorld benchmark using the A2A framework and AgentBeats methodology.

## What Was Implemented

### 1. **Green Agent** (Environment/Assessment Agent)
- File: `src/green_agent/agent.py`
- Implements A2A server using `a2a-sdk`
- Loads AppWorld tasks and retrieves API documentation
- **Tool Delivery Approach II**: Sends tool list in the first message to white agent
- Executes API calls requested by white agent
- Evaluates task completion and returns metrics

### 2. **White Agent** (Tested Agent)
- File: `src/white_agent/agent.py`
- Simple OpenAI GPT-4 based agent
- Implements A2A server interface
- Receives tools from green agent
- Makes decisions and calls APIs via structured JSON responses
- Maintains conversation context across multiple steps

### 3. **Launcher** 
- File: `src/launcher.py`
- Coordinates green and white agents
- Starts both agents in separate processes
- Sends tasks to green agent for evaluation
- Manages agent lifecycle

### 4. **Utility Functions**
- `src/util/__init__.py`: Tag parsing for XML-like message format
- `src/util/a2a_client.py`: A2A communication helpers (send_message, wait_agent_ready, etc.)

### 5. **CLI Interface**
- File: `main.py`
- Commands: `green`, `white`, `launch`, `list-tasks`
- Typer-based CLI for easy interaction

### 6. **AgentBeats Integration**
- File: `run.sh` - Entry point for AgentBeats controller
- TOML configuration: `src/green_agent/appworld_green_agent.toml`
- Compatible with `agentbeats run_ctrl` command

## Architecture Highlights

### Tool Delivery Approach II
As described in [AgentBeats Blog 2](https://docs.agentbeats.org/Blogs/blog-2/), the green agent sends the complete tool list in its **first message**:

```
Your task is: [instruction]

Available APIs: [JSON array of tool specifications]

Communication Protocol:
- To call API: {"action": "call_api", "api_name": "...", "parameters": {...}}
- To answer: {"action": "answer", "content": "..."}
```

### Message Flow
1. **Launcher** → **Green Agent**: Task request with white agent URL and task ID
2. **Green Agent** initializes AppWorld task and gets API docs
3. **Green Agent** → **White Agent**: Initial message with task + tools
4. **White Agent** → **Green Agent**: API call request (JSON)
5. **Green Agent** executes API in AppWorld
6. **Green Agent** → **White Agent**: API result
7. Steps 4-6 repeat until white agent provides final answer
8. **Green Agent** completes task and evaluates

## Project Structure

```
appworld_green_agent/
├── src/
│   ├── green_agent/
│   │   ├── agent.py                        # Green agent implementation
│   │   ├── appworld_green_agent.toml       # Agent card configuration
│   │   └── __init__.py
│   ├── white_agent/
│   │   ├── agent.py                        # White agent (OpenAI-based)
│   │   └── __init__.py
│   ├── util/
│   │   ├── __init__.py                     # Tag parsing utilities
│   │   └── a2a_client.py                   # A2A communication helpers
│   ├── launcher.py                         # Evaluation coordinator
│   └── __init__.py
├── main.py                                 # CLI entry point
├── run.sh                                  # AgentBeats controller entry
├── .env                                    # Environment configuration
└── README.md                               # Documentation
```

## Dependencies Installed

1. **Python 3.13** (conda environment: `appworld_agent_py313`)
2. **AppWorld** - Benchmark framework
3. **a2a-sdk[http-server]** - Agent-to-agent communication
4. **OpenAI** - LLM API
5. **LiteLLM** - Unified LLM interface
6. **FastAPI, Uvicorn, Starlette** - Web framework for A2A servers
7. **Other**: httpx, python-dotenv, typer, etc.

## Key Implementation Decisions

1. **Single Task Evaluation**: Initial scope focuses on one task at a time (like TAU-bench example)
2. **Default OpenAI Model**: White agent uses `gpt-4o` via LiteLLM
3. **No Try-Except**: Following user rules, errors propagate naturally
4. **Real AppWorld Tasks**: Uses actual task `82e2fac_1` from training set
5. **Text-Based Tool Delivery**: Tools sent as JSON in message text (Approach II)

## Usage Notes

### Running Evaluations

Due to AppWorld's path requirements, you have two options:

**Option 1: Run from AppWorld directory (Recommended)**
```bash
cd /home/lyl610/green1112/appworld
export OPENAI_API_KEY="your-key-here"
python ../appworld_green_agent/main.py launch --task-id 82e2fac_1
```

**Option 2: Set environment variable**
```bash
export APPWORLD_DATA_ROOT=/home/lyl610/green1112/appworld/data
export OPENAI_API_KEY="your-key-here"
cd /home/lyl610/green1112/appworld_green_agent
python main.py launch --task-id 82e2fac_1
```

### Testing Individual Components

**Test Green Agent:**
```bash
cd /home/lyl610/green1112/appworld_green_agent
python main.py green  # Starts on port 9001
```

**Test White Agent:**
```bash
cd /home/lyl610/green1112/appworld_green_agent  
python main.py white  # Starts on port 9002
```

**List Available Tasks:**
```bash
cd /home/lyl610/green1112/appworld
python ../appworld_green_agent/main.py list-tasks
```

## Example Task

**Task ID**: `82e2fac_1`  
**Instruction**: "What is the title of the most-liked song in my Spotify playlists."

**Expected Behavior**:
1. White agent receives task + Spotify API documentation
2. Calls `spotify.login()` to authenticate
3. Calls `spotify.show_playlist_library()` to get playlists
4. Iterates through playlists calling `spotify.show_playlist()`
5. Finds song with most likes
6. Returns answer: `{"action": "answer", "content": "song title"}`
7. Green agent evaluates correctness against AppWorld ground truth

## Future Enhancements

- [ ] Support for multiple tasks in batch
- [ ] Integration with AgentBeats platform for hosted evaluation
- [ ] More sophisticated white agent with reasoning capabilities
- [ ] Support for other LLM providers beyond OpenAI
- [ ] Metrics tracking and visualization
- [ ] Docker containerization for deployment

## References

- [AppWorld](https://github.com/StonyBrookNLP/appworld)
- [A2A Framework](https://github.com/a2aproject/A2A)
- [AgentBeats Documentation](https://docs.agentbeats.org/)
- [TAU-bench Example](https://github.com/agentbeats/agentify-example-tau-bench)

## Completion Status

All planned components have been implemented:
- ✅ Environment setup (Python 3.13, all dependencies)
- ✅ Green agent with A2A server and AppWorld integration
- ✅ White agent with OpenAI integration
- ✅ Tool Delivery Approach II implementation
- ✅ Launcher for coordinating evaluation
- ✅ run.sh for AgentBeats controller compatibility
- ✅ Complete documentation (README, this summary)
- ⚠️  End-to-end testing requires OPENAI_API_KEY

The implementation is ready for use. Users need to:
1. Add their OpenAI API key to `.env`
2. Run from the appworld directory or set APPWORLD_DATA_ROOT
3. Execute `python main.py launch --task-id 82e2fac_1`


