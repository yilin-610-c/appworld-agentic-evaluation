#!/bin/bash
# AgentBeats Controller startup script for AppWorld Green Agent
# This script is called by the AgentBeats controller to start the green agent

# Redirect all output to stderr so Cloud Run captures it
exec 1>&2

# Find the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

echo "=== Starting AppWorld Green Agent ===" >&2
echo "Script directory: $SCRIPT_DIR" >&2
echo "Project root: $PROJECT_ROOT" >&2
echo "Current working directory: $(pwd)" >&2
echo "Python path: $(which python)" >&2
echo "Python version: $(python --version 2>&1)" >&2

# Change to project root directory
cd "$PROJECT_ROOT" || {
    echo "ERROR: Cannot change to project root: $PROJECT_ROOT" >&2
    exit 1
}

echo "Changed to directory: $(pwd)" >&2

# Read environment variables set by the controller
# $HOST and $AGENT_PORT are automatically configured by AgentBeats controller

# Default values if not set
HOST=${HOST:-"0.0.0.0"}
AGENT_PORT=${AGENT_PORT:-9001}

echo "Host: $HOST" >&2
echo "Port: $AGENT_PORT" >&2

# Check if main.py exists
MAIN_PY="$PROJECT_ROOT/main.py"
if [ ! -f "$MAIN_PY" ]; then
    echo "ERROR: main.py not found at $MAIN_PY" >&2
    echo "Listing directory contents:" >&2
    ls -la "$PROJECT_ROOT" >&2
    exit 1
fi

echo "Found main.py at: $MAIN_PY" >&2

# Check if APPWORLD_ROOT is set
if [ -z "$APPWORLD_ROOT" ]; then
    echo "WARNING: APPWORLD_ROOT not set" >&2
else
    echo "APPWORLD_ROOT: $APPWORLD_ROOT" >&2
    if [ ! -d "$APPWORLD_ROOT" ]; then
        echo "WARNING: APPWORLD_ROOT directory does not exist: $APPWORLD_ROOT" >&2
    fi
fi

# Start the green agent with the specified host and port
echo "Executing: python $MAIN_PY green --host \"$HOST\" --port \"$AGENT_PORT\"" >&2
exec python "$MAIN_PY" green --host "$HOST" --port "$AGENT_PORT"
