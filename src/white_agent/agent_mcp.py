"""White agent implementation with MCP support (Approach III) - with Planning Phase."""

import uvicorn
import tomllib
import json
import os
import sys
import asyncio
import traceback
import time
from datetime import datetime
from typing import Dict, Any, List

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard
from a2a.utils import new_agent_text_message

from openai import OpenAI
from src.util import parse_tags

# AppWorld imports for MCP client
try:
    from appworld.serve._mcp import MCPClient
except ImportError:
    print("Warning: appworld not found or MCPClient not available.")
    MCPClient = None


def load_agent_card_toml(agent_name: str) -> dict:
    """Load agent card configuration from TOML file."""
    current_dir = os.path.dirname(__file__)
    with open(f"{current_dir}/{agent_name}.toml", "rb") as f:
        return tomllib.load(f)


class AppWorldWhiteAgentMCPExecutor(AgentExecutor):
    """Agent executor for the AppWorld white agent (MCP version) with Planning Phase."""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.history = []
        self.mcp_client = None
        # Planning phase attributes
        self.planned_tools = []
        self.tool_docs = {}
        self.all_tool_names = []
        # Logging attributes
        self.log_file = None
        
    async def connect_to_mcp(self, mcp_url: str):
        """Connect to the MCP server."""
        print(f"[White Agent MCP] Found MCP server URL: {mcp_url}")
        
        if MCPClient is None:
            print("[White Agent MCP] Error: AppWorld MCPClient not available")
            return False
            
        try:
            # Configure MCP Client
            mcp_config = {
                "type": "http",
                "remote_mcp_url": mcp_url.replace("/mcp", "") # Remove /mcp suffix if present
            }
            if mcp_url.endswith("/mcp"):
                mcp_config["remote_mcp_url"] = mcp_url[:-4]
                
            print(f"[Real MCP] Connecting to MCP server: {mcp_url}")
            print(f"[Real MCP] Configuration: {mcp_config}")
            
            self.mcp_client = MCPClient.from_dict(mcp_config)
            self.mcp_client.connect()
            
            print("[Real MCP] ✓ Successfully connected to MCP server")
            
            # List tools to verify connection
            tools = self.mcp_client.list_tools()
            print(f"[Real MCP] ✓ Discovered {len(tools)} tools")
            
            # Store all tool names for later use
            # Tools might be dict or objects, handle both
            if tools and isinstance(tools[0], dict):
                self.all_tool_names = [t['name'] for t in tools]
            else:
                self.all_tool_names = [t.name for t in tools]
            
            print(f"[Real MCP] Tool sample: {self.all_tool_names[:5]}")
            
            return True
        except Exception as e:
            print(f"[Real MCP] ✗ Failed to connect: {e}")
            traceback.print_exc()
            return False

    async def plan_task(self, task_instruction: str):
        """Planning Phase: Analyze task and pre-select relevant tools with documentation."""
        if not self.mcp_client:
            return None
        
        print(f"\n{'='*80}")
        print("[Planning Phase] Analyzing task and selecting relevant tools...")
        print(f"{'='*80}")
        
        # NEW APPROACH: Directly filter tools by keyword matching
        # Extract likely app names from task (e.g., "Spotify" -> spotify)
        task_lower = task_instruction.lower()
        
        # Identify relevant apps from task keywords
        relevant_apps = set()
        app_keywords = {
            'spotify': ['spotify', 'song', 'music', 'playlist', 'artist', 'album'],
            'gmail': ['gmail', 'email', 'mail', 'message'],
            'amazon': ['amazon', 'product', 'order', 'shopping'],
            'file_system': ['file', 'folder', 'directory'],
            'venmo': ['venmo', 'payment', 'money', 'pay'],
            'todoist': ['todoist', 'task', 'todo'],
            'simple_note': ['note', 'memo'],
            'phone': ['phone', 'call', 'contact'],
            'splitwise': ['splitwise', 'expense', 'split'],
        }
        
        for app, keywords in app_keywords.items():
            if any(keyword in task_lower for keyword in keywords):
                relevant_apps.add(app)
        
        # Always include supervisor and api_docs
        relevant_apps.add('supervisor')
        relevant_apps.add('api_docs')
        
        print(f"[Planning] Detected relevant apps: {sorted(relevant_apps)}")
        
        # Filter tools by relevant apps
        relevant_tools = [
            tool_name for tool_name in self.all_tool_names
            if any(tool_name.startswith(app + '__') for app in relevant_apps)
        ]
        
        print(f"[Planning] Found {len(relevant_tools)} relevant tools from {len(relevant_apps)} apps")
        print(f"[Planning] Sample tools: {relevant_tools[:10]}")
        
        # Step 2: Ask LLM to select and prioritize specific tools
        relevant_tools_str = "\n".join(relevant_tools)
        
        planning_prompt = f"""Given this task:
"{task_instruction}"

Here are the RELEVANT tools available (filtered from {len(self.all_tool_names)} total tools):

{relevant_tools_str}

YOUR TASK: Select the EXACT tools you will need to complete this task, in the order you'll use them.

IMPORTANT: Use the EXACT tool names from the list above. Do NOT modify or guess names.

Respond with JSON:
```json
{{
  "selected_tools": ["tool1", "tool2", "tool3", ...],
  "reasoning": "Brief explanation of the plan"
}}
```
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": planning_prompt}],
                temperature=0
            )
            
            content = response.choices[0].message.content
            print(f"[Planning] LLM response received")
            
            # Parse selected tools
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                plan = json.loads(json_match.group(1))
                selected_tools = plan.get("selected_tools", [])
                reasoning = plan.get("reasoning", "")
                
                print(f"[Planning] Selected {len(selected_tools)} tools")
                print(f"[Planning] Reasoning: {reasoning}")
                print(f"[Planning] Tools: {selected_tools}")
                
                # Step 3: Get detailed documentation for selected tools (top 10)
                for tool_name in selected_tools[:10]:
                    if tool_name not in self.all_tool_names:
                        print(f"[Planning] ⚠️  '{tool_name}' not in available tools, skipping")
                        continue
                    
                    if "__" in tool_name:
                        app_name, api_name = tool_name.split("__", 1)
                        try:
                            print(f"[Planning] Fetching docs for {tool_name}...")
                            doc_result = self.mcp_client.call_tool(
                                "api_docs__show_api_doc",
                                arguments={"app_name": app_name, "api_name": api_name}
                            )
                            self.tool_docs[tool_name] = doc_result
                            print(f"[Planning] ✓ Got docs for {tool_name}")
                        except Exception as e:
                            print(f"[Planning] ✗ Failed to get docs for {tool_name}: {e}")
                
                self.planned_tools = selected_tools
                
                # Build documentation summary
                planned_tools_info = []
                for tool in selected_tools[:10]:
                    if tool in self.tool_docs:
                        doc = self.tool_docs[tool]
                        doc_str = json.dumps(doc, indent=2, default=str)
                        if len(doc_str) > 500:
                            doc_str = doc_str[:500] + "...(truncated)"
                        planned_tools_info.append(f"**{tool}**:\n{doc_str}")
                
                planned_summary = "\n\n".join(planned_tools_info)
                
                print(f"[Planning] ✓ Planning phase complete")
                print(f"{'='*80}\n")
                
                return {
                    "planned_tools": selected_tools,
                    "relevant_tools": relevant_tools,  # Full list of relevant tools
                    "reasoning": reasoning,
                    "docs_summary": planned_summary
                }
                
        except Exception as e:
            print(f"[Planning] ✗ Error during planning: {e}")
            traceback.print_exc()
        
        return None

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        print("[White Agent MCP] Received message...")
        user_input = context.get_user_input()
        
        # Initialize log file on first message
        # Try to extract task_id from the message for better log file naming
        if self.log_file is None:
            import re
            task_id_match = re.search(r'<task_id>(.*?)</task_id>', user_input, re.DOTALL)
            if task_id_match:
                task_id = task_id_match.group(1).strip()
                self.log_file = f"/tmp/mcp_tool_calls_{task_id}.jsonl"
                print(f"[White Agent MCP] Log file initialized with task_id: {self.log_file}")
            else:
                context_id = context.context_id or "unknown"
                self.log_file = f"/tmp/mcp_tool_calls_{context_id}.jsonl"
                print(f"[White Agent MCP] Log file initialized with context_id: {self.log_file}")
        
        # Parse input to check for MCP URL and task
        import re
        mcp_url_match = re.search(r'MCP Server URL: (http://\S+)', user_input)
        
        if mcp_url_match and not self.mcp_client:
            mcp_url = mcp_url_match.group(1)
            await self.connect_to_mcp(mcp_url)
            
            # Initialize system prompt with Planning Phase if connected
            if self.mcp_client:
                # Extract task instruction for planning
                task_match = re.search(r'<task>(.*?)</task>', user_input, re.DOTALL)
                task_instruction = task_match.group(1).strip() if task_match else ""
                
                print(f"[White Agent MCP] Task extraction: {'SUCCESS' if task_instruction else 'FAILED'}")
                if task_instruction:
                    print(f"[White Agent MCP] Task: {task_instruction[:100]}...")
                
                # Perform Planning Phase
                planning_result = None
                if task_instruction:
                    print("[White Agent MCP] Starting Planning Phase...")
                    try:
                        planning_result = await self.plan_task(task_instruction)
                        if planning_result:
                            print("[White Agent MCP] ✓ Planning Phase completed successfully")
                        else:
                            print("[White Agent MCP] ⚠️  Planning Phase returned None")
                    except Exception as e:
                        print(f"[White Agent MCP] ✗ Planning Phase failed: {e}")
                        traceback.print_exc()
                else:
                    print("[White Agent MCP] ⚠️  Skipping Planning Phase - no task instruction found")
                
                # Build system prompt with planning results
                if planning_result:
                    # Enhanced system prompt with planning
                    relevant_tools_str = "\n".join(['- ' + t for t in planning_result['relevant_tools']])
                    
                    system_content = f"""You are a helpful AI assistant operating in an AppWorld environment via MCP.
You have access to {len(self.all_tool_names)} tools.

=== PLANNING PHASE RESULTS ===
Based on analysis of the task, I have filtered down to {len(planning_result['relevant_tools'])} RELEVANT tools.

**PREDICTED EXECUTION PLAN:**
{chr(10).join(['  ' + str(i+1) + '. ' + t for i, t in enumerate(planning_result['planned_tools'][:15])])}

**REASONING:** {planning_result['reasoning']}

**DETAILED DOCUMENTATION (Key Tools):**
{planning_result['docs_summary']}

=== ALL RELEVANT TOOLS (USE THESE) ===
{relevant_tools_str}

=== INSTRUCTIONS ===
1. **PRIORITIZE** the tools from the execution plan above
2. **ONLY use tools from the "ALL RELEVANT TOOLS" list**
3. Use EXACT tool names (format: app_name__api_name)
4. For credentials: use supervisor__show_account_passwords and supervisor__show_profile
5. Do NOT invent tool names - they must match EXACTLY from the list
6. If unsure about usage, call api_docs__show_api_doc with app_name and api_name

=== ANSWER FORMAT ===
- Provide ONLY the requested information, nothing else
- For song titles: ONLY the title, e.g., "Song Name" (not "The title is 'Song Name' by Artist")
- For numerical answers: ONLY the number, e.g., "42" (not "The answer is 42")
- If there is no explicit answer, leave content empty: {{"action": "answer", "content": ""}}

=== TOOL CALL FORMAT ===
To call a tool:
```json
{{
  "action": "call_mcp_tool",
  "tool_name": "EXACT_TOOL_NAME",
  "arguments": {{ "arg_name": "value" }}
}}
```

When you have the final answer:
```json
{{
  "action": "answer",
  "content": "your answer"
}}
```
"""
                else:
                    # Fallback system prompt without planning
                    tool_list_str = "\n".join(self.all_tool_names)
                    system_content = f"""You are a helpful AI assistant operating in an AppWorld environment via MCP.
You have access to {len(self.all_tool_names)} tools.

AVAILABLE TOOLS (Exact Names):
{tool_list_str}

INSTRUCTIONS:
1. Use EXACT tool names from the list above
2. Do NOT guess or hallucinate tool names
3. Use 'api_docs__show_app_descriptions' to understand available apps
4. Use 'supervisor__show_account_passwords' to get credentials

ANSWER FORMAT:
- Provide ONLY the requested information
- For song titles: ONLY the title (not "The title is 'Song Name' by Artist")

Tool call format:
```json
{{
  "action": "call_mcp_tool",
  "tool_name": "EXACT_TOOL_NAME",
  "arguments": {{ "arg_name": "value" }}
}}
```
"""
                
                self.history = [{"role": "system", "content": system_content}]

        # Update history
        self.history.append({"role": "user", "content": user_input})
        
        # Generate response
        print(f"[White Agent MCP] Processing message...")
        print(f"[White Agent MCP] Message history length: {len(self.history)}")
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=self.history,
                temperature=0
            )
            
            content = response.choices[0].message.content
            self.history.append({"role": "assistant", "content": content})
            
            print(f"[White Agent MCP] Generated response: {content[:100]}...")
            
            # Check for tool calls in the response
            tags = parse_tags(content)
            
            # Also support markdown json blocks
            if "json" not in tags:
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
                if json_match:
                    tags["json"] = json_match.group(1)
            
            if "json" in tags:
                try:
                    action = json.loads(tags["json"])
                    if action.get("action") == "call_mcp_tool" and self.mcp_client:
                        tool_name = action.get("tool_name")
                        args = action.get("arguments", {})
                        
                        print(f"[White Agent MCP] Detected action: call_mcp_tool")
                        print(f"[White Agent MCP] Executing REAL MCP tool call...")
                        print(f"[Real MCP] Calling tool: {tool_name}")
                        print(f"[Real MCP] Arguments: {args}")
                        
                        # Record start time and timestamp for logging
                        start_time = time.time()
                        timestamp_start = datetime.now().isoformat()
                        success = False
                        result = None
                        
                        try:
                            # REAL MCP CALL
                            result = self.mcp_client.call_tool(tool_name, arguments=args)
                            success = True
                            
                            # Check for is_error in result.response
                            if isinstance(result, dict):
                                response = result.get("response", {})
                                if isinstance(response, dict) and response.get("is_error") == True:
                                    success = False
                            
                            print(f"[Real MCP] ✓ Tool call successful")
                            
                            # DEBUG: Print result to stdout for inspection
                            print(f"[Real MCP] Result payload: {json.dumps(result, default=str)[:200]}...")
                            
                            # Send result back to LLM (internal loop)
                            tool_result_msg = f"Tool '{tool_name}' returned:\n{json.dumps(result, indent=2, default=str)}"
                            
                            # Append result to history
                            self.history.append({"role": "user", "content": tool_result_msg})
                            
                        except Exception as e:
                            success = False
                            result = {"error": str(e)}
                            
                            print(f"[Real MCP] ✗ Tool call failed: {e}")
                            error_msg = str(e)
                            # Provide helpful feedback to LLM
                            if "not found" in error_msg.lower() or "invalid" in error_msg.lower():
                                tool_result_msg = f"ERROR: Tool '{tool_name}' does not exist. Please check your planning results or the available tools list and use the EXACT tool name."
                            else:
                                tool_result_msg = f"ERROR calling tool '{tool_name}': {error_msg}"
                            self.history.append({"role": "user", "content": tool_result_msg})
                            content += f"\n\n(Tool execution failed: {error_msg})"
                        
                        finally:
                            # Calculate duration and log the call
                            duration_ms = (time.time() - start_time) * 1000
                            
                            # Create log entry
                            log_entry = {
                                "timestamp": timestamp_start,
                                "tool_name": tool_name,
                                "arguments": args,
                                "success": success,
                                "duration_ms": round(duration_ms, 2),
                                "result": result
                            }
                            
                            # Write to JSONL log file
                            try:
                                with open(self.log_file, "a") as f:
                                    f.write(json.dumps(log_entry, default=str) + "\n")
                            except Exception as log_error:
                                print(f"[White Agent MCP] Warning: Failed to write log: {log_error}")
                            
                except json.JSONDecodeError:
                    pass
            
            # Send response back to Green Agent
            await event_queue.enqueue_event(
                new_agent_text_message(content)
            )
            
        except Exception as e:
            print(f"Error generating response: {e}")
            traceback.print_exc()
            await event_queue.enqueue_event(
                new_agent_text_message(f"Error: {str(e)}")
            )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass


def start_white_agent_mcp(host: str = "0.0.0.0", port: int = 9002):
    """Start the white agent server with MCP support."""
    print(f"Starting AppWorld White Agent (MCP Mode) on {host}:{port}")
    
    agent_card_data = load_agent_card_toml("appworld_white_agent")
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
    
    executor = AppWorldWhiteAgentMCPExecutor()
    
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
