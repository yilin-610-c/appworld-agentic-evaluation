"""CLI entry point for appworld-green-agent."""

import typer
import asyncio
import os
from pathlib import Path
from typing import Optional, List

from src.green_agent import start_green_agent
from src.white_agent import start_white_agent
from src.launcher import launch_evaluation
from src.evaluator import BatchEvaluator

app = typer.Typer(
    help="Agentified AppWorld - Standardized agent assessment framework"
)


@app.command()
def green(
    host: str = typer.Option(
        "localhost",
        "--host",
        help="Host to bind the green agent to"
    ),
    port: int = typer.Option(
        9001,
        "--port",
        help="Port to run the green agent on"
    )
):
    """Start the green agent (assessment manager)."""
    start_green_agent(host=host, port=port)


@app.command()
def white():
    """Start the white agent (target being tested)."""
    start_white_agent()


@app.command()
def launch(
    task_id: str = typer.Option(
        "82e2fac_1", 
        help="AppWorld task ID to evaluate"
    )
):
    """Launch the complete evaluation workflow."""
    asyncio.run(launch_evaluation(task_id=task_id))


@app.command()
def list_tasks():
    """List available AppWorld tasks."""
    # Set APPWORLD_ROOT (not APPWORLD_DATA_ROOT!) BEFORE importing appworld
    # APPWORLD_ROOT should point to the project root directory (containing data/)
    appworld_root = '/home/lyl610/green1112/appworld'
    if not os.path.exists(appworld_root):
        # Try relative path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        appworld_root = os.path.join(script_dir, '..', 'appworld')
    
    # Verify data directory exists
    appworld_data = os.path.join(appworld_root, 'data')
    if not os.path.exists(appworld_data):
        print(f"Error: AppWorld data directory not found at {appworld_data}")
        print(f"Please ensure AppWorld is installed and data is downloaded.")
        return
    
    os.environ['APPWORLD_ROOT'] = appworld_root  # Use APPWORLD_ROOT, not APPWORLD_DATA_ROOT!
    print(f"Using AppWorld root: {appworld_root}")
    print(f"Data directory: {appworld_data}\n")
    
    # Now import after setting environment
    from appworld import load_task_ids
    
    for split in ["train", "dev", "test_normal", "test_challenge"]:
        try:
            task_ids = load_task_ids(split)
            print(f"\n{split}: {len(task_ids)} tasks")
            print(f"  First 5: {task_ids[:5]}")
        except Exception as e:
            print(f"\n{split}: Error loading - {e}")


@app.command()
def batch_evaluate(
    task_ids: Optional[str] = typer.Option(
        None,
        "--task-ids",
        help="Comma-separated list of task IDs to evaluate"
    ),
    task_file: Optional[Path] = typer.Option(
        None,
        "--task-file",
        help="Path to file containing task IDs (one per line)"
    ),
    split: Optional[str] = typer.Option(
        None,
        "--split",
        help="Load tasks from AppWorld split (train/dev/test_normal/test_challenge)"
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        help="Maximum number of tasks to evaluate"
    ),
    output: str = typer.Option(
        "batch_results.json",
        "--output",
        "-o",
        help="Output file path"
    ),
    format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format (json or csv)"
    ),
    parallel: int = typer.Option(
        1,
        "--parallel",
        "-p",
        help="Number of parallel evaluations (1 = sequential)"
    ),
    green_port: int = typer.Option(
        9001,
        "--green-port",
        help="Base port for green agent"
    ),
    white_port: int = typer.Option(
        9002,
        "--white-port",
        help="Base port for white agent"
    ),
    verbose: bool = typer.Option(
        True,
        "--verbose/--quiet",
        help="Print detailed progress"
    )
):
    """
    Evaluate multiple AppWorld tasks in batch.
    
    Examples:
        # Evaluate specific tasks
        python main.py batch-evaluate --task-ids 82e2fac_1,82e2fac_2,82e2fac_3
        
        # Load from file
        python main.py batch-evaluate --task-file tasks.txt
        
        # Evaluate first 10 from train split
        python main.py batch-evaluate --split train --limit 10
        
        # Run 3 tasks in parallel
        python main.py batch-evaluate --task-ids ... --parallel 3
        
        # Save as CSV
        python main.py batch-evaluate --task-ids ... --format csv --output results.csv
    """
    # Determine task list
    task_list = []
    
    if task_ids:
        task_list = [t.strip() for t in task_ids.split(',')]
    elif task_file:
        with open(task_file, 'r') as f:
            task_list = [line.strip() for line in f if line.strip()]
    elif split:
        # Load from AppWorld split
        appworld_root = '/home/lyl610/green1112/appworld'
        if not os.path.exists(appworld_root):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            appworld_root = os.path.join(script_dir, '..', 'appworld')
        
        os.environ['APPWORLD_ROOT'] = appworld_root
        
        from appworld import load_task_ids
        task_list = load_task_ids(split)
        print(f"Loaded {len(task_list)} tasks from {split} split")
    else:
        print("Error: Must specify one of --task-ids, --task-file, or --split")
        return
    
    # Apply limit
    if limit and limit < len(task_list):
        task_list = task_list[:limit]
        print(f"Limited to first {limit} tasks")
    
    if not task_list:
        print("Error: No tasks to evaluate")
        return
    
    print(f"\n{'='*80}")
    print(f"BATCH EVALUATION")
    print(f"{'='*80}")
    print(f"Tasks to evaluate: {len(task_list)}")
    print(f"Parallel workers:  {parallel}")
    print(f"Output file:       {output}")
    print(f"Output format:     {format}")
    print(f"{'='*80}\n")
    
    # Create evaluator
    evaluator = BatchEvaluator(
        green_port=green_port,
        white_port=white_port,
        parallel=parallel,
        verbose=verbose
    )
    
    # Run evaluation
    try:
        asyncio.run(evaluator.evaluate_batch(task_list))
        
        # Print summary
        evaluator.print_summary()
        
        # Save results
        evaluator.save_results(output, format=format)
        
        print(f"✓ Batch evaluation complete!")
        
    except KeyboardInterrupt:
        print("\n\nEvaluation interrupted by user.")
        if evaluator.results:
            print("Saving partial results...")
            evaluator.print_summary()
            evaluator.save_results(output, format=format)
    except Exception as e:
        print(f"\n✗ Batch evaluation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    app()

