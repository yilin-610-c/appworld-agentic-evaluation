# AppWorld Green Agent

A comprehensive evaluation framework for testing AI agents on real-world tasks using the AppWorld benchmark.

## Overview

This project implements a **Green Agent** (assessment agent) that evaluates **White Agents** (AI agents being tested) on AppWorld tasks. It supports two tool delivery approaches:

- **Approach II**: Tools delivered as JSON text in initial message
- **Approach III (MCP)**: Tools delivered via Model Context Protocol (real-time tool discovery and execution)

## Features

- ✅ Complete AppWorld task evaluation
- ✅ Support for both Approach II and Approach III (MCP)
- ✅ Agent2Agent (A2A) protocol integration
- ✅ AgentBeats controller integration for easy deployment
- ✅ Cloud Run deployment support
- ✅ Batch evaluation capabilities
- ✅ Real-time MCP server management
- ✅ Automatic port management and cleanup

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Green Agent                              │
│  (Manages AppWorld tasks, MCP servers, and evaluation)          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ A2A Protocol
                              │
┌─────────────────────────────────────────────────────────────────┐
│                         White Agent                              │
│  (OpenAI-based agent being tested)                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ (Approach III)
                              │
┌─────────────────────────────────────────────────────────────────┐
│                         MCP Server                               │
│  (Exposes 457 AppWorld tools via MCP protocol)                  │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.13+
- Conda (recommended)
- AppWorld dataset

### Setup

1. **Clone the repository**:
```bash
git clone <repository-url>
cd appworld_green_agent
```

2. **Create Conda environment**:
```bash
conda create -n appworld_agent_py313 python=3.13
conda activate appworld_agent_py313
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Install MCP package** (for Approach III):
```bash
pip install mcp
```

5. **Set up AppWorld**:
```bash
# Clone AppWorld repository
cd ..
git clone https://github.com/stonybrooknlp/appworld.git
cd appworld

# Download dataset
python -m appworld.cli download --dataset-version v1
```

6. **Set environment variables**:
```bash
export APPWORLD_ROOT=/path/to/appworld
export OPENAI_API_KEY=your-api-key-here
```

## Usage

### Local Testing

#### Approach II (JSON Tool Delivery)

```bash
# Launch Green and White agents
python main.py launch --task-id 82e2fac_1

# Or run agents separately
python main.py green --host 0.0.0.0 --port 9001
python main.py white --host 0.0.0.0 --port 9002
```

#### Approach III (MCP)

```bash
# Launch with MCP support
python main.py launch --task-id 82e2fac_1 --mcp

# Or run agents separately with MCP
python main.py green --host 0.0.0.0 --port 9001 --mcp
python main.py white --host 0.0.0.0 --port 9002 --mcp
```

### Batch Evaluation

```bash
# Evaluate on multiple tasks
python main.py batch --task-ids 82e2fac_1,a1b2c3d_2 --output results.json

# With MCP
python main.py batch --task-ids 82e2fac_1,a1b2c3d_2 --output results.json --mcp
```

### Cloud Deployment

1. **Build and deploy to Cloud Run**:
```bash
gcloud run deploy appworld-green-agent \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --timeout 3600
```

2. **Submit to AgentBeats**:
   - Visit https://agentbeats.ai/
   - Register your Green Agent
   - Submit your Controller URL

## Project Structure

```
appworld_green_agent/
├── main.py                      # CLI entry point
├── src/
│   ├── green_agent/
│   │   ├── agent.py            # Green Agent (Approach II)
│   │   ├── agent_mcp.py        # Green Agent (Approach III - MCP)
│   │   └── appworld_green_agent.toml
│   ├── white_agent/
│   │   ├── agent.py            # White Agent (Approach II)
│   │   ├── agent_mcp.py        # White Agent (Approach III - MCP)
│   │   └── appworld_white_agent.toml
│   ├── launcher.py             # Launcher for Approach II
│   ├── launcher_mcp.py         # Launcher for Approach III
│   ├── evaluator/
│   │   └── batch_evaluator.py  # Batch evaluation
│   └── util/
│       ├── parse_tags.py       # XML tag parsing
│       └── a2a_client.py       # A2A client utilities
├── run.sh                       # AgentBeats controller script
├── startup.sh                   # Cloud Run startup script
├── Procfile                     # Process configuration
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Key Features Explained

### Approach II: JSON Tool Delivery

- Tools are serialized as JSON and sent in the initial message
- White Agent receives complete tool schemas upfront
- Simple and straightforward
- Limited by message size for large tool sets

### Approach III: MCP (Model Context Protocol)

- Tools are discovered dynamically via MCP server
- White Agent queries MCP server for available tools
- Real-time tool execution through MCP protocol
- Scalable to large tool sets (457 AppWorld tools)
- Supports structured output and validation

### Automatic Port Management

The system automatically handles port conflicts:
- Checks port availability before starting servers
- Discovers and stops processes using occupied ports
- Uses `SO_REUSEADDR` to allow immediate port reuse
- Graceful error messages if ports cannot be freed

### MCP Server Management

Green Agent automatically manages MCP infrastructure:
- Starts API Server (port 9000) for AppWorld APIs
- Starts MCP Server (port 10000) for tool delivery
- Handles server lifecycle (startup, health checks, shutdown)
- Prevents pipe blocking with proper output handling

## Environment Variables

- `APPWORLD_ROOT`: Path to AppWorld repository (required)
- `OPENAI_API_KEY`: OpenAI API key for White Agent (required)
- `PORT`: Server port (for Cloud Run, default: 8080)

## Troubleshooting

### Port Conflicts

If you see "Port already in use" errors:
```bash
# Find processes using ports
lsof -i :9000 -i :10000

# Kill specific process
kill <PID>
```

The system will attempt to do this automatically, but manual intervention may be needed in some cases.

### MCP Connection Issues

If MCP server fails to connect:
1. Check that port 10000 is available
2. Verify API server is running on port 9000
3. Check logs for detailed error messages

### AppWorld Data Not Found

If you see "AppWorld data directory not found":
```bash
# Verify APPWORLD_ROOT is set
echo $APPWORLD_ROOT

# Check data directory exists
ls $APPWORLD_ROOT/data
```

## Development

### Running Tests

```bash
# Test Approach II
python main.py launch --task-id 82e2fac_1

# Test Approach III (MCP)
python main.py launch --task-id 82e2fac_1 --mcp
```

### Code Structure

- **Green Agent**: Manages task evaluation, coordinates with White Agent
- **White Agent**: OpenAI-based agent that attempts to solve tasks
- **MCP Server**: Exposes AppWorld tools via MCP protocol
- **Launcher**: Coordinates Green and White agents for local testing

## Performance

- **Task Evaluation**: ~1-5 minutes per task (depends on complexity)
- **MCP Server Startup**: ~5 seconds
- **Tool Discovery**: ~1 second (457 tools)
- **Tool Execution**: Real-time via MCP protocol

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Your License Here]

## Acknowledgments

- AppWorld benchmark team
- AgentBeats platform
- Model Context Protocol (MCP) specification
- Agent2Agent (A2A) protocol

## Contact

[Your Contact Information]
