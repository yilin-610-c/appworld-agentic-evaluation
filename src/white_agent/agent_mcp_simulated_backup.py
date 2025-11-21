"""White agent implementation with MCP support (Approach III) - the target agent being tested."""

import uvicorn
import os
import json
import re
import asyncio
from typing import Optional
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentSkill, AgentCard, AgentCapabilities
from a2a.utils import new_agent_text_message
from litellm import completion


def prepare_white_agent_card(url: str) -> AgentCard:
    """Prepare the agent card for the white agent with MCP support."""
    skill = AgentSkill(
        id="task_fulfillment_mcp",
        name="Task Fulfillment (MCP)",
        description="Handles user requests using MCP protocol to discover and call tools",
        tags=["general", "tool-calling", "mcp"],
        examples=[],
    )
    card = AgentCard(
        name="appworld_white_agent_mcp",
        description="OpenAI-based agent for completing AppWorld tasks using MCP",
        url=url,
        version="1.0.0-mcp",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(),
        skills=[skill],
    )
    return card


class MCPToolManager:
    """Manages MCP client connection and tool discovery."""
    
    def __init__(self):
        self.mcp_url: Optional[str] = None
        self.tools: list = []
        self.tools_discovered = False
    
    def extract_mcp_url(self, message: str) -> Optional[str]:
        """Extract MCP server URL from message."""
        # Look for URL pattern
        match = re.search(r'MCP Server URL:\s*(http://[^\s]+)', message)
        if match:
            return match.group(1)
        
        # Alternative pattern
        match = re.search(r'(http://localhost:\d+/mcp)', message)
        if match:
            return match.group(1)
        
        return None
    
    async def discover_tools_via_mcp(self, mcp_url: str) -> list:
        """Discover tools using MCP client.
        
        Note: In a full implementation, this would use the actual MCP client.
        For this demo, we'll simulate the tool discovery process.
        """
        print(f"\n[MCP] Connecting to MCP server: {mcp_url}")
        
        # In a real implementation, you would use:
        # from mcp.client.sse import sse_client
        # from mcp import ClientSession
        # 
        # async with sse_client(mcp_url) as (read, write):
        #     async with ClientSession(read, write) as session:
        #         await session.initialize()
        #         tools_response = await session.list_tools()
        #         return tools_response.tools
        
        # For now, we simulate by telling the LLM about the MCP protocol
        print("[MCP] Tool discovery simulated - LLM will be instructed to use MCP format")
        self.tools_discovered = True
        return []
    
    def create_mcp_instructions(self, mcp_url: str) -> str:
        """Create instructions for LLM on how to use MCP."""
        return f"""
**MCP Protocol Available:**

You have access to tools via MCP (Model Context Protocol) at: {mcp_url}

**Tool Discovery:**
To discover available tools, mentally consider these MCP tool categories:
1. `api_docs__*` - API documentation and discovery tools
2. `supervisor__*` - User credentials and profile tools  
3. `spotify__*`, `gmail__*`, etc. - Application-specific tools

**Tool Naming Convention:**
- All tools use format: `{{app_name}}__{{api_name}}`
- Example: `api_docs__show_app_descriptions`, `spotify__login`, `supervisor__show_credentials`

**How to Call Tools:**
When you need to call a tool via MCP, respond with JSON in this format:

```json
{{
  "action": "call_mcp_tool",
  "tool_name": "spotify__login",
  "arguments": {{
    "username": "user@example.com",
    "password": "password123"
  }}
}}
```

**Workflow:**
1. Start by discovering apps: call `api_docs__show_app_descriptions`
2. Get credentials from supervisor: call `supervisor__show_credentials` or similar
3. Use app-specific tools to complete the task
4. Provide final answer: {{"action": "answer", "content": "your answer"}}

**Important:**
- Always wrap JSON in <json>...</json> tags
- Use supervisor tools to get ALL credentials (never ask users)
- Tool calls will be executed via MCP and results returned to you
"""


class AppWorldWhiteAgentMCPExecutor(AgentExecutor):
    """Agent executor for the AppWorld white agent using OpenAI with MCP support."""
    
    def __init__(self):
        self.ctx_id_to_messages = {}
        self.ctx_id_to_step_count = {}  # Track steps per context
        self.max_internal_steps = 35  # Safety limit (slightly higher than green agent's 30)
        self.mcp_manager = MCPToolManager()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
    
    async def cancel(self) -> None:
        """Cancel the current execution (required by AgentExecutor)."""
        pass

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the agent logic using OpenAI API with MCP tool support."""
        user_input = context.get_user_input()
        
        # Initialize message history for this context
        if context.context_id not in self.ctx_id_to_messages:
            self.ctx_id_to_messages[context.context_id] = []
        
        # Initialize and check step counter for this context
        if context.context_id not in self.ctx_id_to_step_count:
            self.ctx_id_to_step_count[context.context_id] = 0
        
        self.ctx_id_to_step_count[context.context_id] += 1
        current_step = self.ctx_id_to_step_count[context.context_id]
        
        print(f"[White Agent MCP] Step {current_step}/{self.max_internal_steps}")
        
        # Safety check: if exceeded max steps, send timeout response
        if current_step > self.max_internal_steps:
            print(f"[White Agent MCP] ⚠️  Exceeded max internal steps ({self.max_internal_steps})")
            await event_queue.enqueue_event(
                new_agent_text_message(
                    '<json>{"action": "answer", "content": "<<task_timeout>>"}</json>',
                    context_id=context.context_id
                )
            )
            return
        
        messages = self.ctx_id_to_messages[context.context_id]
        
        # On first message, extract MCP URL and set up system prompt
        if len(messages) == 0:
            mcp_url = self.mcp_manager.extract_mcp_url(user_input)
            
            if mcp_url:
                self.mcp_manager.mcp_url = mcp_url
                print(f"\n[White Agent MCP] Detected MCP server: {mcp_url}")
                
                # Discover tools (simulated for now)
                await self.mcp_manager.discover_tools_via_mcp(mcp_url)
            
            # Add system prompt with MCP instructions
            system_prompt = """You are an AI agent operating in an automated AppWorld testing environment with MCP (Model Context Protocol) support.

CRITICAL RULES:
1. You are in an AUTOMATED environment - NEVER ask humans for information
2. Tools are available via MCP protocol - use the specified JSON format to call them
3. Use the 'supervisor' app to get user credentials, addresses, payment info, etc.
4. ALWAYS respond with JSON wrapped in <json>...</json> tags
5. Think step by step and use MCP tools to gather all needed information

**MCP Tool Calling:**
To call any tool, respond with:
```json
{
  "action": "call_mcp_tool",
  "tool_name": "app_name__api_name",
  "arguments": {"param1": "value1"}
}
```

To provide final answer:
```json
{
  "action": "answer",
  "content": "your final answer"
}
```

**Typical Workflow:**
1. Discover apps: `api_docs__show_app_descriptions`
2. Get supervisor credentials: `supervisor__show_credentials` or `supervisor__show_profile`
3. Login to services: `spotify__login`, `gmail__login`, etc.
4. Use service APIs to complete task
5. Provide final answer

**CRITICAL - Understanding Data Types:**
- "most-liked song" = song with HIGHEST like_count NUMBER
- "earliest/latest date" = compare datetime strings or timestamps
- "highest/lowest price" = compare numeric values
- Always verify field names and types from API responses

Remember: You have MCP tools available - use them to complete the task!
"""
            
            if self.mcp_manager.mcp_url:
                system_prompt += self.mcp_manager.create_mcp_instructions(self.mcp_manager.mcp_url)
            
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Add user message
        messages.append({
            "role": "user",
            "content": user_input
        })
        
        print(f"\n[White Agent MCP] Processing message...")
        print(f"Message history length: {len(messages)}")
        
        # Call OpenAI
        try:
            response = completion(
                model="gpt-4o",
                messages=messages,
                temperature=0.1,
            )
            
            assistant_message = response.choices[0].message.content
            messages.append({
                "role": "assistant",
                "content": assistant_message
            })
            
            print(f"[White Agent MCP] Generated response: {assistant_message[:200]}...")
            
            # Check if this is an MCP tool call - support both XML and Markdown formats
            json_match = re.search(r'<json>(.*?)</json>', assistant_message, re.DOTALL)
            if not json_match:
                # Try Markdown code block format (```json ... ```)
                json_match = re.search(r'```json\s*(.*?)\s*```', assistant_message, re.DOTALL)
            
            if json_match:
                json_content = json_match.group(1).strip()
                try:
                    action_data = json.loads(json_content)
                    action_type = action_data.get("action")
                    
                    print(f"[White Agent MCP] Detected action: {action_type}")
                    
                    if action_type == "call_mcp_tool":
                        # This is an MCP tool call - simulate calling it
                        tool_name = action_data.get("tool_name")
                        arguments = action_data.get("arguments", {})
                        
                        print(f"[White Agent MCP] Calling MCP tool: {tool_name}")
                        print(f"[White Agent MCP] Arguments: {arguments}")
                        
                        # Simulate MCP tool call
                        mcp_response = await self.simulate_mcp_tool_call(tool_name, arguments)
                        
                        # Add tool result to messages
                        tool_result_message = f"""Tool call result:
<json>
{json.dumps(mcp_response, indent=2)}
</json>

Continue with next step or provide final answer if task is complete.
"""
                        messages.append({
                            "role": "user",
                            "content": tool_result_message
                        })
                        
                        # Send the response back to continue the conversation
                        await event_queue.enqueue_event(
                            new_agent_text_message(
                                assistant_message,
                                context_id=context.context_id
                            )
                        )
                        return
                    
                    elif action_type == "answer":
                        # Final answer - just send it
                        print(f"[White Agent MCP] Final answer: {action_data.get('content')}")
                        await event_queue.enqueue_event(
                            new_agent_text_message(
                                assistant_message,
                                context_id=context.context_id
                            )
                        )
                        return
                
                except json.JSONDecodeError as e:
                    print(f"[White Agent MCP] JSON decode error: {e}")
                    # Fall through to send regular response
            
            # No special action - just send the response
            await event_queue.enqueue_event(
                new_agent_text_message(
                    assistant_message,
                    context_id=context.context_id
                )
            )
            
        except Exception as e:
            error_msg = f"Error in white agent: {str(e)}"
            print(f"[White Agent MCP] {error_msg}")
            import traceback
            traceback.print_exc()
            await event_queue.enqueue_event(
                new_agent_text_message(
                    f"<json>{{'error': '{error_msg}'}}</json>",
                    context_id=context.context_id
                )
            )
    
    async def simulate_mcp_tool_call(self, tool_name: str, arguments: dict) -> dict:
        """Simulate MCP tool call.
        
        In a real implementation, this would call the actual MCP server.
        For demo purposes, we'll return placeholder responses.
        """
        print(f"[MCP Simulation] Tool: {tool_name}, Args: {arguments}")
        
        # Simulate some common tool responses
        if "show_app_descriptions" in tool_name:
            return {
                "apps": [
                    {"name": "spotify", "description": "Music streaming service"},
                    {"name": "gmail", "description": "Email service"},
                    {"name": "supervisor", "description": "User profile and credentials"}
                ]
            }
        elif "show_credentials" in tool_name:
            return {
                "credentials": {
                    "spotify": {"username": "user@example.com", "password": "pass123"},
                    "gmail": {"username": "user@gmail.com", "password": "gmailpass"}
                }
            }
        else:
            return {
                "status": "success",
                "message": f"Simulated response for {tool_name}",
                "note": "In production, this would call the actual MCP server"
            }


def start_white_agent_mcp(host: str = "localhost", port: int = 9002):
    """Start the white agent server with MCP support.
    
    Args:
        host: Host to bind to
        port: Port to bind to
    """
    print(f"\n{'='*80}")
    print(f"Starting AppWorld White Agent (MCP Mode - Approach III)")
    print(f"{'='*80}\n")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Mode: MCP Protocol for tool usage")
    print(f"\n{'='*80}\n")
    
    # Prepare agent card
    agent_url = f"http://{host}:{port}"
    agent_card = prepare_white_agent_card(agent_url)
    
    # Create executor
    executor = AppWorldWhiteAgentMCPExecutor()
    
    # Create request handler
    task_store = InMemoryTaskStore()
    http_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store
    )
    
    # Create A2A application
    app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=http_handler
    )
    
    print(f"✓ White Agent (MCP) ready at {agent_url}")
    print(f"✓ Agent card: {agent_url}/.well-known/agent-card.json")
    print(f"\nWaiting for tasks...\n")
    
    # Start server
    uvicorn.run(app.build(), host=host, port=port)

