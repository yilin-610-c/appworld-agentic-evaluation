"""White agent implementation - the target agent being tested."""

import uvicorn
import os
import json
import time
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentSkill, AgentCard, AgentCapabilities
from a2a.utils import new_agent_text_message
from litellm import completion


# ==========================================
# 1. ConversationLogger - JSONL logging
# ==========================================
class ConversationLogger:
    """Log all agent interactions to JSONL file for debugging and analysis."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else "/tmp", exist_ok=True)
    
    def log_turn(self, step: int, action: Dict, observation: str, reasoning: str = ""):
        """Write structured log entry to JSONL file."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "action": action,
            "observation": observation[:500] if observation else "",  # Truncate long observations
            "reasoning": reasoning[:300] if reasoning else ""  # Truncate long reasoning
        }
        try:
            with open(self.filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                f.flush()  # Immediate flush
        except Exception as e:
            print(f"[Logger] Failed to write log: {e}")


# ==========================================
# 2. TaskAnalyzer - Identify required apps
# ==========================================
class TaskAnalyzer:
    """Analyze task and identify required apps using LLM."""
    
    ALL_SUPPORTED_APPS = [
        "amazon", "gmail", "spotify", "venmo", 
        "todoist", "simple_note", "calendar", "phone", "splitwise"
    ]
    
    def __init__(self, model: str):
        self.model = model
    
    def identify_apps(self, task_instruction: str) -> List[str]:
        """Call LLM to identify which apps are needed for the task."""
        # Always include supervisor and api_docs
        selected_apps = {"supervisor", "api_docs"}
        
        # Build prompt
        apps_list_str = ", ".join(self.ALL_SUPPORTED_APPS)
        system_prompt = f"""You are a dependency analyzer for an AI agent.
Select the NECESSARY apps from the list below to complete the user's task.

[AVAILABLE APPS CANDIDATES]
{apps_list_str}

[OUTPUT FORMAT]
Return ONLY a JSON array of strings. Example: ["gmail", "calendar"]
If no specific app is needed, return [].
"""
        
        try:
            kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Task: {task_instruction}"}
                ],
                "custom_llm_provider": "openai",
                "api_key": os.getenv("OPENAI_API_KEY"),
                "temperature": 0.0,
                "max_tokens": 100
            }
            
            response = completion(**kwargs)
            content = response.choices[0].message.content
            
            # Parse JSON array
            identified = self._parse_json_list(content)
            
            # Add identified apps to set
            for app in identified:
                clean_app = app.lower().strip()
                if clean_app in self.ALL_SUPPORTED_APPS:
                    selected_apps.add(clean_app)
                    
        except Exception as e:
            print(f"[TaskAnalyzer] LLM error: {e}, using default apps")
        
        return list(selected_apps)
    
    def _parse_json_list(self, text: str) -> List[str]:
        """Parse JSON array from LLM response."""
        text = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(text)
        except:
            match = re.search(r'\[.*?\]', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except:
                    pass
        return []


# ==========================================
# 3. ToolRegistry - Fetch and simplify API docs
# ==========================================
class ToolRegistry:
    """Fetch and simplify API documentation for selected apps."""
    
    def __init__(self):
        pass
    
    async def fetch_tools_schema(self, apps: List[str], green_agent_executor) -> Dict[str, List[str]]:
        """Fetch API documentation for each app via Green Agent."""
        schemas = {}
        
        for app in apps:
            try:
                result = await green_agent_executor(f"api_docs.show_api_descriptions", {"app_name": app})
                if result.get("success"):
                    schemas[app] = self._simplify_schema(result.get("result"))
                else:
                    print(f"[ToolRegistry] Failed to fetch docs for {app}: {result.get('error')}")
            except Exception as e:
                print(f"[ToolRegistry] Exception fetching {app} docs: {e}")
        
        return schemas
    
    def _simplify_schema(self, api_docs) -> List[str]:
        """Convert complex API docs to token-friendly format."""
        simplified = []
        
        if isinstance(api_docs, list):
            for entry in api_docs:
                if isinstance(entry, dict):
                    name = entry.get("name", "unknown")
                    desc = entry.get("description", "")[:100]  # First 100 chars
                    
                    # Extract parameter names
                    params = []
                    p = entry.get("parameters") or entry.get("params") or []
                    if isinstance(p, list):
                        for x in p:
                            if isinstance(x, dict):
                                params.append(x.get("name", ""))
                    elif isinstance(p, dict):
                        params = list(p.keys())
                    
                    # Format: "function_name(param1, param2): Description"
                    params_str = ", ".join(params) if params else ""
                    simplified.append(f"{name}({params_str}): {desc}")
        
        return simplified


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
        self.ctx_id_to_logger = {}  # Track logger per context
    
    async def preload_context(self, green_agent_executor, relevant_apps: List[str]) -> Dict[str, Any]:
        """Fetch profile and credentials from supervisor via Green Agent."""
        print("[Context Preload] Fetching supervisor data...")
        context = {"profile": {}, "credentials": []}
        
        # 1. Get profile
        try:
            profile_result = await green_agent_executor("supervisor.show_profile", {})
            if profile_result.get("success"):
                context["profile"] = profile_result["result"]
                print(f"[Context Preload] ✓ Got profile")
        except Exception as e:
            print(f"[Context Preload] Failed to get profile: {e}")
        
        # 2. Get all credentials
        try:
            creds_result = await green_agent_executor("supervisor.show_account_passwords", {})
            if creds_result.get("success"):
                all_creds = creds_result["result"]
                
                # 3. Filter credentials by relevant apps
                if isinstance(all_creds, list):
                    for cred in all_creds:
                        acct_name = str(cred.get("account_name", "")).lower()
                        # Include if matches any relevant app or is supervisor account
                        if any(app in acct_name for app in relevant_apps) or "supervisor" in acct_name:
                            context["credentials"].append(cred)
                    
                    print(f"[Context Preload] ✓ Got {len(context['credentials'])} relevant credentials")
        except Exception as e:
            print(f"[Context Preload] Failed to get credentials: {e}")
        
        return context
    
    def build_enhanced_system_prompt(self, profile: Dict, credentials: List[Dict], tools_schema: Dict[str, List[str]]) -> str:
        """Build enhanced system prompt with preloaded context and tools."""
        
        # Format data as JSON
        profile_str = json.dumps(profile, indent=2, ensure_ascii=False) if profile else "{}"
        creds_str = json.dumps(credentials, indent=2, ensure_ascii=False) if credentials else "[]"
        tools_str = json.dumps(tools_schema, indent=2, ensure_ascii=False) if tools_schema else "{}"
        
        prompt = f"""You are an AI agent operating in an automated AppWorld testing environment.

[USER PROFILE]
{profile_str}

[AVAILABLE CREDENTIALS]
(Use these strictly for login. Do not ask the user for passwords. All credentials are already provided above.)
{creds_str}

[AVAILABLE TOOLS]
(These are the APIs you will use. You must not guess API names; use only the APIs listed here.)
{tools_str}

[CRITICAL RULES]
1. You are in an AUTOMATED environment - NEVER ask humans for information
2. **CREDENTIALS ARE PRELOADED**: Use the credentials from [AVAILABLE CREDENTIALS] above. Do NOT call supervisor APIs to fetch them again.
3. ALWAYS respond with JSON wrapped in <json>...</json> tags
4. Think step by step and use APIs to gather all needed information

**LOGIN PARAMETERS MAPPING (CRITICAL)**:
- When a login tool asks for a `username`, you MUST use the `email` address from the credentials.
- **DO NOT** use the `account_name` or app name (e.g., "spotify") as the username.
- Example: If creds are {{"account_name": "spotify", "email": "bob@mail.com"}}, you MUST call login(username='bob@mail.com')

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
❌ Call show_liked_songs, find first song with liked: true
❌ Return that song

Example - CORRECT approach:
Task: "Find most-liked song"
✅ Get all songs from playlists to check
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

[RESPONSE FORMAT]
You must ALWAYS respond with JSON in one of these formats:

To call an API:
<json>
{{"action": "call_api", "api_name": "app.function_name", "parameters": {{...}}}}
</json>

To provide final answer:
<json>
{{"action": "answer", "content": "your concise answer here"}}
</json>

Remember: Use the preloaded credentials above. Start by using them to login, not by fetching them again!"""
        
        return prompt.strip()
    
    def build_step_prompt(self, step: int, task_instruction: str, last_observation: str) -> str:
        """Build structured step prompt for guidance."""
        prompt = f"""[TASK INSTRUCTION]
{task_instruction}

[CURRENT STATUS]
Step: {step}

[LAST OBSERVATION]
{last_observation}

[INSTRUCTION FOR NEXT STEP]
Based on the Last Observation:
1. If it was an ERROR: Analyze why it failed. Do not repeat the exact same parameters. Change your approach or fix the arguments.
2. If it was SUCCESS: Proceed to the next logical step.
3. If you found IDs or data: Use them in the next action.
4. Remember: For "most/least/best" tasks, compare ALL items (check pagination!)
5. Use the preloaded credentials from your context - don't fetch them again.

Generate the next JSON response now."""
        
        return prompt.strip()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the agent logic using OpenAI API with enhanced features."""
        user_input = context.get_user_input()
        
        # Initialize message history for this context
        if context.context_id not in self.ctx_id_to_messages:
            self.ctx_id_to_messages[context.context_id] = []
        
        messages = self.ctx_id_to_messages[context.context_id]
        step_count = len([m for m in messages if m.get("role") == "user"]) + 1
        
        # ====================================================================================
        # INITIALIZATION PHASE (First message only)
        # ====================================================================================
        if len(messages) == 0:
            print("\n" + "="*80)
            print("INITIALIZATION PHASE")
            print("="*80)
            
            # 1. Extract task from user_input
            task_match = re.search(r'<task>(.*?)</task>', user_input, re.DOTALL)
            if not task_match:
                # Fallback: use entire input as task
                task_instruction = user_input.strip()
            else:
                task_instruction = task_match.group(1).strip()
            
            print(f"Task: {task_instruction[:100]}...")
            
            # 2. Create TaskAnalyzer and identify required apps
            model = os.environ.get("WHITE_AGENT_MODEL", "openai/gpt-4o")
            task_analyzer = TaskAnalyzer(model)
            required_apps = task_analyzer.identify_apps(task_instruction)
            print(f"[TaskAnalyzer] Identified apps: {required_apps}")
            
            # 3. Create green_agent_executor wrapper for API calls during init
            async def green_agent_executor(api_name: str, parameters: Dict) -> Dict:
                """Helper to call Green Agent APIs during initialization."""
                # We need to directly interact with event_queue to make API calls
                # Store result in a way we can retrieve it
                
                # For now, we'll return a placeholder - this needs green agent integration
                # In practice, this would send a message to green agent and wait for response
                return {"success": False, "error": "Green agent executor not fully implemented yet"}
            
            # 4. Call preload_context - fetch profile and credentials
            try:
                preloaded_context = await self.preload_context(green_agent_executor, required_apps)
                profile = preloaded_context.get("profile", {})
                credentials = preloaded_context.get("credentials", [])
                print(f"[Context] Preloaded {len(credentials)} credentials")
            except Exception as e:
                print(f"[Context] Preload failed: {e}, continuing without preload")
                profile = {}
                credentials = []
            
            # 5. Create ToolRegistry and fetch API schemas
            try:
                tool_registry = ToolRegistry()
                tools_schema = await tool_registry.fetch_tools_schema(required_apps, green_agent_executor)
                print(f"[ToolRegistry] Fetched schemas for {len(tools_schema)} apps")
            except Exception as e:
                print(f"[ToolRegistry] Failed to fetch schemas: {e}")
                tools_schema = {}
            
            # 6. Build enhanced system prompt with preloaded context
            if profile or credentials or tools_schema:
                system_prompt = self.build_enhanced_system_prompt(profile, credentials, tools_schema)
                print("[System Prompt] Using enhanced prompt with preloaded context")
            else:
                # Fallback to basic prompt if preload failed
                system_prompt = """You are an AI agent operating in an automated AppWorld testing environment.

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

**IMPORTANT - Answer Format (CRITICAL):**
When providing final answers for question-style tasks:
- Provide CONCISE, DIRECT answers - ONLY the requested information
- Do NOT add explanations, context, URLs, or extra information
- Extract ONLY the specific information requested

Examples:
- Question: "What is the title of the most popular song?"
  ✅ CORRECT: "Midnight Dreams"
  ❌ WRONG: "The title of the most popular song is 'Midnight Dreams' with 25 plays."
  ❌ WRONG: "Midnight Dreams (https://spotify.com/songs/123)"
  
- Question: "What is the user's email?"
  ✅ CORRECT: "john.doe@email.com"
  ❌ WRONG: "The user's email address is john.doe@email.com."

- Question: "What is the title of the most-liked song?"
  ✅ CORRECT: "A Love That Never Was"
  ❌ WRONG: "The most-liked song is 'A Love That Never Was' with a like_count of 18."

[RESPONSE FORMAT]
<json>{"action": "call_api", "api_name": "...", "parameters": {...}}</json>
OR
<json>{"action": "answer", "content": "CONCISE_ANSWER_ONLY"}</json>"""
                print("[System Prompt] Using fallback prompt (preload failed)")
            
            messages.append({"role": "system", "content": system_prompt})
            
            # 7. Initialize ConversationLogger
            log_file = f"/tmp/a2a_agent_trace_{context.context_id}.jsonl"
            self.ctx_id_to_logger[context.context_id] = ConversationLogger(log_file)
            print(f"[Logger] Initialized at {log_file}")
            
            # 8. Planning Phase (optional, kept from original)
            planning_prompt = f"""Before starting the task, analyze it and create a plan.

Task: {task_instruction}

Provide your analysis in this format:
<json>
{{
    "action": "plan",
    "task_type": "question|action",
    "key_entities": ["entity1", "entity2"],
    "required_apps": {json.dumps(required_apps)},
    "execution_steps": [
        "Step 1: Description",
        "Step 2: Description"
    ],
    "data_to_collect": ["what data is needed"],
    "comparison_needed": "yes|no (if finding most/least/best)"
}}
</json>

Note: You already have user profile and credentials preloaded in your context.
After planning, we'll proceed with execution."""
            
            # Get planning response
            planning_messages = [
                messages[0],  # system prompt
                {"role": "user", "content": planning_prompt}
            ]
            
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
                    
                    # Add plan to message history
                    messages.append({"role": "assistant", "content": planning_content})
                    messages.append({
                        "role": "user",
                        "content": f"Good plan! Now execute it step by step. Task: {task_instruction}"
                    })
                    
                    # Log planning phase
                    logger = self.ctx_id_to_logger.get(context.context_id)
                    if logger:
                        logger.log_turn(0, plan, "Planning complete", "Initial task analysis")
                        
            except Exception as e:
                print(f"[Planning] Failed: {e}, proceeding without plan")
            
            print("="*80 + "\n")
        
        # ====================================================================================
        # MAIN EXECUTION LOOP
        # ====================================================================================
        
        # Add user input to messages (use structured step prompt if not first message)
        if len(messages) > 1:
            # Not first message - use structured step prompt
            task_match = re.search(r'<task>(.*?)</task>', user_input, re.DOTALL)
            task_instruction = task_match.group(1).strip() if task_match else "Complete the task"
            step_prompt = self.build_step_prompt(step_count, task_instruction, user_input)
            messages.append({"role": "user", "content": step_prompt})
        else:
            # First message - use raw input
            messages.append({"role": "user", "content": user_input})
        
        # Message compression (keep existing logic)
        MAX_MESSAGES = 20
        if len(messages) > MAX_MESSAGES:
            print(f"[Compression] {len(messages)} -> {MAX_MESSAGES} messages")
            system_msg = messages[0]
            initial_task_msg = messages[1] if len(messages) > 1 else None
            num_recent = min(12, len(messages) - 2)
            recent_messages = messages[-num_recent:]
            
            if len(messages) > 2 + num_recent:
                middle_messages = messages[2:-num_recent]
                summary_parts = []
                
                for msg in middle_messages:
                    content = msg.get("content", "")
                    if "credential" in content.lower() or "login" in content.lower():
                        summary_parts.append("Obtained credentials and logged in")
                    elif "playlist" in content:
                        summary_parts.append("Retrieved playlist data")
                    elif "show_song" in content:
                        summary_parts.append("Examined song details")
                
                summary_message = {
                    "role": "user",
                    "content": "=== Progress Summary ===\n" + "\n".join(dict.fromkeys(summary_parts))
                }
                
                if initial_task_msg:
                    messages_to_send = [system_msg, initial_task_msg, summary_message] + recent_messages
                else:
                    messages_to_send = [system_msg, summary_message] + recent_messages
            else:
                messages_to_send = [system_msg] + ([initial_task_msg] if initial_task_msg else []) + recent_messages
        else:
            messages_to_send = messages
        
        # Get OpenAI API key
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
            # Call LLM
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
            messages.append({"role": "assistant", "content": content})
            
            # Extract reasoning and action for logging
            try:
                json_match = re.search(r'<json>(.*?)</json>', content, re.DOTALL)
                if json_match:
                    action = json.loads(json_match.group(1))
                    reasoning = content.split('<json>')[0].strip() if '<json>' in content else ""
                    
                    # Log this turn
                    logger = self.ctx_id_to_logger.get(context.context_id)
                    if logger:
                        logger.log_turn(step_count, action, user_input[:200], reasoning)
            except:
                pass  # Logging is best-effort
            
            # Send response
            await event_queue.enqueue_event(
                new_agent_text_message(content, context_id=context.context_id)
            )
            
        except Exception as e:
            print(f"[LLM] Error calling OpenAI: {e}")
            import traceback
            traceback.print_exc()
            await event_queue.enqueue_event(
                new_agent_text_message(f"Error: {str(e)}", context_id=context.context_id)
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

