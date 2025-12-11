# AppWorld Green Agent: Agentified Benchmark Platform

[![UC Berkeley AgentX-AgentBeats](https://img.shields.io/badge/AgentX--AgentBeats-Phase%201-green)](https://rdi.berkeley.edu/agentx-agentbeats.html)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An agentified evaluation infrastructure for the AppWorld benchmark, built for the UC Berkeley AgentX-AgentBeats competition. This system transforms AppWorld into an interactive, standardized benchmark using the Agent-to-Agent (A2A) protocol and Model Context Protocol (MCP).

## 🎯 Overview

This project implements a **Green Agent** (benchmark/evaluator) that assesses **White Agents** (AI agents under test) on real-world tasks spanning 9 applications with 469+ APIs. It supports two tool delivery approaches:

- **Approach II**: JSON-based tool description (traditional)
- **Approach III (MCP)**: Live tool discovery via Model Context Protocol (advanced)

### Key Features

- ✅ **Standardized Evaluation**: A2A-compatible interface for any agent
- ✅ **Dynamic Tool Discovery**: MCP-based real-time API access
- ✅ **Intelligent Planning**: Keyword-based tool filtering (469 → ~100 relevant tools)
- ✅ **Multi-dimensional Metrics**: Success rate, API efficiency, failed execution tracking
- ✅ **Reproducible Assessment**: Consistent initial state for each evaluation run
- ✅ **Production-Ready**: Cloud Run deployment with automated resource management

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Green Agent (Evaluator)                        │
│  • Manages AppWorld tasks and environments                       │
│  • Orchestrates MCP/API servers                                  │
│  • Evaluates white agent performance                             │
└──────────────────────────────────────────────────────────────────┘
                              │
                              │ A2A Protocol (standardized communication)
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                    White Agent (Under Test)                       │
│  • Baseline: OpenAI GPT-4o with planning phase                   │
│  • Discovers tools dynamically                                   │
│  • Executes multi-step reasoning                                 │
└──────────────────────────────────────────────────────────────────┘
                              │
                              │ MCP (Approach III)
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                    MCP Server + API Server                        │
│  • Exposes 469 AppWorld tools                                    │
│  • Task-specific database loading                                │
│  • Ports: 9000 (API), 10000 (MCP)                                │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📦 Installation

### Prerequisites

- **Python 3.13+**
- **Conda** (recommended for environment management)
- **Git**
- **OpenAI API Key**

### Setup Steps

#### 1. Clone the Repository

```bash
git clone https://github.com/your-username/appworld-green-agent.git
cd appworld-green-agent
```

#### 2. Create Conda Environment

```bash
conda create -n appworld_agent_py313 python=3.13
conda activate appworld_agent_py313
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
pip install mcp  # For Approach III (MCP mode)
```

#### 4. Setup AppWorld Benchmark

```bash
# Clone AppWorld repository (adjacent to this project)
cd ..
git clone https://github.com/stonybrooknlp/appworld.git
cd appworld

# Download dataset
python -m appworld.cli download --dataset-version v1
```

#### 5. Configure Environment Variables

```bash
# Add to ~/.bashrc or ~/.zshrc
export APPWORLD_ROOT=/path/to/appworld
export OPENAI_API_KEY=your-openai-api-key-here
```

**Verify setup:**

```bash
echo $APPWORLD_ROOT
ls $APPWORLD_ROOT/data  # Should show task files
```

---

## 🚀 Usage

### Quick Start: Single Task Evaluation

#### Approach II (JSON-based)

```bash
# Launch both green and white agents
python main.py launch --task-id 82e2fac_1
```

#### Approach III (MCP - Recommended)

```bash
# Launch with MCP for dynamic tool discovery
python main.py launch --task-id 82e2fac_1 --mcp
```

### Batch Evaluation

```bash
# Evaluate multiple tasks
python main.py batch --task-ids 82e2fac_1,a1b2c3d_2,xyz123_3 --output results.json

# With MCP
python main.py batch --task-ids 82e2fac_1,a1b2c3d_2 --output results.json --mcp
```

### Running Agents Separately

```bash
# Terminal 1: Start Green Agent
python main.py green --host 0.0.0.0 --port 9001 --mcp

# Terminal 2: Start White Agent
python main.py white --host 0.0.0.0 --port 9002 --mcp

# Terminal 3: Send evaluation request (using A2A client)
curl -X POST http://localhost:9001 \
  -H "Content-Type: application/json" \
  -d '{"white_agent_url": "http://localhost:9002", "task_id": "82e2fac_1"}'
```

---

## 📊 Evaluation Metrics

The system tracks multiple dimensions of agent performance:

| Metric | Description |
|--------|-------------|
| **Success Rate** | Task completion accuracy (unit tests passed) |
| **API Call Efficiency** | Success/failure rate of tool calls |
| **Failed Execution Count** | Number of failed attempts or errors |
| **Interaction Steps** | Total steps taken to complete task |
| **Task Completion Time** | Duration of evaluation |

Example output:

```json
{
  "task_id": "82e2fac_1",
  "success": true,
  "steps": 7,
  "final_answer": "A Love That Never Was",
  "evaluation": {
    "success": true,
    "difficulty": 1,
    "num_tests": 2,
    "passes": [...]
  }
}
```

---

## 📁 Project Structure

```
appworld_green_agent/
├── main.py                          # CLI entry point
├── requirements.txt                 # Python dependencies
├── run.sh                           # AgentBeats controller startup script
├── startup.sh                       # Cloud Run deployment script
├── Procfile                         # Process configuration
│
├── src/
│   ├── green_agent/
│   │   ├── agent.py                # Green Agent (Approach II)
│   │   ├── agent_mcp.py           # Green Agent (Approach III - MCP)
│   │   ├── serve_task_apis.py     # Custom API server with task-specific DB loading
│   │   └── appworld_green_agent.toml
│   │
│   ├── white_agent/
│   │   ├── agent.py                # White Agent (Approach II)
│   │   ├── agent_mcp.py           # White Agent (Approach III - MCP with Planning)
│   │   └── appworld_white_agent.toml
│   │
│   ├── evaluator/
│   │   └── batch_evaluator.py      # Batch evaluation logic
│   │
│   ├── util/
│   │   ├── __init__.py             # parse_tags utility
│   │   └── a2a_client.py           # A2A protocol client
│   │
│   ├── launcher.py                 # Launcher for Approach II
│   └── launcher_mcp.py             # Launcher for Approach III (MCP)
│
└── README.md                        # This file
```

---

## 🧠 Technical Deep Dive

### Approach III: MCP with Intelligent Planning

The MCP-based approach includes a **Planning Phase** that significantly improves performance:

1. **Task Analysis**: Extract keywords from task instruction (e.g., "Spotify", "playlist")
2. **Tool Filtering**: Narrow 469 tools → ~100 relevant tools using keyword matching
3. **LLM Planning**: GPT-4o predicts execution plan with specific tools
4. **Documentation Fetching**: Pre-load API docs for predicted tools
5. **Enhanced Prompt**: System prompt includes planned tools + full relevant tool list

**Benefits:**
- Reduces hallucination (LLM sees only relevant tools)
- Faster execution (pre-fetched documentation)
- Better task completion rate

### MCP Server Management

Green Agent automatically manages infrastructure:

```python
# Simplified flow
1. Start API Server (port 9000) with task-specific DB
2. Start MCP Server (port 10000) connected to API Server
3. White Agent discovers tools via MCP
4. White Agent calls tools → MCP Server → API Server → AppWorld
5. Green Agent evaluates results
6. Cleanup: Stop servers, reset state
```

### Port Management & Error Handling

- Automatic port conflict detection and resolution
- Graceful subprocess cleanup
- Comprehensive error logging
- Timeout protection for Cloud Run

---

## 🛠️ Troubleshooting

### Port Already in Use

```bash
# Check what's using the ports
lsof -i :9000 -i :10000

# Kill processes
kill <PID>
```

The system attempts automatic cleanup, but manual intervention may be needed.

### MCP Connection Fails

1. Verify ports 9000 and 10000 are available
2. Check `APPWORLD_ROOT` is set correctly
3. Review logs: `tail -f /tmp/mcp_server.log`

### OpenAI API Errors

```bash
# Verify API key
echo $OPENAI_API_KEY

# Test API access
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Task Data Not Found

```bash
# Verify AppWorld data
ls $APPWORLD_ROOT/data/tasks/

# Re-download if needed
cd $APPWORLD_ROOT
python -m appworld.cli download --dataset-version v1
```

---

## 🚢 Cloud Deployment (Optional)

### Deploy to Google Cloud Run

```bash
# Build and deploy
gcloud run deploy appworld-green-agent \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --set-env-vars APPWORLD_ROOT=/workspace/appworld

# Get service URL
gcloud run services describe appworld-green-agent --format='value(status.url)'
```

### Submit to AgentBeats

1. Visit [AgentBeats Platform](https://agentbeats.ai/)
2. Register your Green Agent
3. Submit your Controller URL

---

## 🧪 Development & Testing

### Running Tests

```bash
# Test single task (Approach II)
python main.py launch --task-id 82e2fac_1

# Test with MCP
python main.py launch --task-id 82e2fac_1 --mcp

# Batch evaluation
python main.py batch --task-file test_tasks.txt --output results.json --mcp
```

### Adding New Tasks

Create `test_tasks.txt`:

```
82e2fac_1
a1b2c3d_2
xyz123_3
```

### Modifying Evaluation Logic

- **Green Agent**: Edit `src/green_agent/agent_mcp.py`
- **White Agent**: Edit `src/white_agent/agent_mcp.py`
- **Planning Phase**: Modify `plan_task()` in white agent
- **Metrics**: Update evaluation section in green agent

---

## 📈 Performance Notes

- **Task Evaluation**: 1-5 minutes per task (complexity-dependent)
- **MCP Server Startup**: ~8 seconds
- **Tool Discovery**: <1 second for 469 tools
- **Planning Phase**: ~5 seconds (GPT-4o call + doc fetching)

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **UC Berkeley RDI** for hosting the AgentX-AgentBeats competition
- **AppWorld Team** at Stony Brook NLP for the comprehensive benchmark
- **AgentBeats Platform** for standardized agent evaluation infrastructure
- **Model Context Protocol (MCP)** for dynamic tool interaction framework
- **Agent2Agent (A2A) Protocol** for agent communication standards

---

## 📧 Contact

For questions or issues:
- Open an issue on GitHub
- Competition Discord: [AgentX-AgentBeats Discord](https://discord.gg/agentx)

---

## 🔗 Related Links

- [AgentX-AgentBeats Competition](https://rdi.berkeley.edu/agentx-agentbeats.html)
- [AppWorld Benchmark](https://github.com/stonybrooknlp/appworld)
- [AgentBeats Platform](https://agentbeats.ai/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [A2A Protocol Documentation](https://github.com/berkeley-function-call-leaderboard/agent2agent)

---

**Built with ❤️ for the AgentX-AgentBeats Competition**
