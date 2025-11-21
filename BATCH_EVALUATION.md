# Batch Evaluation Guide

## Overview

The batch evaluation feature allows you to evaluate multiple AppWorld tasks efficiently, with support for parallel execution and comprehensive result reporting.

## Quick Start

### 1. Evaluate Specific Tasks

```bash
python main.py batch-evaluate --task-ids 82e2fac_1,82e2fac_2,82e2fac_3
```

### 2. Load Tasks from File

Create a file `tasks.txt` with one task ID per line:
```
82e2fac_1
82e2fac_2
82e2fac_3
```

Then run:
```bash
python main.py batch-evaluate --task-file tasks.txt
```

### 3. Evaluate from AppWorld Split

```bash
# Evaluate first 10 tasks from train split
python main.py batch-evaluate --split train --limit 10

# Evaluate all tasks from dev split
python main.py batch-evaluate --split dev
```

## Advanced Usage

### Parallel Execution

Run multiple tasks in parallel for faster evaluation:

```bash
# Run 3 tasks in parallel
python main.py batch-evaluate --task-ids 82e2fac_1,82e2fac_2,82e2fac_3,82e2fac_4,82e2fac_5 --parallel 3
```

**Note**: Parallel execution uses external parallelism - each task runs in its own agent instances with separate ports.

### Output Formats

#### JSON (default)
```bash
python main.py batch-evaluate --task-ids ... --output results.json
```

Output structure:
```json
{
  "summary": {
    "total_tasks": 10,
    "successful": 7,
    "failed": 3,
    "success_rate": 0.7,
    "avg_steps": 12.3,
    "avg_time": 45.2,
    "avg_score": 0.85,
    "timestamp": "2025-11-13T..."
  },
  "tasks": [
    {
      "task_id": "82e2fac_1",
      "success": true,
      "steps": 15,
      "time": 52.3,
      "score": 1.0,
      "passes": 2,
      "fails": 0,
      "total": 2,
      "error": null
    },
    ...
  ]
}
```

#### CSV
```bash
python main.py batch-evaluate --task-ids ... --format csv --output results.csv
```

### Custom Ports

If you need to avoid port conflicts:

```bash
python main.py batch-evaluate --task-ids ... --green-port 10001 --white-port 10002
```

### Quiet Mode

Suppress detailed progress output:

```bash
python main.py batch-evaluate --task-ids ... --quiet
```

## Output Explanation

### Summary Metrics

- **total_tasks**: Number of tasks evaluated
- **successful**: Number of tasks where the agent succeeded
- **failed**: Number of tasks where the agent failed
- **success_rate**: Percentage of successful tasks (pass@1)
- **avg_steps**: Average number of interaction steps
- **avg_time**: Average time per task (in seconds)
- **avg_score**: Average AppWorld evaluation score
- **timestamp**: When the evaluation completed

### Per-Task Results

- **task_id**: AppWorld task identifier
- **success**: Whether the task was completed successfully
- **steps**: Number of interaction steps taken
- **time**: Time taken (in seconds)
- **score**: AppWorld evaluation score (0.0 to 1.0)
- **passes**: Number of test cases passed
- **fails**: Number of test cases failed
- **total**: Total number of test cases
- **error**: Error message (if any)

## Examples

### Evaluate 5 tasks sequentially
```bash
python main.py batch-evaluate \
  --task-ids 82e2fac_1,82e2fac_2,82e2fac_3,82e2fac_4,82e2fac_5 \
  --output my_results.json
```

### Evaluate 20 tasks in parallel (4 at a time)
```bash
python main.py batch-evaluate \
  --split train \
  --limit 20 \
  --parallel 4 \
  --output train_20_results.json
```

### Quick test with 3 tasks
```bash
python main.py batch-evaluate \
  --split train \
  --limit 3 \
  --output quick_test.json
```

## Tips

1. **Start Small**: Test with 2-3 tasks before running large batches
2. **Use Parallel Wisely**: More parallel workers = more memory and API usage
3. **Monitor Resources**: Each parallel worker runs separate agent processes
4. **Save Results**: Always specify an output file for later analysis
5. **Interrupt Safely**: Press Ctrl+C to stop - partial results will be saved

## Troubleshooting

### Port Already in Use
If you see port conflict errors, either:
- Wait for previous agents to shut down
- Use custom ports: `--green-port 10001 --white-port 10002`

### Out of Memory
If running out of memory:
- Reduce `--parallel` value
- Run fewer tasks at once

### API Rate Limits
If hitting OpenAI rate limits:
- Reduce `--parallel` value to 1
- Add delays between tasks (sequential mode)

## Next Steps

After batch evaluation, you can:
1. Analyze results in the JSON/CSV file
2. Compare performance across different tasks
3. Identify which tasks your agent struggles with
4. Calculate metrics like pass@k by running multiple times


