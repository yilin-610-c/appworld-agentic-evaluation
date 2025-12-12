"""Green agent implementation with MCP support (Approach III) - manages AppWorld assessment and evaluation."""

import uvicorn
import tomllib
import json
import time
import os
import sys
import asyncio
import subprocess
from contextlib import asynccontextmanager
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, JSONRPCErrorResponse, JSONRPCError
from a2a.utils import new_agent_text_message, get_text_parts

from appworld import AppWorld, load_task_ids
from appworld.apps import get_all_apps
from src.util import parse_tags
from src.util.a2a_client import send_message


def load_agent_card_toml(agent_name: str) -> dict:
    """Load agent card configuration from TOML file."""
    current_dir = os.path.dirname(__file__)
    with open(f"{current_dir}/{agent_name}.toml", "rb") as f:
        return tomllib.load(f)


class MCPServerManager:
    """Manages AppWorld MCP Server lifecycle."""
    
    def __init__(self, mcp_port: int = 10000, api_port: int = 9000):
        self.mcp_port = mcp_port
        self.api_port = api_port
        self.mcp_process = None
        self.api_process = None
        
    def _check_port_available(self, port: int) -> bool:
        """Check if a port is available."""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Set SO_REUSEADDR to allow immediate reuse of the port
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('127.0.0.1', port))
            sock.close()
            return True
        except OSError:
            sock.close()
            return False
    
    @asynccontextmanager
    async def run_servers(self, task_id: str):
        """Start AppWorld API Server and MCP Server."""
        print(f"Starting AppWorld servers for task {task_id}...")
        
        # Check if ports are available and try to free them if not
        for port_name, port in [("API", self.api_port), ("MCP", self.mcp_port)]:
            if not self._check_port_available(port):
                print(f"⚠️  Port {port} ({port_name}) is already in use. Attempting to free it...")
                try:
                    # Find process using the port
                    result = subprocess.run(
                        ['lsof', '-ti', f':{port}'],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.stdout.strip():
                        pids = result.stdout.strip().split('\n')
                        for pid in pids:
                            print(f"   Killing process {pid} using port {port}...")
                            subprocess.run(['kill', pid], timeout=2)
                        await asyncio.sleep(1)  # Wait for port to be freed
                        print(f"✓ Port {port} is now available")
                    else:
                        raise Exception(f"Port {port} is in use but no process found. Please wait or restart.")
                except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
                    raise Exception(f"Port {port} is already in use and could not be freed: {e}")

        # Prepare environment for subprocesses
        env = os.environ.copy()
        # Ensure APPWORLD_ROOT is set correctly
        if 'APPWORLD_ROOT' not in env:
             # Fallback logic if not set in run_appworld_task_mcp (should not happen but safe)
             appworld_root = '/home/lyl610/green1112/appworld'
             if not os.path.exists(appworld_root):
                 script_dir = os.path.dirname(os.path.abspath(__file__))
                 appworld_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..', 'appworld'))
             env['APPWORLD_ROOT'] = appworld_root
        
        print(f"Starting servers with APPWORLD_ROOT={env.get('APPWORLD_ROOT')}")

        # Start API Server
        print(f"Starting API Server on port {self.api_port}...")
        
        # Use custom script to serve specific task DB
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'serve_task_apis.py')
        api_cmd = [
            sys.executable, script_path,
            task_id,
            str(self.api_port)
        ]
        
        # Capture output to help debugging
        self.api_process = subprocess.Popen(
            api_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,  # Pass environment explicitly
            cwd=os.path.dirname(script_path)  # Run from script directory
        )
        
        # Wait for API server to start and check it's running
        # We need to read stdout/stderr to prevent blocking, but also want to check if it fails
        # A simple way is to check poll() after a sleep
        # Increased wait time for task loading
        await asyncio.sleep(8) 
        
        if self.api_process.poll() is not None:
            # Process exited
            _, stderr = self.api_process.communicate()
            error_msg = stderr.decode('utf-8') if stderr else "No error output"
            raise Exception(f"API Server failed to start (exit code: {self.api_process.returncode}). Error: {error_msg}")
            
        print(f"✓ API Server started on http://localhost:{self.api_port}")
        
        # Start MCP Server
        print(f"Starting MCP Server on port {self.mcp_port}...")
        # Expose all apps (excluding api_docs as it's not a valid app name for MCP server)
        app_names = ",".join(get_all_apps(skip_admin=True, skip_api_docs=True))
        mcp_cmd = [
            sys.executable, "-m", "appworld.cli",
            "serve", "mcp", "http",
            "--port", str(self.mcp_port),
            "--remote-apis-url", f"http://localhost:{self.api_port}",
            "--app-names", app_names,
            "--output-type", "both"
        ]
        
        self.mcp_process = subprocess.Popen(
            mcp_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,  # Pass environment explicitly
            cwd=env['APPWORLD_ROOT']  # Set working directory to AppWorld root
        )
        
        # Wait for MCP server to start and check it's running
        await asyncio.sleep(5)  # MCP server might take longer
        if self.mcp_process.poll() is not None:
            _, stderr = self.mcp_process.communicate()
            error_msg = stderr.decode('utf-8') if stderr else "No error output"
            raise Exception(f"MCP Server failed to start (exit code: {self.mcp_process.returncode}). Error: {error_msg}")
        
        mcp_url = f"http://localhost:{self.mcp_port}/mcp"
        print(f"✓ MCP Server started at {mcp_url}")
        
        # Verify MCP server is actually reachable
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://localhost:{self.mcp_port}/", timeout=5.0)
                if response.status_code >= 500:
                    raise Exception(f"MCP Server returned error: {response.status_code}")
        except Exception as e:
            print(f"Warning: Could not verify MCP server: {e}")
        
        try:
            yield mcp_url
        finally:
            # Cleanup
            print("\nShutting down servers...")
            if self.mcp_process:
                self.mcp_process.terminate()
                self.mcp_process.wait(timeout=5)
                print("✓ MCP Server stopped")
            if self.api_process:
                self.api_process.terminate()
                self.api_process.wait(timeout=5)
                print("✓ API Server stopped")


async def run_appworld_task_mcp(white_agent_url: str, task_id: str, max_steps: int = 30) -> dict:
    """Run an AppWorld task using MCP for tool delivery (Approach III).
    
    Args:
        white_agent_url: URL of the white agent to test
        task_id: AppWorld task ID to run
        max_steps: Maximum number of interaction steps
        
    Returns:
        Dictionary with evaluation results
    """
    # Set APPWORLD_ROOT environment variable
    appworld_root = '/home/lyl610/green1112/appworld'
    if not os.path.exists(appworld_root):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        appworld_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..', 'appworld'))
    
    appworld_data = os.path.join(appworld_root, 'data')
    if not os.path.exists(appworld_data):
        raise Exception(f"AppWorld data directory not found at {appworld_data}. Please ensure AppWorld is installed.")
    
    os.environ['APPWORLD_ROOT'] = appworld_root
    print(f"Using AppWorld from: {appworld_root}")
    
    metrics = {"task_id": task_id}
    
    # Start MCP and API servers
    server_manager = MCPServerManager()
    
    async with server_manager.run_servers(task_id):
        mcp_url = f"http://localhost:{server_manager.mcp_port}/mcp"
        
        # We still need AppWorld instance for task description and evaluation
        # But we connect it to the remote API server we just started
        # Note: AppWorld context manager usually starts its own things, but if we pass remote_apis_url
        # it should use that. However, for evaluation, we need access to the task object.
        # Simpler approach: Use AppWorld normally to get task/evaluate, but let White Agent use MCP.
        # The API server and AppWorld instance share the same file-based DBs if task_id matches.
        
        with AppWorld(task_id=task_id, experiment_name="green_agent_mcp_eval") as world:
            # Get task instruction
            instruction = world.task.instruction
            print(f"\nTask Instruction: {instruction}")
            print(f"\n{'='*80}")
            print("MCP MODE: Tools will be delivered via MCP Protocol")
            print(f"{'='*80}\n")
            
            # Prepare initial message with MCP connection info (Approach III)
            initial_message = f"""Your task is to help answer the following question:

<task>
{instruction}
</task>

**IMPORTANT CONTEXT:**
- You are operating in an automated AppWorld environment
- DO NOT ask humans for any information (passwords, usernames, etc.)
- Use the 'supervisor' app to access credentials and personal information
- The supervisor has access to all login credentials for various services

**ANSWER FORMAT:**
- Provide ONLY the requested information in your final answer
- For "What is the title of X?", answer with ONLY the title (e.g., "Song Name")
- Do NOT include extra explanation like "The title is..." or "by Artist"
- If there is no explicit answer, leave the content empty

**MCP Tool Access:**

Connect to the MCP server to discover and use tools:

MCP Server URL: {mcp_url}

Use your MCP client to:
1. List available tools
2. Call tools with proper arguments

Format for tool calls:
```json
{{
  "action": "call_mcp_tool",
  "tool_name": "tool_name_here",
  "arguments": {{ "arg1": "value1", ... }}
}}
```

When you have the final answer, please respond with:
```json
{{
  "action": "answer",
  "content": "your answer here"
}}
```
"""
            
            print("Sending initial message to white agent...")
            
            # Send message to white agent
            response = await send_message(
                url=white_agent_url,
                message=initial_message
            )
            
            # Extract response
            from a2a.types import SendMessageSuccessResponse, Message, JSONRPCErrorResponse
            res_root = response.root
            
            if isinstance(res_root, JSONRPCErrorResponse):
                print(f"Error from White Agent: {res_root.error.message}")
                return {"success": False, "error": res_root.error.message}

            if not isinstance(res_root, SendMessageSuccessResponse):
                print(f"Error: Unexpected response type: {type(res_root)}")
                return {"success": False, "error": "Unexpected response type"}
                
            res_result = res_root.result
            if not isinstance(res_result, Message):
                print(f"Error: Unexpected result type: {type(res_result)}")
                return {"success": False, "error": "Unexpected result type"}
            
            context_id = res_result.context_id
            
            # Main interaction loop
            step_count = 0
            task_completed = False
            final_answer = None
            
            # Wait for white agent to complete task via MCP
            print("Waiting for white agent to complete task via MCP...")
            print("(White agent will use MCP client to discover and call tools)")
            print(f"Maximum steps: {max_steps}")
            print(f"{'='*80}")

            # We need a loop to keep receiving status updates from White Agent
            # In MCP mode, White Agent should just do its work and finally report back
            # But A2A usually implies turn-taking.
            # If White Agent does everything in one "turn" (internal loop), we just get the final response.
            # If White Agent wants to report progress, it might send messages.
            # Let's assume White Agent will report "answer" when done.
            
            # Loop to handle potential status updates or final answer
            while step_count < max_steps:
                step_count += 1
                print(f"\n--- Step {step_count} ---")
                
                # Check response from previous turn (or initial)
                text_parts = get_text_parts(res_result.parts)
                if not text_parts:
                    print("Error: No text in response")
                    break
                    
                white_text = text_parts[0]
                print(f"White Agent Response:\n{white_text}\n")
                
                # Parse action
                tags = parse_tags(white_text)
                
                # Support markdown json blocks if xml tag not found
                if "json" not in tags:
                    import re
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', white_text, re.DOTALL)
                    if json_match:
                        tags["json"] = json_match.group(1)
                
                # Check for final answer
                if "json" in tags:
                    try:
                        print("[Green Agent] Found JSON in Markdown format")
                        action = json.loads(tags["json"])
                        print(f"[Green Agent] Parsed action: {action.get('action')}")
                        
                        if action.get("action") == "answer":
                            final_answer = action.get("content")
                            print(f"✓ Final Answer: {final_answer}")
                            
                            # Submit answer to AppWorld
                            print(f"\nCompleting task with answer: {final_answer}")
                            try:
                                # Use supervisor API to complete task
                                # Note: We use world.execute to run this on the internal AppWorld instance
                                # which shares the DB with the API server
                                code = f"result = apis.supervisor.complete_task(answer={repr(final_answer)})\nprint(result)"
                                result = world.execute(code)
                                print(f"Task completion result: {result}")
                            except Exception as e:
                                print(f"Error completing task: {e}")
                                import traceback
                                traceback.print_exc()
                                
                            task_completed = True
                            break
                        elif action.get("action") == "call_mcp_tool":
                             # White agent should call tools directly, but if it sends back a message saying it did...
                             print("Note: Received action 'call_mcp_tool' but in MCP mode, tools should be called via MCP client")
                    except json.JSONDecodeError:
                        print("Error: Invalid JSON in response")
                
                # If not completed, prompt for status/next step
                # In a real MCP scenario, the White Agent might stay in its own loop calling tools
                # until it's done. But if it returns control to us without an answer, we prompt it again.
                # This handles cases where White Agent yields control or sends progress updates.
                
                msg = "Please continue. If you have finished, provide the final answer in JSON format."
                
                response = await send_message(
                    url=white_agent_url,
                    message=msg,
                    context_id=context_id
                )
                
                res_root = response.root
                if isinstance(res_root, JSONRPCErrorResponse):
                    print(f"Error from White Agent: {res_root.error.message}")
                    break
                res_result = res_root.result
            
            # Evaluation
            print(f"\n{'='*80}")
            if not task_completed:
                print(f"Task incomplete after {max_steps} steps")
            
            print("Saving final state...")
            # world.close() # Ensure DBs are flushed - handled by context manager
            
            print("Evaluating task...")
            print(f"{'='*80}\n")
            
            eval_result = world.evaluate()
            ev_dict = eval_result.to_dict()
            print(f"EVALUATION RESULTS:")
            print(f"{'='*80}")
            print(json.dumps(ev_dict, indent=2))
            print(f"{'='*80}")
            
            # Calculate metrics (simplified)
            success = ev_dict.get("success", False)
            
            metrics["success"] = success
            metrics["steps"] = step_count
            metrics["final_answer"] = final_answer
            metrics["evaluation"] = ev_dict
            
            # NEW: Trajectory Analysis
            try:
                from src.evaluator.trajectory_analyzer import analyze_mcp_trajectory
                
                # Get log file path (use context_id from the interaction)
                log_file = f"/tmp/mcp_tool_calls_{context_id}.jsonl"
                
                if os.path.exists(log_file):
                    print(f"\n{'='*80}")
                    print("TRAJECTORY ANALYSIS:")
                    print(f"{'='*80}")
                    trajectory_metrics = analyze_mcp_trajectory(log_file)
                    metrics["trajectory_analysis"] = trajectory_metrics
                    print(json.dumps(trajectory_metrics, indent=2))
                    print(f"{'='*80}")
                else:
                    print(f"\nWarning: Log file not found: {log_file}")
                    print("Trajectory analysis skipped.")
                    
            except Exception as e:
                print(f"\nWarning: Trajectory analysis failed: {e}")
                import traceback
                traceback.print_exc()
            
            return metrics


class AppWorldGreenAgentMCPExecutor(AgentExecutor):
    """Agent executor for the AppWorld green agent (MCP version)."""
    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        print("Green agent (MCP): Received a task, parsing...")
        user_input = context.get_user_input()
        tags = parse_tags(user_input)
        
        white_agent_url = tags.get("white_agent_url", "")
        task_id = tags.get("task_id", "")
        
        if not white_agent_url or not task_id:
            await event_queue.enqueue_event(
                new_agent_text_message("Error: Missing white_agent_url or task_id")
            )
            return
        
        print(f"Testing white agent at: {white_agent_url}")
        print(f"Task ID: {task_id}")
        print("Mode: MCP (Approach III)")
        
        try:
            metrics = await run_appworld_task_mcp(white_agent_url, task_id)
            
            result_bool = metrics.get("success", False)
            result_emoji = "✅" if result_bool else "❌"
            
            print("Green agent: Evaluation complete.")
            await event_queue.enqueue_event(
                new_agent_text_message(
                    f"Finished. White agent success: {result_emoji}\n"
                    f"Metrics: {json.dumps(metrics, indent=2)}\n"
                )
            )
        except Exception as e:
            print(f"Error during evaluation: {e}")
            import traceback
            traceback.print_exc()
            await event_queue.enqueue_event(
                new_agent_text_message(f"Error during evaluation: {str(e)}")
            )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass


def start_green_agent_mcp(host: str = "0.0.0.0", port: int = 9001):
    """Start the green agent server with MCP support."""
    print(f"Starting AppWorld Green Agent (MCP Mode) on {host}:{port}")
    
    agent_card_data = load_agent_card_toml("appworld_green_agent")
    # Add URL to agent card data (required by A2A SDK)
    # Use CLOUDRUN_HOST if set (for AgentBeats platform deployment)
    cloudrun_host = os.environ.get("CLOUDRUN_HOST")
    if cloudrun_host:
        # Platform deployment: use HTTPS and CLOUDRUN_HOST
        agent_card_data["url"] = f"https://{cloudrun_host}"
        print(f"Using CLOUDRUN_HOST for Agent Card URL: https://{cloudrun_host}")
    else:
        # Local deployment: use provided host and port
        agent_card_data["url"] = f"http://{host}:{port}"
    agent_card = AgentCard(**agent_card_data)
    
    executor = AppWorldGreenAgentMCPExecutor()
    
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )
    
    app_builder = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=handler
    )
    app = app_builder.build()
    
    uvicorn.run(app, host=host, port=port)

