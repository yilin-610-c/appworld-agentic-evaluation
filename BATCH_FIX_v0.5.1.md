# Batch Evaluation Bug Fix - v0.5.1

## Issue

Batch evaluation failed with error:
```
ERROR: Error loading ASGI app. Could not import module "src.green_agent.server".
ERROR: Error loading ASGI app. Could not import module "src.white_agent.server".
```

## Root Cause

The `batch_evaluator.py` was trying to start agents using:
```python
['python', '-m', 'uvicorn', 'src.green_agent.server:app', ...]
```

But the agents don't have `server.py` files. They start through the `start_green_agent()` and `start_white_agent()` functions.

## Fix

Changed the subprocess commands to:
```python
['python', '-c',
 f'from src.green_agent import start_green_agent; start_green_agent(port={green_port})']
['python', '-c',
 f'from src.white_agent import start_white_agent; start_white_agent(port={white_port})']
```

## Verification

After the fix, agents start correctly:
```
Starting AppWorld green agent...
INFO:     Uvicorn running on http://localhost:9001
Starting AppWorld white agent...
INFO:     Uvicorn running on http://localhost:9002
```

## Prerequisites for Running Batch Evaluation

Before running batch evaluation, ensure:

### 1. Install Missing Package
```bash
pip install tenacity
```

### 2. Set OpenAI API Key
Create or edit `.env` file:
```bash
OPENAI_API_KEY=sk-your-actual-api-key-here
```

Or export in shell:
```bash
export OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 3. Verify Setup
```bash
# Test single task first
python main.py launch --task-id 82e2fac_1

# Then try batch
python main.py batch-evaluate --split train --limit 2
```

## Status

✅ **FIXED** - Batch evaluation now correctly starts agents with proper port configuration.

## Files Modified

- `src/evaluator/batch_evaluator.py`: Updated agent startup commands


