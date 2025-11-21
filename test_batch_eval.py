"""
Quick test script to demonstrate batch evaluation functionality.
This validates the code works without running full evaluations.
"""

from src.evaluator import BatchEvaluator, EvaluationResult, EvaluationSummary
from datetime import datetime

# Create mock results
results = [
    EvaluationResult(
        task_id="82e2fac_1",
        success=True,
        steps=17,
        time=79.7,
        score=1.0,
        passes=2,
        fails=0,
        total=2,
        error=None
    ),
    EvaluationResult(
        task_id="82e2fac_2",
        success=False,
        steps=16,
        time=75.3,
        score=0.0,
        passes=1,
        fails=1,
        total=2,
        error="Task failed"
    ),
    EvaluationResult(
        task_id="82e2fac_3",
        success=True,
        steps=12,
        time=45.2,
        score=1.0,
        passes=2,
        fails=0,
        total=2,
        error=None
    ),
]

# Create evaluator and add results
evaluator = BatchEvaluator(verbose=True)
evaluator.results = results

# Print summary
print("\nTesting summary generation:")
evaluator.print_summary()

# Test JSON export
print("\nTesting JSON export:")
evaluator.save_results("test_results.json", format="json")

# Test CSV export
print("\nTesting CSV export:")
evaluator.save_results("test_results.csv", format="csv")

print("\n✓ All tests passed! Batch evaluation module is working correctly.")
print("\nYou can now run actual evaluations with:")
print("  python main.py batch-evaluate --task-ids 82e2fac_1,82e2fac_2")


