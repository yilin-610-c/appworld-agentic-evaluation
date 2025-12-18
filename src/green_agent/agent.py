"""Green agent implementation - manages AppWorld assessment and evaluation."""

import uvicorn
import tomllib
import json
import time
import os
import sys
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard
from a2a.utils import new_agent_text_message, get_text_parts

from appworld import AppWorld, load_task_ids
from src.util import parse_tags
from src.util.a2a_client import send_message


def truncate_output(text, max_length=200):
    """Truncate long output for terminal display."""
    text_str = str(text)
    if len(text_str) > max_length:
        return text_str[:max_length] + f"... (truncated, total: {len(text_str)} chars)"
    return text_str


def load_agent_card_toml(agent_name: str) -> dict:
    """Load agent card configuration from TOML file."""
    current_dir = os.path.dirname(__file__)
    with open(f"{current_dir}/{agent_name}.toml", "rb") as f:
        return tomllib.load(f)


def get_meta_api_specs() -> list:
    """Get specifications for the meta-APIs that allow discovering other APIs.
    
    Returns a list of API specifications for api_docs.* functions.
    """
    return [
        {
            "name": "api_docs.show_app_descriptions",
            "description": "Get descriptions of all available apps in AppWorld",
            "parameters": {},
            "returns": {
                "type": "list", 
                "description": "List of dicts with 'name' and 'description' keys for each app",
                "example": [
                    {"name": "spotify", "description": "A music streaming app..."},
                    {"name": "gmail", "description": "An email app..."}
                ]
            }
        },
        {
            "name": "api_docs.show_api_descriptions",
            "description": "Get list of all API names for a specific app",
            "parameters": {
                "app_name": {
                    "type": "string", 
                    "required": True, 
                    "description": "The app name (e.g., 'spotify', 'gmail', 'amazon')"
                }
            },
            "returns": {
                "type": "list", 
                "description": "List of dicts with 'name' (API name without app prefix) and 'description' keys",
                "example": [
                    {"name": "login", "description": "Login to your account."},
                    {"name": "show_account", "description": "Show your account information."}
                ]
            }
        },
        {
            "name": "api_docs.show_api_doc",
            "description": "Get detailed documentation for a specific API",
            "parameters": {
                "app_name": {
                    "type": "string",
                    "required": True,
                    "description": "The app name (e.g., 'spotify', 'gmail')"
                },
                "api_name": {
                    "type": "string", 
                    "required": True, 
                    "description": "The API name without app prefix (e.g., 'login', 'send_email')"
                }
            },
            "returns": {
                "type": "dict", 
                "description": "Detailed API documentation including app_name, api_name, method, path, parameters, response_schemas",
                "example": {
                    "app_name": "spotify",
                    "api_name": "login",
                    "method": "POST",
                    "parameters": [{"name": "username", "type": "string", "required": True}],
                    "response_schemas": {"success": {"field": "value"}, "failure": {"message": "string"}}
                }
            }
        }
    ]


async def run_appworld_task(white_agent_url: str, task_id: str, max_steps: int = 30) -> dict:
    """Run an AppWorld task by coordinating with the white agent.
    
    Args:
        white_agent_url: URL of the white agent to test
        task_id: AppWorld task ID to run
        max_steps: Maximum number of interaction steps
        
    Returns:
        Dictionary with evaluation results
    """
    # Set APPWORLD_ROOT environment variable before initializing AppWorld
    # APPWORLD_ROOT should point to the AppWorld project root (containing data/)
    appworld_root = '/home/lyl610/green1112/appworld'
    if not os.path.exists(appworld_root):
        # Try relative path as fallback
        script_dir = os.path.dirname(os.path.abspath(__file__))
        appworld_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..', 'appworld'))
    
    # Verify the data directory exists
    appworld_data = os.path.join(appworld_root, 'data')
    if not os.path.exists(appworld_data):
        raise Exception(f"AppWorld data directory not found at {appworld_data}. Please ensure AppWorld is installed.")
    
    os.environ['APPWORLD_ROOT'] = appworld_root
    print(f"Using AppWorld from: {appworld_root}")
    
    metrics = {"task_id": task_id}
    
    with AppWorld(task_id=task_id, experiment_name="green_agent_eval") as world:
        # Get task instruction
        instruction = world.task.instruction
        print(f"Task Instruction: {instruction}")
        
        # Get meta-API specifications for discovery
        print("Preparing meta-APIs for agent discovery...")
        meta_apis = get_meta_api_specs()
        print(f"Providing {len(meta_apis)} discovery/documentation APIs")
        
        # Prepare initial message with meta-APIs (Approach II)
        initial_message = f"""Your task is to help answer the following question:

<task>
{instruction}
</task>

**IMPORTANT CONTEXT:**
- You are operating in an automated AppWorld environment
- DO NOT ask humans for any information (passwords, usernames, etc.)
- Use the 'supervisor' app to access credentials and personal information
- The supervisor has access to all login credentials for various services
- Example: To login to Spotify, first get credentials from supervisor APIs

You have access to AppWorld APIs. Follow these steps to discover and use them:

**Step 1: Discover available apps**
   Call: api_docs.show_app_descriptions()
   Returns: [{{"name": "spotify", "description": "..."}}, {{"name": "supervisor", "description": "..."}}, ...]
   
   IMPORTANT: The 'supervisor' app contains credentials for all services!

**Step 2: Get APIs for the relevant apps**
   Call: api_docs.show_api_descriptions(app_name='spotify')
   Returns: [{{"name": "login", "description": "..."}}, {{"name": "show_playlist_library", "description": "..."}}, ...]
   
   For credentials: api_docs.show_api_descriptions(app_name='supervisor')
   Note: API names returned here do NOT include the app prefix

**Step 3: Get detailed API documentation**
   Call: api_docs.show_api_doc(app_name='spotify', api_name='login')
   Returns: Full API details including parameters, types, response schemas, etc.

**Step 4: Call the actual APIs**
   Example workflow for accessing Spotify:
   1. Get credentials: supervisor.show_credentials() (or similar supervisor API)
   2. Login: spotify.login(username='...', password='...')
   3. Use other Spotify APIs to complete your task
   
   Important: Use the FULL API name (app_name.api_name) when calling actual APIs

Here are the discovery/documentation APIs you can use:

<tools>
{json.dumps(meta_apis, indent=2)}
</tools>

**Communication Protocol:**
- ALWAYS respond with JSON wrapped in <json>...</json> tags
- To call an API, respond with JSON:
  {{"action": "call_api", "api_name": "app.function", "parameters": {{"param1": "value1"}}}}
  Example: {{"action": "call_api", "api_name": "api_docs.show_app_descriptions", "parameters": {{}}}}
  Example: {{"action": "call_api", "api_name": "supervisor.show_profile", "parameters": {{}}}}
  Example: {{"action": "call_api", "api_name": "spotify.login", "parameters": {{"username": "user@example.com", "password": "pass123"}}}}
  
- To provide a final answer:
  {{"action": "answer", "content": "your answer here"}}

After each API call, I will provide you with the result.

**Start by discovering what apps are available, then find credentials via supervisor, then complete the task!**
"""
        
        context_id = None
        step_count = 0
        task_completed = False
        
        print(f"\n{'='*80}")
        print("Starting task execution...")
        print(f"{'='*80}\n")
        
        for step in range(max_steps):
            step_count += 1
            print(f"\n--- Step {step_count} ---")
            print(f"Sending message to white agent...")
            
            # Send message to white agent
            try:
                white_agent_response = await send_message(
                    white_agent_url, initial_message, context_id=context_id
                )
                
                # Extract response
                from a2a.types import SendMessageSuccessResponse, Message
                res_root = white_agent_response.root
                if not isinstance(res_root, SendMessageSuccessResponse):
                    print(f"Error: Unexpected response type: {type(res_root)}")
                    break
                    
                res_result = res_root.result
                if not isinstance(res_result, Message):
                    print(f"Error: Unexpected result type: {type(res_result)}")
                    break
                
                # Update context ID
                if context_id is None:
                    context_id = res_result.context_id
                else:
                    assert context_id == res_result.context_id, \
                        "Context ID should remain the same in a conversation"
                
                # Get text response
                text_parts = get_text_parts(res_result.parts)
                if not text_parts:
                    print("Error: No text in response")
                    break
                    
                white_text = text_parts[0]
                print(f"White agent response:\n{white_text}\n")
                
                # Parse action from response
                tags = parse_tags(white_text)
                if "json" not in tags:
                    print("Error: No JSON found in response")
                    # Send a reminder message instead of breaking immediately
                    initial_message = """ERROR: You must respond with JSON wrapped in <json>...</json> tags.

Reminder of the correct format:

<json>
{{"action": "call_api", "api_name": "...", "parameters": {{...}}}}
</json>

OR

<json>
{{"action": "answer", "content": "your answer here"}}
</json>

Examples:
- To discover apps: <json>{{"action": "call_api", "api_name": "api_docs.show_app_descriptions", "parameters": {{}}}}</json>
- To get supervisor APIs: <json>{{"action": "call_api", "api_name": "api_docs.show_api_descriptions", "parameters": {{"app_name": "supervisor"}}}}</json>

Please respond again with the proper JSON format."""
                    continue  # Continue loop instead of breaking
                    
                action_json = tags["json"]
                action = json.loads(action_json)
                
                # Process action
                if action.get("action") == "answer":
                    # White agent provided final answer
                    final_answer = action.get("content", "")
                    print(f"\nFinal Answer: {final_answer}")
                    
                    # Complete the task in AppWorld with the answer
                    # For question-style tasks, need to pass the answer parameter
                    # Need to print result to capture it
                    print("Submitting answer to supervisor...")
                    code = f"result = apis.supervisor.complete_task(answer={repr(final_answer)})\nprint(result)"
                    completion_result = world.execute(code)
                    print(f"Task completion result: {completion_result}")
                    task_completed = True
                    break
                    
                elif action.get("action") == "call_api":
                    # Execute API call in AppWorld
                    api_name = action.get("api_name", "")
                    parameters = action.get("parameters", {})
                    
                    print(f"Executing: {api_name} with {truncate_output(parameters, max_length=100)}")
                    
                    # Build the API call
                    # IMPORTANT: Must print the result so it's captured in stdout
                    # Otherwise world.execute() only returns "Execution successful."
                    params_str = ", ".join([f"{k}={repr(v)}" for k, v in parameters.items()])
                    code = f"result = apis.{api_name}({params_str})\nprint(result)"
                    
                    try:
                        api_result = world.execute(code)
                        print(f"API Result: {truncate_output(api_result, max_length=150)}")
                        
                        # Prepare next message with result
                        initial_message = f"""API call result:
<api_result>
{api_result}
</api_result>

Please analyze this result and decide your next action. You can:
1. Call another API if you need more information
2. Provide a final answer if you have enough information

Remember to wrap your JSON response with <json>...</json> tags.
"""
                    except Exception as e:
                        print(f"API execution error: {e}")
                        initial_message = f"""API call failed with error:
<error>
{str(e)}
</error>

Please try a different approach or API call.
"""
                else:
                    print(f"Unknown action: {action.get('action')}")
                    break
                    
            except Exception as e:
                print(f"Error in step {step_count}: {e}")
                import traceback
                traceback.print_exc()
                break
        
        # Evaluate the task
        print(f"\n{'='*80}")
        print("Evaluating task...")
        print(f"{'='*80}\n")
        
        eval_result = world.evaluate()
        
        # Use to_dict() to get evaluation results
        ev_dict = eval_result.to_dict()
        
        # Display full evaluation results (like MCP version)
        print(f"EVALUATION RESULTS:")
        print(f"{'='*80}")
        print(json.dumps(ev_dict, indent=2))
        print(f"{'='*80}\n")
        
        def _cnt(x):
            """Count helper function."""
            if x is None:
                return 0
            if isinstance(x, int):
                return x
            if isinstance(x, (list, tuple, set)):
                return len(x)
            return 0
        
        # Extract passes and fails with multiple fallback names
        passes = ev_dict.get("passes") or ev_dict.get("passed") or ev_dict.get("successes") or ev_dict.get("passes_list")
        fails = ev_dict.get("fails") or ev_dict.get("failures") or ev_dict.get("failed") or ev_dict.get("errors")
        
        # If tests field exists, try to infer from it
        if ("tests" in ev_dict) and (passes is None or fails is None):
            tests = ev_dict["tests"]
            if isinstance(tests, list) and tests and isinstance(tests[0], dict):
                p = sum(1 for t in tests if str(t.get("status", "")).lower() in ("pass", "passed", "success"))
                f = sum(1 for t in tests if str(t.get("status", "")).lower() in ("fail", "failed", "error"))
                if passes is None: 
                    passes = p
                if fails is None: 
                    fails = f
        
        passes = _cnt(passes)
        fails = _cnt(fails)
        total = passes + fails
        
        # If still no data, try parsing report text
        if total == 0:
            try:
                rep = eval_result.report(print_it=False, colorize=False)
                import re
                mp = re.search(r"Num Passed Tests\s*:\s*(\d+)", rep)
                mf = re.search(r"Num Failed Tests\s*:\s*(\d+)", rep)
                if mp: 
                    passes = int(mp.group(1))
                if mf: 
                    fails = int(mf.group(1))
                total = passes + fails
            except Exception as e:
                print(f"Warning: Could not parse evaluation report: {e}")
        
        # Determine success
        success = ev_dict.get("success")
        if success is None:
            success = (fails == 0 and total > 0)
        
        metrics["steps"] = step_count
        metrics["success"] = bool(success)
        metrics["passes"] = passes
        metrics["fails"] = fails
        metrics["total"] = total
        metrics["score"] = ev_dict.get("score", 0)
        metrics["evaluation"] = ev_dict  # Store full evaluation dict like MCP version
        
        # Display summary
        print(f"Evaluation Summary:")
        print(f"  Success: {success}")
        print(f"  Passed: {passes}/{total}")
        print(f"  Failed: {fails}/{total}")
        print(f"  Score: {metrics['score']}")
        print(f"  Steps: {step_count}")
        
        return metrics


class AppWorldGreenAgentExecutor(AgentExecutor):
    """Agent executor for the AppWorld green agent."""
    
    def __init__(self):
        pass

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the assessment task.
        
        Expected input format:
        <white_agent_url>http://localhost:9002/</white_agent_url>
        <task_id>82e2fac_1</task_id>
        """
        print("Green agent: Received a task, parsing...")
        user_input = context.get_user_input()
        tags = parse_tags(user_input)
        
        white_agent_url = tags.get("white_agent_url", "")
        task_id = tags.get("task_id", "")
        
        if not white_agent_url or not task_id:
            await event_queue.enqueue_event(
                new_agent_text_message(
                    "Error: Missing white_agent_url or task_id in request"
                )
            )
            return
        
        print(f"Testing white agent at: {white_agent_url}")
        print(f"Task ID: {task_id}")
        
        timestamp_started = time.time()
        
        try:
            # Run the task
            metrics = await run_appworld_task(white_agent_url, task_id)
            
            metrics["time_used"] = time.time() - timestamp_started
            
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
        raise NotImplementedError


def start_green_agent(
    agent_name: str = "appworld_green_agent", 
    host: str = "localhost", 
    port: int = 9001
):
    """Start the AppWorld green agent server."""
    # Ensure all output goes to stderr so Cloud Run can capture it
    # This is critical for debugging in Cloud Run environment
    print("Starting AppWorld green agent...", file=sys.stderr, flush=True)
    print(f"Host: {host}, Port: {port}", file=sys.stderr, flush=True)
    print(f"Python version: {sys.version}", file=sys.stderr, flush=True)
    print(f"Working directory: {os.getcwd()}", file=sys.stderr, flush=True)
    
    try:
        agent_card_dict = load_agent_card_toml(agent_name)
        url = f"http://{host}:{port}"
        agent_card_dict["url"] = url
        print(f"Agent card loaded, URL: {url}", file=sys.stderr, flush=True)

        request_handler = DefaultRequestHandler(
            agent_executor=AppWorldGreenAgentExecutor(),
            task_store=InMemoryTaskStore(),
        )
        print("Request handler created", file=sys.stderr, flush=True)

        app = A2AStarletteApplication(
            agent_card=AgentCard(**agent_card_dict),
            http_handler=request_handler,
        )
        print("A2A application created", file=sys.stderr, flush=True)
        print(f"Starting uvicorn server on {host}:{port}...", file=sys.stderr, flush=True)

        uvicorn.run(app.build(), host=host, port=port, log_config=None)
    except Exception as e:
        print(f"ERROR starting green agent: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        raise

