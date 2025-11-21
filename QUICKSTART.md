# Quick Start Guide - AppWorld Green Agent

## Prerequisites Check
- ✅ Python 3.13 environment: `appworld_agent_py313`
- ✅ AppWorld installed and data downloaded
- ⚠️ **Required**: OpenAI API Key

## Step 1: Set Up Environment

```bash
# Activate the conda environment
conda activate appworld_agent_py313

# Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"
```

## Step 2: Run a Single Task Evaluation

The simplest way to run an evaluation:

```bash
# Navigate to the appworld directory (required for data access)
cd /home/lyl610/green1112/appworld

# Launch evaluation for task 82e2fac_1
python ../appworld_green_agent/main.py launch --task-id 82e2fac_1
```

This will:
1. Start the green agent (assessment manager) on port 9001
2. Start the white agent (OpenAI-based) on port 9002
3. Run the task evaluation
4. Display results and metrics
5. Automatically terminate both agents

## Step 3: Understanding the Output

You should see:
```
Launching green agent...
Waiting for green agent to be ready...
Green agent is ready.

Launching white agent...
Waiting for white agent to be ready...
White agent is ready.

Sending task to green agent (task_id: 82e2fac_1)...
...
[Green agent logs showing task execution]
...
Evaluation complete. Terminating agents...
```

## Alternative: Run Agents Separately

### Terminal 1: Start Green Agent
```bash
cd /home/lyl610/green1112/appworld
python ../appworld_green_agent/main.py green
# Listens on http://localhost:9001
```

### Terminal 2: Start White Agent
```bash
cd /home/lyl610/green1112/appworld_green_agent
export OPENAI_API_KEY="your-key"
python main.py white
# Listens on http://localhost:9002
```

### Terminal 3: Send Evaluation Request
```python
import asyncio
from src.util.a2a_client import send_message

async def test():
    message = """<white_agent_url>
http://localhost:9002/
</white_agent_url>

<task_id>
82e2fac_1
</task_id>"""
    
    response = await send_message("http://localhost:9001", message)
    print(response)

asyncio.run(test())
```

## Available Tasks

List all available tasks:
```bash
cd /home/lyl610/green1112/appworld
python ../appworld_green_agent/main.py list-tasks
```

Output:
```
train: 90 tasks
  First 5: ['82e2fac_1', '82e2fac_2', '82e2fac_3', '692c77d_1', '692c77d_2']

dev: [number] tasks
  First 5: [...]
...
```

## Troubleshooting

### "OPENAI_API_KEY not set"
```bash
export OPENAI_API_KEY="sk-..."
# Or add to .env file in appworld_green_agent/
```

### "Task directory doesn't exist"
Make sure you're running from the appworld directory:
```bash
cd /home/lyl610/green1112/appworld
```

### "Agent not ready in time"
The agent may need more time to start. Increase timeout in `src/util/a2a_client.py:wait_agent_ready(timeout=10)` to a higher value like 30.

### Import Errors
Verify environment:
```bash
conda activate appworld_agent_py313
which python  # Should show miniconda3/envs/appworld_agent_py313/bin/python
```

## Next Steps

1. **Try different tasks**: Change `--task-id` to other values from `list-tasks`
2. **Deploy with AgentBeats**: Use `./run.sh` or `agentbeats run_ctrl`
3. **Customize white agent**: Modify `src/white_agent/agent.py` to use different models
4. **Extend evaluation**: Modify `src/green_agent/agent.py` to add more metrics

## Important Notes

- **Real AppWorld Tasks**: The system uses actual AppWorld benchmark tasks
- **Tool Delivery Approach II**: Tools are sent in the green agent's first message
- **OpenAI GPT-4**: Default model is `gpt-4o` via LiteLLM
- **Single Task**: Current implementation focuses on one task at a time
- **No Error Handling**: As per user rules, errors propagate naturally (no try-except)

## Documentation

- Full README: `appworld_green_agent/README.md`
- Implementation Summary: `appworld_green_agent/IMPLEMENTATION_SUMMARY.md`
- Code structure: See `src/` directory with green_agent, white_agent, and launcher

## Support

If you encounter issues:
1. Check all environment variables are set
2. Verify AppWorld installation: `appworld --version`
3. Test imports: `python -c "from src.green_agent import start_green_agent"`
4. Review logs in the terminal output

Happy evaluating! 🚀


