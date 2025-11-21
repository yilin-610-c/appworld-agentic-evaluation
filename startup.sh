#!/bin/bash
# Startup script for Cloud Run deployment
# This script downloads AppWorld data from Cloud Storage and starts the AgentBeats controller

set -e  # Exit on error

# Redirect all output to stderr for Cloud Run logging
exec 1>&2

echo "=== Cloud Run Startup Script ===" >&2
echo "Starting at: $(date)" >&2

# Configuration
APPWORLD_DATA_BUCKET="${APPWORLD_DATA_BUCKET:-appworld-green-agent-data}"
APPWORLD_ROOT="/workspace/appworld"
WORKSPACE_DIR="/workspace"

echo "Bucket: gs://${APPWORLD_DATA_BUCKET}" >&2
echo "Target: ${APPWORLD_ROOT}" >&2

# Create workspace directory
mkdir -p "${WORKSPACE_DIR}"
cd "${WORKSPACE_DIR}"

# Check if AppWorld data already exists (for container reuse)
if [ -d "${APPWORLD_ROOT}/data" ]; then
    echo "AppWorld data already exists, skipping download" >&2
    DATA_SIZE=$(du -sh "${APPWORLD_ROOT}/data" 2>/dev/null | cut -f1)
    echo "Data directory size: ${DATA_SIZE}" >&2
else
    echo "Downloading AppWorld data from Cloud Storage..." >&2
    
    # Create appworld directory
    mkdir -p "${APPWORLD_ROOT}"
    
    # Download data from Cloud Storage using Python
    python3 << 'PYTHON_SCRIPT'
import sys
import os
from google.cloud import storage

bucket_name = os.environ.get("APPWORLD_DATA_BUCKET", "appworld-green-agent-data")
target_dir = "/workspace/appworld"

try:
    print(f"Initializing Google Cloud Storage client...", file=sys.stderr, flush=True)
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    print(f"Listing objects in gs://{bucket_name}/data/...", file=sys.stderr, flush=True)
    blobs = list(bucket.list_blobs(prefix="data/"))
    
    if not blobs:
        print(f"ERROR: No objects found in gs://{bucket_name}/data/", file=sys.stderr, flush=True)
        sys.exit(1)
    
    print(f"Found {len(blobs)} objects to download", file=sys.stderr, flush=True)
    
    downloaded = 0
    for blob in blobs:
        # Create local file path
        local_path = os.path.join(target_dir, blob.name)
        
        # Skip if it's a directory marker
        if blob.name.endswith('/'):
            os.makedirs(local_path, exist_ok=True)
            continue
        
        # Create parent directory if needed
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # Download file
        blob.download_to_filename(local_path)
        downloaded += 1
        
        # Print progress every 1000 files
        if downloaded % 1000 == 0:
            print(f"  Downloaded {downloaded}/{len(blobs)} files...", file=sys.stderr, flush=True)
    
    print(f"✓ AppWorld data downloaded successfully ({downloaded} files)", file=sys.stderr, flush=True)
    sys.exit(0)
    
except Exception as e:
    print(f"ERROR: Failed to download AppWorld data: {e}", file=sys.stderr, flush=True)
    print("Please ensure:", file=sys.stderr, flush=True)
    print(f"  1. The bucket exists: {bucket_name}", file=sys.stderr, flush=True)
    print(f"  2. The data is uploaded at gs://{bucket_name}/data/", file=sys.stderr, flush=True)
    print("  3. Cloud Run service account has Storage Object Viewer role", file=sys.stderr, flush=True)
    sys.exit(1)
PYTHON_SCRIPT
    
    if [ $? -ne 0 ]; then
        echo "Continuing without AppWorld data (limited functionality)..." >&2
        # Create minimal directory structure to prevent errors
        mkdir -p "${APPWORLD_ROOT}/data"
    else
        DATA_SIZE=$(du -sh "${APPWORLD_ROOT}/data" 2>/dev/null | cut -f1)
        echo "Data directory size: ${DATA_SIZE}" >&2
    fi
fi

# Set environment variable
export APPWORLD_ROOT="${APPWORLD_ROOT}"
echo "APPWORLD_ROOT set to: ${APPWORLD_ROOT}" >&2

# List downloaded files (for debugging)
echo "AppWorld directory structure:" >&2
ls -la "${APPWORLD_ROOT}" 2>&1 || echo "Cannot list ${APPWORLD_ROOT}" >&2
ls -la "${APPWORLD_ROOT}/data" 2>&1 | head -15 || echo "Cannot list ${APPWORLD_ROOT}/data" >&2

# Configure .ab directory for AgentBeats controller to use writable /tmp
export AB_HOME="/tmp/.ab"
mkdir -p "${AB_HOME}"
echo "AgentBeats controller home: ${AB_HOME}" >&2

# Change to app directory
cd /workspace/app || cd /workspace || {
    echo "ERROR: Cannot find app directory" >&2
    exit 1
}

echo "Working directory: $(pwd)" >&2
echo "Starting AgentBeats controller..." >&2

# Start the AgentBeats controller
exec agentbeats run_ctrl

