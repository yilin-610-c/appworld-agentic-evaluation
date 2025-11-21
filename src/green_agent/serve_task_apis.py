import sys
import os
import json
import uvicorn

# Ensure we can find appworld
try:
    from appworld.task import Task
    from appworld.apps.lib.models.db import get_db_home_path
    from appworld.apps import build_main_app
    from appworld.common.constants import DEFAULT_REMOTE_APIS_PORT
except ImportError:
    # Fallback: try to append APPWORLD_ROOT/src if set
    if 'APPWORLD_ROOT' in os.environ:
        sys.path.append(os.path.join(os.environ['APPWORLD_ROOT'], 'src'))
    from appworld.task import Task
    from appworld.apps.lib.models.db import get_db_home_path
    from appworld.apps import build_main_app
    from appworld.common.constants import DEFAULT_REMOTE_APIS_PORT

def run_task_api_server(task_id: str, port: int = DEFAULT_REMOTE_APIS_PORT):
    print(f"Initializing API Server for Task: {task_id}")
    
    # Load Task metadata to get DB paths
    print(f"Loading task {task_id} metadata...")
    task = Task.load(task_id=task_id)
    
    # Logic adapted from AppWorld.__init__
    # Target is memory (fast, ephemeral) - unique per run/task
    to_db_home_path = get_db_home_path(storage_type="memory", type="task_output", task_id=task_id)
    
    # Source is the task's initial state (from disk)
    from_db_home_path = task.model_collection.from_db_home_path
    
    print(f"Loading DB from: {from_db_home_path}")
    print(f"Writing DB to: {to_db_home_path}")
    print(f"Task Date/Time: {task.datetime}")
    
    app_names = list(task.allowed_apps) + ["admin"]
    print(f"Allowed Apps: {app_names}")

    # Set environment variables for build_main_app/lifespan
    os.environ["LOAD_ON_STARTUP"] = "true"
    
    # Construct arguments for set_local_dbs ONLY
    db_args = {
        "to_db_home_path": to_db_home_path,
        "from_db_home_path": from_db_home_path,
        "create": True,
        "app_names": app_names,
    }
    
    os.environ["APPWORLD_DB_ARGS"] = json.dumps(db_args)
    os.environ["APPWORLD_DATE_TIME"] = task.datetime.isoformat()
    
    # Build the FastAPI app
    app = build_main_app(app_names=app_names)
    
    print(f"Starting uvicorn on port {port}...")
    # Run uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python serve_task_apis.py <task_id> [port]")
        sys.exit(1)
        
    task_id = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9000
    
    run_task_api_server(task_id, port)
