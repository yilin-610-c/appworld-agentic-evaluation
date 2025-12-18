"""White agent implementation - the target agent being tested."""

import uvicorn
import os
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentSkill, AgentCard, AgentCapabilities
from a2a.utils import new_agent_text_message
from litellm import completion


def prepare_white_agent_card(url: str) -> AgentCard:
    """Prepare the agent card for the white agent."""
    skill = AgentSkill(
        id="task_fulfillment",
        name="Task Fulfillment",
        description="Handles user requests and completes tasks using provided tools",
        tags=["general", "tool-calling"],
        examples=[],
    )
    card = AgentCard(
        name="appworld_white_agent",
        description="OpenAI-based agent for completing AppWorld tasks",
        url=url,
        version="1.0.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(),
        skills=[skill],
    )
    return card


class AppWorldWhiteAgentExecutor(AgentExecutor):
    """Agent executor for the AppWorld white agent using OpenAI."""
    
    def __init__(self):
        self.ctx_id_to_messages = {}

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the agent logic using OpenAI API."""
        user_input = context.get_user_input()
        
        # Initialize message history for this context
        if context.context_id not in self.ctx_id_to_messages:
            self.ctx_id_to_messages[context.context_id] = []
        
        messages = self.ctx_id_to_messages[context.context_id]
        
        # Add system prompt on first message to guide the agent
        if len(messages) == 0:
            messages.append({
                "role": "system",
                "content": """You are an AI agent operating in an automated AppWorld testing environment.

CRITICAL RULES:
1. You are in an AUTOMATED environment - NEVER ask humans for information
2. Use the 'supervisor' app to get user credentials, addresses, payment info, etc.
3. ALWAYS respond with JSON wrapped in <json>...</json> tags
4. Explore APIs using api_docs functions before using them
5. Think step by step and use APIs to gather all needed information

When you need credentials for any service (Spotify, Gmail, etc.):
- Call api_docs.show_api_descriptions(app_name='supervisor') to see available supervisor APIs
- Use supervisor APIs like show_profile(), show_credentials(), etc. to get credentials
- NEVER say "please provide your password" - get it from supervisor APIs instead!

Example workflow for accessing a service like Spotify:
1. Discover apps: api_docs.show_app_descriptions()
2. Check supervisor APIs: api_docs.show_api_descriptions(app_name='supervisor')
3. Get credentials: supervisor.show_credentials() or similar
4. Use those credentials: spotify.login(username=..., password=...)

**CRITICAL - Understanding "Most-Liked" and Similar Terms:**
PAY CLOSE ATTENTION to field types and meanings:

- "most-liked song" = song with HIGHEST like_count NUMBER
  → Field: "like_count": 18 (a number)
  → Meaning: How many people liked this song

- "liked song" (by you) = song YOU personally liked
  → Field: "liked": true (a boolean)
  → Meaning: Whether YOU clicked "like"

These are COMPLETELY DIFFERENT! Do NOT confuse them!

When asked for "most-liked/most-popular/highest-rated":
1. Identify the NUMERIC field (like_count, play_count, rating, etc.)
2. Get details for ALL items to see this numeric field
3. Compare the NUMBERS and find the maximum
4. Do NOT stop at the first item with boolean liked=true

Example - WRONG approach:
Task: "Find most-liked song"
❌ Call show_song_privates, find first song with liked: true
❌ Return that song

Example - CORRECT approach:
Task: "Find most-liked song"
✅ Call show_song for ALL songs to get their like_count values
✅ Compare: Song A (like_count: 5), Song B (like_count: 18), Song C (like_count: 10)
✅ Return Song B (highest like_count: 18)

**IMPORTANT - Data Analysis:**
When tasks require finding "most/highest/best/least":
1. Gather ALL relevant items first (IMPORTANT: check if API supports pagination!)
2. Retrieve detailed information for EACH item
3. Compare the specific NUMERIC metric (like_count, play_count, rating, etc.)
4. Find the maximum/minimum based on NUMBERS, not boolean flags
5. Do NOT rely on API names or ordering - always check the actual data fields

**CRITICAL - Pagination:**
Many list/library APIs return only a PAGE of results (often 5 items by default):
- APIs like show_song_library, show_playlist_library, show_liked_songs, etc. have pagination
- ALWAYS check API docs for page_index and page_limit parameters
- When finding "most/least/best", you MUST iterate through ALL pages to get ALL items
- Example: If you need the least-played song, don't just check the first 5 songs!

How to handle pagination:
```
page_index = 0
all_items = []
while True:
    page_results = api_call(..., page_index=page_index, page_limit=20)
    if not page_results or len(page_results) == 0:
        break
    all_items.extend(page_results)
    page_index += 1
    if page_index > 50:  # Safety limit
        break
# Now compare all_items to find the answer
```

**IMPORTANT - Answer Format:**
When providing final answers for question-style tasks:
- Provide CONCISE, DIRECT answers
- Do NOT add explanations, context, or extra information
- Extract only the specific information requested

Examples:
- Question: "What is the title of the most popular song?"
  ✅ Good: "Midnight Dreams"
  ❌ Bad: "The title of the most popular song is 'Midnight Dreams' with 25 plays."
  
- Question: "What is the user's email address?"
  ✅ Good: "john.doe@email.com"
  ❌ Bad: "The user's email address is john.doe@email.com."
  
- Question: "How many items are in the cart?"
  ✅ Good: "3"
  ❌ Bad: "There are 3 items in the shopping cart."

Remember: ALWAYS wrap your response in <json>{"action": "...", ...}</json>"""
            })
        
        # NEW: Add planning phase for first message
        import re
        task_match = re.search(r'<task>(.*?)</task>', user_input, re.DOTALL)
        if task_match:
            task = task_match.group(1).strip()
            
            # Request planning from LLM
            planning_prompt = f"""Before starting the task, analyze it and create a plan.

Task: {task}

Provide your analysis in this format:
<json>
{{
    "action": "plan",
    "task_type": "question|action",
    "key_entities": ["entity1", "entity2"],
    "required_apps": ["app1", "app2"],
    "execution_steps": [
        "Step 1: Description",
        "Step 2: Description"
    ],
    "data_to_collect": ["what data is needed"],
    "comparison_needed": "yes|no (if finding most/least/best)"
}}
</json>

After planning, we'll proceed with execution."""
            
            # Get planning response
            planning_messages = [
                messages[0],  # system prompt
                {"role": "user", "content": planning_prompt}
            ]
            
            model = os.environ.get("WHITE_AGENT_MODEL", "openai/gpt-4o")
            kwargs = {
                "messages": planning_messages,
                "model": model,
                "custom_llm_provider": "openai",
                "api_key": os.getenv("OPENAI_API_KEY"),
                "num_retries": 3,
            }
            if not model.startswith("o1") and not model.startswith("o3") and "gpt-5" not in model:
                kwargs["temperature"] = 0.0
            
            try:
                planning_response = completion(**kwargs)
                planning_content = planning_response.choices[0].message.content
                
                # Extract and display plan
                plan_json_match = re.search(r'<json>(.*?)</json>', planning_content, re.DOTALL)
                if plan_json_match:
                    import json
                    plan = json.loads(plan_json_match.group(1))
                    print("\n" + "="*80)
                    print("PLANNING PHASE")
                    print("="*80)
                    print(f"Task Type: {plan.get('task_type', 'unknown')}")
                    print(f"Required Apps: {', '.join(plan.get('required_apps', []))}")
                    print("\nExecution Steps:")
                    for i, step in enumerate(plan.get('execution_steps', []), 1):
                        print(f"  {i}. {step}")
                    if plan.get('comparison_needed') == 'yes':
                        print("\n⚠️  Comparison Task: Will need to track and compare values")
                    print("="*80 + "\n")
                    
                    # Add plan to message history as context
                    messages.append({
                        "role": "assistant",
                        "content": planning_content
                    })
                    messages.append({
                        "role": "user",
                        "content": f"Good plan! Now execute it step by step. Task: {task}"
                    })
            except Exception as e:
                print(f"Planning phase failed: {e}, proceeding without plan")
        
        messages.append({
            "role": "user",
            "content": user_input,
        })
        
        # Compress message history if it's getting too long
        # Three-layer retention strategy:
        # 1. Always keep: system prompt + initial task (critical context)
        # 2. Compress: middle conversation (API calls/results)
        # 3. Always keep: recent messages (current context)
        MAX_MESSAGES = 20  # Increased threshold to retain more context
        
        if len(messages) > MAX_MESSAGES:
            print(f"Compressing message history: {len(messages)} -> {MAX_MESSAGES} messages")
            
            # Layer 1: Always keep system prompt and initial task message
            system_msg = messages[0]  # System prompt with rules and protocols
            initial_task_msg = messages[1] if len(messages) > 1 else None  # Task description
            
            # Layer 3: Keep recent messages (last 6 rounds = 12 messages)
            num_recent = min(12, len(messages) - 2)  # At least 12 or what's available
            recent_messages = messages[-num_recent:]
            
            # Layer 2: Compress middle conversation
            # Everything between initial_task and recent messages
            if len(messages) > 2 + num_recent:
                middle_messages = messages[2:-num_recent]
                
                # Create intelligent summary
                summary_parts = []
                important_info = []
                
                for msg in middle_messages:
                    role = msg.get("role")
                    content = msg.get("content", "")
                    
                    if role == "user":
                        # Extract important information from user messages
                        if "credential" in content.lower() or "password" in content.lower():
                            important_info.append("Obtained user credentials")
                        elif "login" in content.lower() and "success" in content.lower():
                            important_info.append("Successfully authenticated")
                    elif role == "assistant":
                        # Extract key actions from assistant
                        if "show_playlist" in content or "playlist_library" in content:
                            summary_parts.append("Retrieved playlist information")
                        elif "show_song" in content:
                            summary_parts.append("Examined song details")
                
                # Remove duplicates
                unique_summary = list(dict.fromkeys(summary_parts))
                unique_info = list(dict.fromkeys(important_info))
                
                # Create comprehensive summary including task reminder
                summary_lines = ["=== Progress Summary ==="]
                if unique_info:
                    summary_lines.extend(unique_info)
                if unique_summary:
                    summary_lines.extend(unique_summary)
                
                # Add protocol reminder
                summary_lines.append("\n=== Protocol Reminder ===")
                summary_lines.append('Use: {"action": "call_api", "api_name": "...", "parameters": {...}}')
                summary_lines.append('Or: {"action": "answer", "content": "your answer"}')
                summary_lines.append("Always wrap in <json>...</json> tags")
                
                summary_message = {
                    "role": "user",
                    "content": "\n".join(summary_lines)
                }
                
                print(f"Summary created: {len(middle_messages)} messages compressed")
                print(f"Kept: system + initial_task + summary + {len(recent_messages)} recent")
            else:
                # Not enough middle messages to compress
                summary_message = None
            
            # Reconstruct compressed message list
            if initial_task_msg and summary_message:
                compressed_messages = [system_msg, initial_task_msg, summary_message] + recent_messages
            elif initial_task_msg:
                compressed_messages = [system_msg, initial_task_msg] + recent_messages
            else:
                compressed_messages = [system_msg] + recent_messages
            
            messages_to_send = compressed_messages
            print(f"Final message count: {len(messages_to_send)}")
        else:
            messages_to_send = messages
        
        # Get OpenAI API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            await event_queue.enqueue_event(
                new_agent_text_message(
                    "Error: OPENAI_API_KEY not set in environment",
                    context_id=context.context_id
                )
            )
            return
        
        try:
            # Call OpenAI API with potentially compressed messages
            model = os.environ.get("WHITE_AGENT_MODEL", "openai/gpt-4o")
            kwargs = {
                "messages": messages_to_send,
                "model": model,
                "custom_llm_provider": "openai",
                "api_key": api_key,
                "num_retries": 3,
            }
            if not model.startswith("o1") and not model.startswith("o3") and "o1" not in model and "gpt-5" not in model:
                kwargs["temperature"] = 0.0

            response = completion(**kwargs)
            
            next_message = response.choices[0].message.model_dump()
            content = next_message["content"]
            
            # Add assistant response to history
            messages.append({
                "role": "assistant",
                "content": content,
            })
            
            # Send response
            await event_queue.enqueue_event(
                new_agent_text_message(
                    content, 
                    context_id=context.context_id
                )
            )
            
        except Exception as e:
            print(f"Error calling OpenAI: {e}")
            import traceback
            traceback.print_exc()
            await event_queue.enqueue_event(
                new_agent_text_message(
                    f"Error: {str(e)}",
                    context_id=context.context_id
                )
            )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError


def start_white_agent(
    agent_name: str = "appworld_white_agent", 
    host: str = "localhost", 
    port: int = 9002
):
    """Start the AppWorld white agent server."""
    print("Starting AppWorld white agent...")
    url = f"http://{host}:{port}"
    card = prepare_white_agent_card(url)

    request_handler = DefaultRequestHandler(
        agent_executor=AppWorldWhiteAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    app = A2AStarletteApplication(
        agent_card=card,
        http_handler=request_handler,
    )

    uvicorn.run(app.build(), host=host, port=port)

