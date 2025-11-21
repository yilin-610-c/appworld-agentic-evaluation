# Quick Start: Batch Evaluation

## 🚀 Ready to Use!

The batch evaluation feature is now fully implemented and tested. Here's how to get started:

## 1. Simple Test (2 tasks)

```bash
# Evaluate 2 specific tasks
python main.py batch-evaluate --task-ids 82e2fac_1,82e2fac_2

# This will:
# - Run each task sequentially
# - Print progress and results
# - Save results to batch_results.json
```

## 2. Batch from Train Split (10 tasks)

```bash
# Evaluate first 10 tasks from train split
python main.py batch-evaluate --split train --limit 10

# Faster with parallel execution (3 at a time):
python main.py batch-evaluate --split train --limit 10 --parallel 3
```

## 3. Using a Task File

Create `my_tasks.txt`:
```
82e2fac_1
82e2fac_2
82e2fac_3
```

Run:
```bash
python main.py batch-evaluate --task-file my_tasks.txt
```

## 4. Export to CSV for Analysis

```bash
python main.py batch-evaluate \
  --split train \
  --limit 20 \
  --format csv \
  --output train_results.csv
```

Then open `train_results.csv` in Excel/Google Sheets for analysis.

## Expected Output

```
================================================================================
BATCH EVALUATION
================================================================================
Tasks to evaluate: 3
Parallel workers:  1
Output file:       batch_results.json
Output format:     json
================================================================================

================================================================================
Evaluating task: 82e2fac_1
Green agent port: 9001, White agent port: 9002
================================================================================
...
✓ Task 82e2fac_1 completed in 79.5s
  Success: ✅
  Steps: 17, Score: 1.0

...

================================================================================
EVALUATION SUMMARY
================================================================================
Total Tasks:    3
Successful:     2 (66.7%)
Failed:         1
Avg Steps:      15.0
Avg Time:       66.7s
Avg Score:      0.67
Timestamp:      2025-11-13T...
================================================================================

TASK DETAILS:
Task ID         Success    Steps    Time       Score   
--------------- ---------- -------- ---------- --------
82e2fac_1       ✅          17       79.7       1.00    
82e2fac_2       ❌          16       75.3       0.00    
82e2fac_3       ✅          12       45.2       1.00    

================================================================================
Results saved to: batch_results.json
================================================================================
✓ Batch evaluation complete!
```

## Tips for Success

### Start Small
```bash
# Test with 2-3 tasks first
python main.py batch-evaluate --split train --limit 3
```

### Use Parallel for Speed
```bash
# 4 parallel workers for 20 tasks
python main.py batch-evaluate --split train --limit 20 --parallel 4
```

### Watch for Rate Limits
If you hit OpenAI rate limits:
```bash
# Run sequentially (slower but safer)
python main.py batch-evaluate --split train --limit 10 --parallel 1
```

### Interrupt Safely
- Press `Ctrl+C` to stop
- Partial results will be automatically saved

## What to Do Next

1. **Analyze Results**: Open the JSON/CSV file to see detailed metrics
2. **Identify Patterns**: Which tasks succeed/fail?
3. **Improve White Agent**: Use insights to enhance prompts/logic
4. **Calculate Pass@K**: Run same tasks multiple times
5. **Integrate AgentBeats**: Follow blog-3 for platform integration

## Common Commands Reference

```bash
# List available tasks
python main.py list-tasks

# Single task evaluation (original command)
python main.py launch --task-id 82e2fac_1

# Batch: specific tasks
python main.py batch-evaluate --task-ids ID1,ID2,ID3

# Batch: from file
python main.py batch-evaluate --task-file tasks.txt

# Batch: from split
python main.py batch-evaluate --split train --limit 10

# Batch: parallel execution
python main.py batch-evaluate --split train --limit 20 --parallel 4

# Batch: CSV output
python main.py batch-evaluate --task-ids ... --format csv -o results.csv

# Batch: quiet mode
python main.py batch-evaluate --task-ids ... --quiet
```

## Need Help?

- Full guide: See `BATCH_EVALUATION.md`
- Implementation details: See `BATCH_IMPLEMENTATION.md`
- CLI help: Run `python main.py batch-evaluate --help`

---

Happy evaluating! 🎉


