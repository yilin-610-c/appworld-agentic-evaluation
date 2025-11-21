"""Batch evaluator for running multiple AppWorld tasks."""

import asyncio
import json
import time
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from pathlib import Path
import subprocess
import signal
import os


@dataclass
class EvaluationResult:
    """Result of evaluating a single task."""
    task_id: str
    success: bool
    steps: int
    time: float
    score: float
    passes: int
    fails: int
    total: int
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class EvaluationSummary:
    """Summary statistics for batch evaluation."""
    total_tasks: int
    successful: int
    failed: int
    success_rate: float
    avg_steps: float
    avg_time: float
    avg_score: float
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class BatchEvaluator:
    """Manages batch evaluation of multiple tasks."""
    
    def __init__(
        self,
        green_port: int = 9001,
        white_port: int = 9002,
        parallel: int = 1,
        verbose: bool = True
    ):
        """
        Initialize batch evaluator.
        
        Args:
            green_port: Base port for green agent
            white_port: Base port for white agent
            parallel: Number of parallel evaluations (1 = sequential)
            verbose: Print detailed progress
        """
        self.green_port = green_port
        self.white_port = white_port
        self.parallel = parallel
        self.verbose = verbose
        self.results: List[EvaluationResult] = []
        
    async def evaluate_task(
        self,
        task_id: str,
        port_offset: int = 0
    ) -> EvaluationResult:
        """
        Evaluate a single task.
        
        Args:
            task_id: AppWorld task ID
            port_offset: Port offset for parallel execution
            
        Returns:
            Evaluation result
        """
        green_port = self.green_port + port_offset * 2
        white_port = self.white_port + port_offset * 2
        
        if self.verbose:
            print(f"\n{'='*80}")
            print(f"Evaluating task: {task_id}")
            print(f"Green agent port: {green_port}, White agent port: {white_port}")
            print(f"{'='*80}")
        
        green_proc = None
        white_proc = None
        
        try:
            start_time = time.time()
            
            # Start green agent using CLI command
            green_env = os.environ.copy()
            green_env['PYTHONUNBUFFERED'] = '1'
            green_proc = subprocess.Popen(
                ['python', '-c',
                 f'from src.green_agent import start_green_agent; start_green_agent(port={green_port})'],
                stdout=subprocess.PIPE if not self.verbose else None,
                stderr=subprocess.PIPE if not self.verbose else None,
                env=green_env,
                preexec_fn=os.setsid  # Create process group for clean shutdown
            )
            
            # Start white agent using CLI command
            white_env = os.environ.copy()
            white_env['PYTHONUNBUFFERED'] = '1'
            white_proc = subprocess.Popen(
                ['python', '-c',
                 f'from src.white_agent import start_white_agent; start_white_agent(port={white_port})'],
                stdout=subprocess.PIPE if not self.verbose else None,
                stderr=subprocess.PIPE if not self.verbose else None,
                env=white_env,
                preexec_fn=os.setsid
            )
            
            # Wait for agents to start
            await asyncio.sleep(3)
            
            # Import here to avoid circular imports
            from src.util.a2a_client import send_message
            
            # Construct task message
            task_text = f"""Your task is to test the agent located at:
<white_agent_url>
http://localhost:{white_port}
</white_agent_url>

Using AppWorld task:
<task_id>
{task_id}
</task_id>
"""
            
            # Send to green agent
            green_url = f"http://localhost:{green_port}"
            response = await send_message(green_url, task_text)
            
            elapsed = time.time() - start_time
            
            # Parse response to extract metrics
            response_text = response.result.parts[0].root.text
            
            # Extract metrics from response
            result = self._parse_response(task_id, response_text, elapsed)
            
            if self.verbose:
                print(f"\n✓ Task {task_id} completed in {elapsed:.1f}s")
                print(f"  Success: {'✅' if result.success else '❌'}")
                print(f"  Steps: {result.steps}, Score: {result.score}")
            
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            if self.verbose:
                print(f"\n✗ Task {task_id} failed: {e}")
            
            return EvaluationResult(
                task_id=task_id,
                success=False,
                steps=0,
                time=elapsed,
                score=0.0,
                passes=0,
                fails=0,
                total=0,
                error=str(e)
            )
            
        finally:
            # Clean up processes
            for proc in [green_proc, white_proc]:
                if proc:
                    try:
                        # Kill entire process group
                        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                        proc.wait(timeout=5)
                    except:
                        try:
                            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                        except:
                            pass
    
    def _parse_response(
        self,
        task_id: str,
        response_text: str,
        elapsed: float
    ) -> EvaluationResult:
        """Parse green agent response to extract metrics."""
        import re
        
        # Extract success status
        success = '✅' in response_text or 'success": True' in response_text or 'success": true' in response_text
        
        # Extract metrics using regex
        steps_match = re.search(r'"steps":\s*(\d+)', response_text)
        score_match = re.search(r'"score":\s*([0-9.]+)', response_text)
        passes_match = re.search(r'"passes":\s*(\d+)', response_text)
        fails_match = re.search(r'"fails":\s*(\d+)', response_text)
        total_match = re.search(r'"total":\s*(\d+)', response_text)
        
        return EvaluationResult(
            task_id=task_id,
            success=success,
            steps=int(steps_match.group(1)) if steps_match else 0,
            time=elapsed,
            score=float(score_match.group(1)) if score_match else 0.0,
            passes=int(passes_match.group(1)) if passes_match else 0,
            fails=int(fails_match.group(1)) if fails_match else 0,
            total=int(total_match.group(1)) if total_match else 0,
            error=None if success else "Task failed"
        )
    
    async def evaluate_batch(
        self,
        task_ids: List[str]
    ) -> List[EvaluationResult]:
        """
        Evaluate multiple tasks.
        
        Args:
            task_ids: List of task IDs to evaluate
            
        Returns:
            List of evaluation results
        """
        if self.parallel == 1:
            # Sequential execution
            results = []
            for task_id in task_ids:
                result = await self.evaluate_task(task_id, port_offset=0)
                results.append(result)
                self.results.append(result)
            return results
        else:
            # Parallel execution (external parallelism)
            tasks = []
            for i, task_id in enumerate(task_ids):
                # Limit to self.parallel concurrent tasks
                if i > 0 and i % self.parallel == 0:
                    # Wait for previous batch to complete
                    batch_results = await asyncio.gather(*tasks)
                    self.results.extend(batch_results)
                    tasks = []
                
                tasks.append(self.evaluate_task(task_id, port_offset=i % self.parallel))
            
            # Wait for remaining tasks
            if tasks:
                batch_results = await asyncio.gather(*tasks)
                self.results.extend(batch_results)
            
            return self.results
    
    def generate_summary(self) -> EvaluationSummary:
        """Generate summary statistics from results."""
        if not self.results:
            return EvaluationSummary(
                total_tasks=0,
                successful=0,
                failed=0,
                success_rate=0.0,
                avg_steps=0.0,
                avg_time=0.0,
                avg_score=0.0,
                timestamp=datetime.now().isoformat()
            )
        
        successful = sum(1 for r in self.results if r.success)
        failed = len(self.results) - successful
        
        return EvaluationSummary(
            total_tasks=len(self.results),
            successful=successful,
            failed=failed,
            success_rate=successful / len(self.results) if self.results else 0.0,
            avg_steps=sum(r.steps for r in self.results) / len(self.results),
            avg_time=sum(r.time for r in self.results) / len(self.results),
            avg_score=sum(r.score for r in self.results) / len(self.results),
            timestamp=datetime.now().isoformat()
        )
    
    def save_results(self, output_path: str, format: str = "json"):
        """
        Save evaluation results to file.
        
        Args:
            output_path: Path to output file
            format: Output format ('json' or 'csv')
        """
        summary = self.generate_summary()
        
        if format == "json":
            output = {
                "summary": summary.to_dict(),
                "tasks": [r.to_dict() for r in self.results]
            }
            
            with open(output_path, 'w') as f:
                json.dump(output, f, indent=2)
        
        elif format == "csv":
            import csv
            
            with open(output_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'task_id', 'success', 'steps', 'time', 'score',
                    'passes', 'fails', 'total', 'error'
                ])
                writer.writeheader()
                for result in self.results:
                    writer.writerow(result.to_dict())
        
        if self.verbose:
            print(f"\n{'='*80}")
            print(f"Results saved to: {output_path}")
            print(f"{'='*80}")
    
    def print_summary(self):
        """Print summary statistics to console."""
        summary = self.generate_summary()
        
        print(f"\n{'='*80}")
        print("EVALUATION SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tasks:    {summary.total_tasks}")
        print(f"Successful:     {summary.successful} ({summary.success_rate*100:.1f}%)")
        print(f"Failed:         {summary.failed}")
        print(f"Avg Steps:      {summary.avg_steps:.1f}")
        print(f"Avg Time:       {summary.avg_time:.1f}s")
        print(f"Avg Score:      {summary.avg_score:.2f}")
        print(f"Timestamp:      {summary.timestamp}")
        print(f"{'='*80}\n")
        
        # Print per-task details
        print("TASK DETAILS:")
        print(f"{'Task ID':<15} {'Success':<10} {'Steps':<8} {'Time':<10} {'Score':<8}")
        print(f"{'-'*15} {'-'*10} {'-'*8} {'-'*10} {'-'*8}")
        for result in self.results:
            status = '✅' if result.success else '❌'
            print(f"{result.task_id:<15} {status:<10} {result.steps:<8} {result.time:<10.1f} {result.score:<8.2f}")
        print()

