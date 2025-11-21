"""White agent implementation with MCP support (Approach III)."""

import uvicorn
import tomllib
import json
import os
import sys
import asyncio
import traceback
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
    """Agent executor for the AppWorld white agent (MCP version)."""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.history = []
        self.mcp_client = None
        
    async def connect_to_mcp(self, mcp_url: str):
        """Connect to the MCP server."""
        print(f"[White Agent MCP] Found MCP server URL: {mcp_url}")
        
        if MCPClient is None:
            print("[White Agent MCP] Error: AppWorld MCPClient not available")
            return False
            
        try:
            # Configure MCP Client
            # AppWorld's MCPClient.from_dict expects a config dict
            # For HTTP transport:
            mcp_config = {
                "type": "http",
                "remote_mcp_url": mcp_url.replace("/mcp", "") # Remove /mcp suffix if present, client adds it
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
            # print(f"Tools sample: {[t['name'] for t in tools[:5]]}")
            
            return True
        except Exception as e:
            print(f"[Real MCP] ✗ Failed to connect: {e}")
            traceback.print_exc()
            return False

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        print("[White Agent MCP] Received message...")
        user_input = context.get_user_input()
        
        # Parse input to check for MCP URL
        import re
        mcp_url_match = re.search(r'MCP Server URL: (http://\S+)', user_input)
        
        if mcp_url_match and not self.mcp_client:
            mcp_url = mcp_url_match.group(1)
            await self.connect_to_mcp(mcp_url)
            
            # Initialize system prompt with tool definitions if connected
            if self.mcp_client:
                # List all tools to verify connection and get metadata
                tools = self.mcp_client.list_tools()
                print(f"[Real MCP] ✓ Discovered {len(tools)} tools")
                
                # Extract just names for context efficiency (there are many tools)
                # Assuming tool object has 'name' attribute
                tool_names = [t.name for t in tools]
                tool_list_str = "\n".join(tool_names)
                
                self.history = [
                    {"role": "system", "content": f"""You are a helpful AI assistant operating in an AppWorld environment via MCP.
You have access to {len(tools)} tools.

AVAILABLE TOOLS (Exact Names):
{tool_list_str}

INSTRUCTIONS:
1. The tool names above are EXACT. Do NOT guess or hallucinate tool names (e.g. do not invent 'spotify.get_most_liked_song').
2. Use 'api_docs__show_app_descriptions' to understand available apps.
3. Use 'api_docs__show_apis' with an app_name to see available APIs for that app.
4. Use 'api_docs__show_api_doc' to see how to use a specific API.
5. Use 'supervisor__show_account_passwords' to get credentials if needed.
6. ALWAYS check the tool list above before calling a tool.

IMPORTANT: To call a tool, you MUST output a JSON block. Do not just say you will call it.
Format:
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
"""}
                ]

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
                        
                        try:
                            # REAL MCP CALL
                            result = self.mcp_client.call_tool(tool_name, arguments=args)
                            print(f"[Real MCP] ✓ Tool call successful")
                            
                            # DEBUG: Print result to stdout for inspection
                            print(f"[Real MCP] Result payload: {json.dumps(result, default=str)}")
                            
                            # Send result back to LLM (internal loop)
                            tool_result_msg = f"Tool '{tool_name}' returned:\n{json.dumps(result, indent=2, default=str)}"
                            
                            # We could loop internally, but for A2A visibility, let's return the thought process
                            # But we need to tell Green Agent we're still working.
                            # Actually, Green Agent just waits.
                            # Let's append result to history and run LLM again?
                            # For simplicity in this demo, we return the result to Green Agent
                            # Green Agent will see it and prompt us to continue.
                            
                            # Better: Append result to history, generate next thought
                            self.history.append({"role": "user", "content": tool_result_msg})
                            
                            # Recursively call execute? No, too complex.
                            # Just reply to Green Agent with the thought and the action taken.
                            # Green Agent loop will prompt "Please continue".
                            
                        except Exception as e:
                            print(f"[Real MCP] ✗ Tool call failed: {e}")
                            content += f"\n\n(Tool execution failed: {e})"
                            
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

