"""
Trajectory Analysis Module for AppWorld Green Agent

This module provides functions to analyze the execution trajectory of the White Agent
by reading tool call logs and computing various metrics related to efficiency, 
error rates, and behavioral patterns.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any


def analyze_mcp_trajectory(log_file_path: str) -> Dict[str, Any]:
    """
    Analyze the MCP tool call trajectory from a JSONL log file.
    
    This function computes three dimensions of metrics:
    
    1. Basic Efficiency Metrics:
       - total_api_calls: Total number of API/tool calls
       - total_duration_seconds: Time span from first to last call
       - calls_per_minute: Throughput (calls / minute)
       - avg_duration_ms: Average response time per call
    
    2. Error and Stability Metrics:
       - error_rate: Percentage of failed calls
       - retry_count: Number of times the agent retried after failure (self-correction)
    
    3. Behavioral Pattern Metrics:
       - pagination_sequences: Number of continuous browsing/search sequences
       - unique_tools: Number of distinct tools used
    
    Args:
        log_file_path: Path to the JSONL log file containing tool call records
        
    Returns:
        Dictionary containing all computed metrics
        
    Raises:
        FileNotFoundError: If log file doesn't exist
        ValueError: If log file is empty or malformed
    """
    
    if not os.path.exists(log_file_path):
        raise FileNotFoundError(f"Log file not found: {log_file_path}")
    
    # Read all log entries
    logs = []
    with open(log_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Warning: Skipping malformed log line: {line[:50]}... ({e})")
                    continue
    
    if not logs:
        raise ValueError(f"Log file is empty or contains no valid entries: {log_file_path}")
    
    # Initialize metrics
    metrics = {}
    
    # ============================================================================
    # 1. BASIC EFFICIENCY METRICS
    # ============================================================================
    
    # Total API calls
    total_api_calls = len(logs)
    metrics["total_api_calls"] = total_api_calls
    
    # Total duration (time span from first to last call)
    try:
        first_timestamp = datetime.fromisoformat(logs[0]["timestamp"])
        last_timestamp = datetime.fromisoformat(logs[-1]["timestamp"])
        total_duration_seconds = (last_timestamp - first_timestamp).total_seconds()
        metrics["total_duration_seconds"] = round(total_duration_seconds, 2)
    except (KeyError, ValueError) as e:
        print(f"Warning: Could not calculate duration: {e}")
        metrics["total_duration_seconds"] = 0.0
        total_duration_seconds = 0.0
    
    # Calls per minute (throughput)
    if total_duration_seconds > 0:
        calls_per_minute = (total_api_calls / total_duration_seconds) * 60
        metrics["calls_per_minute"] = round(calls_per_minute, 2)
    else:
        metrics["calls_per_minute"] = 0.0
    
    # Average duration per call
    durations = [log.get("duration_ms", 0) for log in logs]
    if durations:
        avg_duration_ms = sum(durations) / len(durations)
        metrics["avg_duration_ms"] = round(avg_duration_ms, 2)
    else:
        metrics["avg_duration_ms"] = 0.0
    
    # ============================================================================
    # 2. ERROR AND STABILITY METRICS
    # ============================================================================
    
    # Error rate
    failed_calls = 0
    for log in logs:
        # Check explicit success field
        if log.get("success") == False:
            failed_calls += 1
            continue
        
        # Check for is_error in result.response
        result = log.get("result", {})
        if isinstance(result, dict):
            response = result.get("response", {})
            if isinstance(response, dict) and response.get("is_error") == True:
                failed_calls += 1
    
    error_rate = failed_calls / total_api_calls if total_api_calls > 0 else 0.0
    metrics["error_rate"] = round(error_rate, 3)
    metrics["failed_calls"] = failed_calls
    metrics["successful_calls"] = total_api_calls - failed_calls
    
    # Retry count (self-correction ability)
    # Logic: Find sequences where:
    #   - Call i-1 failed
    #   - Call i succeeded
    #   - Both calls used the same tool
    retry_count = 0
    for i in range(1, len(logs)):
        prev_log = logs[i - 1]
        curr_log = logs[i]
        
        # Check if previous call failed
        prev_failed = prev_log.get("success") == False
        if not prev_failed:
            # Also check is_error in result
            prev_result = prev_log.get("result", {})
            if isinstance(prev_result, dict):
                prev_response = prev_result.get("response", {})
                if isinstance(prev_response, dict):
                    prev_failed = prev_response.get("is_error") == True
        
        # Check if current call succeeded
        curr_success = curr_log.get("success") == True
        if curr_success:
            # Also verify no is_error in result
            curr_result = curr_log.get("result", {})
            if isinstance(curr_result, dict):
                curr_response = curr_result.get("response", {})
                if isinstance(curr_response, dict):
                    curr_success = not curr_response.get("is_error", False)
        
        # Check if same tool
        same_tool = prev_log.get("tool_name") == curr_log.get("tool_name")
        
        if prev_failed and curr_success and same_tool:
            retry_count += 1
    
    metrics["retry_count"] = retry_count
    
    # ============================================================================
    # 3. BEHAVIORAL PATTERN METRICS
    # ============================================================================
    
    # Pagination/browsing sequences
    # Detect continuous calls to "library", "list", or "search" tools
    # Use word boundaries to avoid false matches (e.g., "playlist" shouldn't match "list")
    pagination_keywords = ["_library", "_list", "_search"]
    pagination_sequences = 0
    consecutive_browsing = 0
    prev_was_browsing = False
    
    for log in logs:
        tool_name = log.get("tool_name", "").lower()
        # Check if tool name contains any of the keywords (with underscore prefix for precision)
        is_browsing = any(keyword in tool_name for keyword in pagination_keywords)
        
        if is_browsing:
            if prev_was_browsing:
                consecutive_browsing += 1
            else:
                consecutive_browsing = 1
        else:
            # End of browsing sequence
            if consecutive_browsing >= 2:
                pagination_sequences += 1
            consecutive_browsing = 0
        
        prev_was_browsing = is_browsing
    
    # Check for trailing sequence
    if consecutive_browsing >= 2:
        pagination_sequences += 1
    
    metrics["pagination_sequences"] = pagination_sequences
    
    # Tool diversity (unique tools used)
    unique_tools = set(log.get("tool_name") for log in logs if log.get("tool_name"))
    metrics["unique_tools"] = len(unique_tools)
    metrics["unique_tool_list"] = sorted(list(unique_tools))
    
    return metrics


def print_trajectory_analysis(metrics: Dict[str, Any]) -> None:
    """
    Pretty-print trajectory analysis metrics.
    
    Args:
        metrics: Dictionary returned by analyze_mcp_trajectory()
    """
    print("=" * 80)
    print("TRAJECTORY ANALYSIS RESULTS")
    print("=" * 80)
    print()
    
    print("📊 BASIC EFFICIENCY METRICS")
    print("-" * 80)
    print(f"  Total API Calls:        {metrics.get('total_api_calls', 0)}")
    print(f"  Total Duration:         {metrics.get('total_duration_seconds', 0):.2f} seconds")
    print(f"  Throughput:             {metrics.get('calls_per_minute', 0):.2f} calls/min")
    print(f"  Average Latency:        {metrics.get('avg_duration_ms', 0):.2f} ms")
    print()
    
    print("⚠️  ERROR AND STABILITY METRICS")
    print("-" * 80)
    print(f"  Successful Calls:       {metrics.get('successful_calls', 0)}")
    print(f"  Failed Calls:           {metrics.get('failed_calls', 0)}")
    print(f"  Error Rate:             {metrics.get('error_rate', 0):.1%}")
    print(f"  Retry Count:            {metrics.get('retry_count', 0)} (self-correction)")
    print()
    
    print("🔍 BEHAVIORAL PATTERN METRICS")
    print("-" * 80)
    print(f"  Pagination Sequences:   {metrics.get('pagination_sequences', 0)}")
    print(f"  Unique Tools Used:      {metrics.get('unique_tools', 0)}")
    print()
    
    if metrics.get('unique_tool_list'):
        print("🔧 TOOLS USED:")
        print("-" * 80)
        for i, tool in enumerate(metrics['unique_tool_list'], 1):
            print(f"  {i}. {tool}")
        print()
    
    print("=" * 80)


if __name__ == "__main__":
    """
    Test the trajectory analyzer with a sample log file.
    """
    import sys
    
    if len(sys.argv) > 1:
        log_file = sys.argv[1]
        try:
            metrics = analyze_mcp_trajectory(log_file)
            print_trajectory_analysis(metrics)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        print("Usage: python trajectory_analyzer.py <log_file.jsonl>")
        print()
        print("This module analyzes MCP tool call trajectories.")
        sys.exit(1)

