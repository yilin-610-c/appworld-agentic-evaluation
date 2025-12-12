#!/usr/bin/env python3
"""
Test script to verify trajectory metrics calculation.

This script runs a short MCP evaluation and checks if all metrics are properly collected.
"""

import sys
import os
import json
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.evaluator.trajectory_analyzer import analyze_mcp_trajectory, print_trajectory_analysis


def create_test_log():
    """Create a test JSONL log file with sample tool calls."""
    test_log_file = "/tmp/test_mcp_tool_calls.jsonl"
    
    # Sample log entries
    log_entries = [
        {
            "timestamp": "2024-01-15T10:00:00.000000",
            "tool_name": "spotify__login",
            "arguments": {"username": "test@example.com", "password": "pass123"},
            "success": True,
            "duration_ms": 120.5,
            "result": {"response": {"access_token": "token123"}}
        },
        {
            "timestamp": "2024-01-15T10:00:01.000000",
            "tool_name": "spotify__show_playlist_library",
            "arguments": {"access_token": "token123"},
            "success": False,
            "duration_ms": 95.2,
            "result": {"response": {"message": "Invalid token", "is_error": True}}
        },
        {
            "timestamp": "2024-01-15T10:00:02.000000",
            "tool_name": "spotify__show_playlist_library",
            "arguments": {"access_token": "token123"},
            "success": True,
            "duration_ms": 105.8,
            "result": {"response": [{"playlist_id": 1, "title": "My Playlist"}]}
        },
        {
            "timestamp": "2024-01-15T10:00:03.000000",
            "tool_name": "spotify__show_playlist_library",
            "arguments": {"access_token": "token123", "offset": 10},
            "success": True,
            "duration_ms": 98.3,
            "result": {"response": [{"playlist_id": 2, "title": "Another Playlist"}]}
        },
        {
            "timestamp": "2024-01-15T10:00:04.000000",
            "tool_name": "spotify__show_playlist",
            "arguments": {"playlist_id": 1, "access_token": "token123"},
            "success": True,
            "duration_ms": 110.7,
            "result": {"response": {"songs": [{"song_id": 101, "title": "Song 1"}]}}
        },
        {
            "timestamp": "2024-01-15T10:00:05.000000",
            "tool_name": "spotify__search_songs",
            "arguments": {"query": "rock", "access_token": "token123"},
            "success": True,
            "duration_ms": 130.2,
            "result": {"response": [{"song_id": 201, "title": "Rock Song"}]}
        },
        {
            "timestamp": "2024-01-15T10:00:06.000000",
            "tool_name": "spotify__search_songs",
            "arguments": {"query": "jazz", "access_token": "token123"},
            "success": True,
            "duration_ms": 125.5,
            "result": {"response": [{"song_id": 202, "title": "Jazz Song"}]}
        },
        {
            "timestamp": "2024-01-15T10:00:07.000000",
            "tool_name": "supervisor__complete_task",
            "arguments": {"answer": "Song 1"},
            "success": True,
            "duration_ms": 50.1,
            "result": {"response": {"message": "Task completed"}}
        }
    ]
    
    # Write to JSONL file
    with open(test_log_file, 'w') as f:
        for entry in log_entries:
            f.write(json.dumps(entry) + "\n")
    
    return test_log_file


def verify_metrics(metrics):
    """Verify that all expected metrics are present and valid."""
    print("\n" + "="*80)
    print("VERIFICATION RESULTS")
    print("="*80)
    
    checks_passed = 0
    checks_total = 0
    
    # Check basic efficiency metrics
    basic_metrics = ["total_api_calls", "total_duration_seconds", "calls_per_minute", "avg_duration_ms"]
    for metric in basic_metrics:
        checks_total += 1
        if metric in metrics:
            print(f"✓ {metric}: {metrics[metric]}")
            checks_passed += 1
        else:
            print(f"✗ {metric}: MISSING")
    
    # Check error metrics
    error_metrics = ["error_rate", "failed_calls", "successful_calls", "retry_count"]
    for metric in error_metrics:
        checks_total += 1
        if metric in metrics:
            print(f"✓ {metric}: {metrics[metric]}")
            checks_passed += 1
        else:
            print(f"✗ {metric}: MISSING")
    
    # Check behavioral metrics
    behavioral_metrics = ["pagination_sequences", "unique_tools", "unique_tool_list"]
    for metric in behavioral_metrics:
        checks_total += 1
        if metric in metrics:
            if metric == "unique_tool_list":
                print(f"✓ {metric}: {len(metrics[metric])} tools")
            else:
                print(f"✓ {metric}: {metrics[metric]}")
            checks_passed += 1
        else:
            print(f"✗ {metric}: MISSING")
    
    print("\n" + "="*80)
    print(f"VERIFICATION SUMMARY: {checks_passed}/{checks_total} checks passed")
    print("="*80)
    
    # Verify specific values for test data
    print("\n" + "="*80)
    print("VALIDATING COMPUTED VALUES")
    print("="*80)
    
    validations_passed = 0
    validations_total = 0
    
    # Expected values based on test data
    expected = {
        "total_api_calls": 8,
        "error_rate": 0.125,  # 1 failed out of 8
        "retry_count": 1,  # One retry: spotify__show_playlist_library
        "pagination_sequences": 2,  # 3x spotify__show_playlist_library (1 seq) + 2x spotify__search_songs (1 seq) = 2 sequences
        "unique_tools": 5  # login, show_playlist_library, show_playlist, search_songs, complete_task
    }
    
    for key, expected_value in expected.items():
        validations_total += 1
        actual_value = metrics.get(key)
        if actual_value == expected_value:
            print(f"✓ {key}: {actual_value} (expected: {expected_value})")
            validations_passed += 1
        else:
            print(f"✗ {key}: {actual_value} (expected: {expected_value})")
    
    print("\n" + "="*80)
    print(f"VALIDATION SUMMARY: {validations_passed}/{validations_total} validations passed")
    print("="*80)
    
    return checks_passed == checks_total and validations_passed == validations_total


def main():
    print("="*80)
    print("TRAJECTORY ANALYZER TEST")
    print("="*80)
    
    # Create test log
    print("\n1. Creating test log file...")
    test_log_file = create_test_log()
    print(f"   ✓ Created: {test_log_file}")
    
    # Run analysis
    print("\n2. Running trajectory analysis...")
    try:
        metrics = analyze_mcp_trajectory(test_log_file)
        print("   ✓ Analysis completed successfully")
    except Exception as e:
        print(f"   ✗ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Print results
    print("\n3. Printing analysis results...")
    print_trajectory_analysis(metrics)
    
    # Verify metrics
    print("\n4. Verifying metrics...")
    all_passed = verify_metrics(metrics)
    
    # Cleanup
    print("\n5. Cleaning up...")
    os.remove(test_log_file)
    print(f"   ✓ Removed: {test_log_file}")
    
    # Final result
    print("\n" + "="*80)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("="*80)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

