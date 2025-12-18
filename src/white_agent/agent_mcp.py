"""White agent implementation with MCP support (Approach III) - with Planning Phase."""

import uvicorn
import tomllib
import json
import os
import sys
import asyncio
import traceback
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

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


class ConversationLogger:
    """
    Responsible for saving conversation history, reasoning process, and execution results to a file.
    """
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.debug_log_file = filepath.replace(".jsonl", "_debug.log")
        
        # Console output logger
        self.console_logger = logging.getLogger("Agent")
        self.console_logger.setLevel(logging.INFO)
        if not self.console_logger.handlers:
            ch = logging.StreamHandler()
            ch.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
            self.console_logger.addHandler(ch)
            
        self.debug(f"Logger initialized. Debug logs: {self.debug_log_file}")

    def info(self, msg: str):
        self.console_logger.info(msg)
        self.debug(f"[INFO] {msg}")

    def error(self, msg: str):
        self.console_logger.error(msg)
        self.debug(f"[ERROR] {msg}")
        
    def debug(self, msg: str):
        """Write debug message to separate log file with immediate flush"""
        timestamp = datetime.now().isoformat()
        try:
            with open(self.debug_log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {msg}\n")
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            # Fallback to console if file write fails
            print(f"DEBUG LOG ERROR: {e}")

    def log_turn(self, step: int, memory_snapshot: List[Dict], action: Dict, observation: Dict):
        """Save detailed data of each turn to a JSONL file"""
        entry = {
            "timestamp": time.time(),
            "step": step,
            "memory_last_3": memory_snapshot[-3:] if len(memory_snapshot) > 3 else memory_snapshot,
            "action": action,
            "observation": observation
        }
        try:
            with open(self.filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            self.error(f"Failed to write log: {e}")


class PromptManager:
    """
    Manages all prompt logic.
    """
    def __init__(self, all_tool_names: List[str], planned_tools: List[str], relevant_tools: List[str], docs_summary: str, supervisor_data: Dict):
        self.all_tool_names = all_tool_names
        self.planned_tools = planned_tools
        self.relevant_tools = relevant_tools
        self.docs_summary = docs_summary
        self.profile = supervisor_data.get("profile", {})
        self.credentials = supervisor_data.get("credentials", [])

    def get_system_prompt(self, reasoning: str) -> str:
        """
        Constructs the System Prompt.
        """
        relevant_tools_str = "\n".join(['- ' + t for t in self.relevant_tools])
        profile_str = json.dumps(self.profile, ensure_ascii=False)
        creds_str = json.dumps(self.credentials, indent=2, ensure_ascii=False)
        
        prompt = f"""You are a helpful AI assistant operating in an AppWorld environment via MCP.
You have access to {len(self.all_tool_names)} tools.

[USER PROFILE]
User Profile: {profile_str}

[AVAILABLE CREDENTIALS]
(Use these strictly for login. Do not ask the user for passwords. Also, do not guess usernames, emails, passwords, etc.; obtain all necessary information from here.)
{creds_str}

=== PLANNING PHASE RESULTS ===
Based on analysis of the task, I have filtered down to {len(self.relevant_tools)} RELEVANT tools.

**PREDICTED EXECUTION PLAN:**
{chr(10).join(['  ' + str(i+1) + '. ' + t for i, t in enumerate(self.planned_tools[:15])])}

**REASONING:** {reasoning}

**DETAILED DOCUMENTATION (Key Tools):**
{self.docs_summary}

=== ALL RELEVANT TOOLS (USE THESE) ===
{relevant_tools_str}

[CRITICAL RULES - READ CAREFULLY]

0. **IMMEDIATE ANSWER SUBMISSION (HIGHEST PRIORITY)**:
   - AS SOON AS you have determined the final answer, you MUST call `supervisor__complete_task` IMMEDIATELY in the NEXT action.
   - DO NOT continue exploring or verifying after you've found the answer.
   - For "most-liked" queries: After checking all items, submit the one with the highest like_count.
   - Keep track of your best candidate as you process items.
   
   Example workflow:
   1. Get playlist library → extract all song_ids
   2. For each song: query details, compare like_count with current best
   3. After processing all songs → IMMEDIATELY submit: supervisor__complete_task(answer="Best Song Title")
   
   **TERMINATION IS MANDATORY:** Never exceed 25 steps without submitting an answer or reporting inability to complete.

1. **LOGIN PARAMETERS MAPPING (CRITICAL)**:
   - When a login tool asks for a `username`, you MUST use the `email` address from the credentials.
   - **DO NOT** use the `account_name` or app name (e.g., "spotify") as the username.
   - Example: If creds are `{{'account_name': 'spotify', 'email': 'bob@mail.com'}}`, you MUST call `login(username='bob@mail.com')`.

1.5. **DATA SCOPE CONSTRAINT**:
   - When asked about "songs in my playlists", you MUST ONLY consider songs that appear in the playlist library.
   - DO NOT query random song IDs that were not returned by show_playlist_library.
   - Process flow:
     1. Call show_playlist_library → get all playlists
     2. Extract all song_ids from all playlists
     3. ONLY query these specific song_ids
     4. Find the best match among these songs ONLY

2. **STATELESS API & TOKEN PERSISTENCE (MOST IMPORTANT)**:
   - **DO NOT RE-LOGIN**: Once you successfully log in and get an `access_token`, **YOU MUST REUSE IT** for all future steps. Do not call `login` again unless you receive a specific "401 Unauthorized" error.
   - **CHECK PARAMETER NAME**: Look at the schema. Is the required parameter named `access_token` or `token`? Use the EXACT name.
   - **PUBLIC vs PRIVATE TOOLS**:
     * **Private Tools** (Require Token): `login`, `update_...`, `create_...`, `delete_...`, `..._privates`, `review_...`, `show_liked_...`.
     * **Public Tools** (NO Token): `search_...`, `show_song`, `show_album`, `show_artist`, `show_..._reviews`.
   - **WARNING**: Only pass the token IF the tool explicitly accepts it in the schema. Do not force it into public tools.
   - If an API call fails with "401 Unauthorized", it implies you forgot the token.

3. **TERMINATION PROTOCOL (HOW TO SUBMIT)**:
   - **NEVER output `none` as a tool.** This causes an infinite loop.
   - You CANNOT stop just by finding the answer in your reasoning. You MUST submit it to the system.
   - **REQUIRED ACTION**: Use `supervisor.complete_task(answer='YOUR_ANSWER')` to finish the task.
   - If the task involves a change of state (e.g. sending an email), and no answer is required, use `complete_task(status='completed')` or check the schema for the correct argument.

4. **CHAINING OUTPUTS**: 
   - Always use the output of the previous step. 
   - Example: `search_song` returns `song_id`. Next step MUST be `play_song(song_id=...)`. 
   - **NO ID GUESSING**: Do not fabricate IDs (e.g., `song_id="123"`). You must find them first.

5. **DATA INTERPRETATION & "MOST-LIKED" UNDERSTANDING (CRITICAL)**:
   **PAY CLOSE ATTENTION to field types and meanings:**
   
   - **"most-liked song"** = song with HIGHEST like_count NUMBER
     → Field: "like_count": 18 (a number)
     → Meaning: How many people liked this song
   
   - **"liked song" (by you)** = song YOU personally liked
     → Field: "liked": true (a boolean)
     → Meaning: Whether YOU clicked "like"
   
   **These are COMPLETELY DIFFERENT! Do NOT confuse them!**
   
   When asked for "most-liked/most-popular/highest-rated":
   1. Identify the NUMERIC field (like_count, play_count, rating, etc.)
   2. Get details for ALL items to see this numeric field
   3. Compare the NUMBERS and find the maximum
   4. Do NOT stop at the first item with boolean liked=true
   
   **Example - WRONG approach:**
   Task: "Find most-liked song"
   ❌ Call show_liked_songs, find first song with liked: true
   ❌ Return that song
   
   **Example - CORRECT approach:**
   Task: "Find most-liked song"
   ✅ Get all songs from playlists to check
   ✅ Call show_song for ALL songs to get their like_count values
   ✅ Compare: Song A (like_count: 5), Song B (like_count: 18), Song C (like_count: 10)
   ✅ Return Song B (highest like_count: 18)
   
   **IMPORTANT - Data Analysis:**
   When tasks require finding "most/highest/best/least":
   1. Gather ALL relevant items first (check pagination!)
   2. Retrieve detailed information for EACH item
   3. Compare the specific NUMERIC metric (like_count, play_count, rating, etc.)
   4. Find the maximum/minimum based on NUMBERS, not boolean flags
   5. Do NOT rely on API names or ordering - always check the actual data fields
   
   **EFFICIENCY TIP - Smart Sampling:**
   - You don't always need to check EVERY item exhaustively
   - If you've checked a significant sample (e.g., 50%+ of items) and found a clear winner with a much higher value than others, you can confidently submit
   - Example: If song A has like_count=18 and you've checked 20 songs with none higher than 10, it's safe to submit song A
   - Balance thoroughness with efficiency to stay within step limits

6. **LOGIN FIRST**: 
   - If the first observation is a "401 Unauthorized" or "Login required", your IMMEDIATE next action must be to log in using the credentials provided above (remember Rule #1).

7. **ARGUMENT ACCURACY**: 
   - **ANTI-HALLUCINATION**: Before generating args, compare them against the tool definitions.
   - **ID Names**: Check if it requires `review_id` or `song_review_id`. Do not invent keys.
   - Ensure arguments match the tool schema exactly (e.g., integers for limits, correct string formats).
   - **COMMON TRAPS**: 
     * For reviews/ratings, the ID is usually `review_id` (NOT `song_review_id`).
     * The value to set is usually `rating` (NOT `new_rating`).
     * Status is usually `success` or `fail` (NOT `completed`).

8. **STEP-BY-STEP**: 
   - Don't try to do everything in one step. Search -> Verify -> Act -> Submit.

9. **CHECK BEFORE WRITING (AVOID 409/422 ERRORS)**:
   - Before rating or reviewing, ALWAYS call `show_..._reviews` first to check if you have already reviewed it.
   - **IF EXISTS**: Use `update_..._review` (using `review_id`).
   - **IF NOT EXISTS**: Use `review_...` or `create_...` (using `song_id`).
   - Do not blindly try to create; a 409 error means it already exists. A 422 error means you tried to update someone else's review.

10. **EFFICIENT LIST PROCESSING & PAGINATION**:
   - If you need to process a list of items (e.g., "rate all songs"), do it one by one efficiently.
   - **CRITICAL**: Do NOT log in between items. Use the SAME `access_token` for item 1, item 2, item 3...
   - **PAGINATION RULES (EXTREMELY IMPORTANT)**:
     * **page_index starts from 0, NOT 1!**
       - page_index=0, page_limit=20 → first 20 items (items 1-20)
       - page_index=1, page_limit=20 → next 20 items (items 21-40)
     * If you receive an empty list [], it most likely means:
       a) You used the wrong page_index (try 0 instead of 1)
       b) There is no more data (you've reached the end)
     * When calling library/list APIs, start with page_index=0 or omit page_index entirely
     * Check the API documentation for page_limit maximums (often 20 or 50)
   - When finding "most/least/best", you MUST iterate through ALL pages to get ALL items.

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
        return prompt

    def get_step_prompt(self, step: int, instruction: str, last_observation: str) -> str:
        """
        Constructs the User Prompt for each step.
        """
        # Extract hints from instruction for specific query types
        hint = ""
        if "most-liked" in instruction.lower() or "highest" in instruction.lower() or "most liked" in instruction.lower():
            hint = """
[PROGRESS TRACKING]
- Keep track of the BEST candidate found so far (title + like_count).
- After checking each item, mentally note: "Current best: [Title] with [N] likes"
- Once you've processed all items, IMMEDIATELY submit the best one using supervisor__complete_task.
            """
        elif "least" in instruction.lower() or "lowest" in instruction.lower():
            hint = """
[PROGRESS TRACKING]
- Keep track of the candidate with the LOWEST value found so far.
- After checking each item, mentally note: "Current lowest: [Title] with [N] value"
- Once you've processed all items, IMMEDIATELY submit it using supervisor__complete_task.
            """
        
        prompt = f"""
        [TASK INSTRUCTION]
        {instruction}
        
        [CURRENT STATUS]
        Step: {step} / 30
        {hint}
        
        [LAST OBSERVATION]
        {last_observation}
        
        [INSTRUCTION FOR NEXT STEP]
        Based on the Last Observation:
        1. If it was an ERROR: Analyze why it failed. Do not repeat the exact same parameters. Change your approach or fix the arguments.
        2. If it was SUCCESS: Proceed to the next logical step.
        3. If you found IDs: Use them in the next action.
        4. If you found the answer: IMMEDIATELY call supervisor__complete_task(answer='...').
        
        Generate the next JSON response now.
        """
        return prompt.strip()


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
        self.logger = None
        self.prompt_manager = None
        self.step_count = 0
        
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

    async def preload_context(self, relevant_tools: List[str]) -> Dict:
        """Fetch supervisor data (profile and credentials) based on relevant tools."""
        print("[Context] Pre-loading user context from supervisor...")
        data = {"profile": {}, "credentials": []}
        
        # Determine relevant apps from relevant tools
        relevant_apps = set()
        for tool in relevant_tools:
            if "__" in tool:
                app = tool.split("__")[0]
                relevant_apps.add(app)
        
        try:
            # 1. Fetch Profile
            print("[Context] Fetching user profile...")
            p_result = self.mcp_client.call_tool("supervisor__show_profile", arguments={})
            if not isinstance(p_result, dict) or p_result.get("response", {}).get("is_error"):
                print(f"[Context] Warning: Failed to fetch profile: {p_result}")
            else:
                data["profile"] = p_result
                
            # 2. Fetch Passwords
            print("[Context] Fetching credentials...")
            c_result = self.mcp_client.call_tool("supervisor__show_account_passwords", arguments={})
            
            # Helper to check error in MCP result
            def is_error(res):
                if not isinstance(res, dict): return False
                # Standard MCP error might be in top level or inside 'response'
                if res.get("is_error"): return True
                
                response = res.get("response")
                if isinstance(response, dict) and response.get("is_error"): return True
                return False
            
            if is_error(c_result):
                 print(f"[Context] Warning: Failed to fetch credentials: {c_result}")
            else:
                # Filter credentials based on relevant apps
                all_creds = []
                
                # Check for wrapped result
                if isinstance(c_result, dict) and "account_name" not in c_result and "response" in c_result:
                    # Wrapped in {response: [...]} or {response: {result: [...]}}?
                    # Since is_error checked res.get("response").get("is_error"), 
                    # let's assume valid data might also be in "response" or "result".
                    # But usually list tools return list directly if not error?
                    # Let's inspect c_result structure more safely
                    possible_list = c_result.get("response")
                    if isinstance(possible_list, list):
                        all_creds = possible_list
                    elif isinstance(c_result, list):
                        all_creds = c_result
                elif isinstance(c_result, list):
                    all_creds = c_result
                
                filtered_creds = []
                for cred in all_creds:
                    if not isinstance(cred, dict): continue
                    acct_name = str(cred.get("account_name", "")).lower()
                    
                    # Keep if it matches any relevant app or is supervisor
                    if any(app in acct_name for app in relevant_apps) or "supervisor" in acct_name:
                        filtered_creds.append(cred)
                
                data["credentials"] = filtered_creds
                print(f"[Context] ✓ Loaded {len(filtered_creds)} credentials")
                
        except Exception as e:
            print(f"[Context] ✗ Error pre-loading context: {e}")
            traceback.print_exc()
            
        return data

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

IMPORTANT GUIDELINES:
1. Use the EXACT tool names from the list above. Do NOT modify or guess names.
2. If the task asks for "most-liked", "most-popular", "highest-rated", etc.:
   - You need tools that return NUMERIC fields (like_count, play_count, rating)
   - Choose tools like "show_song", "show_album", "show_playlist" to get detailed info
   - AVOID "show_liked_songs" - that returns songs YOU liked (boolean), not songs with highest like_count (number)
3. To compare items, you'll need to:
   - First get a list of items (e.g., show_playlist_library)
   - Then get details for EACH item (e.g., show_song for each song_id)
   - Compare the numeric values to find max/min

Respond with JSON:
```json
{{
  "selected_tools": ["tool1", "tool2", "tool3", ...],
  "reasoning": "Brief explanation of the plan"
}}
```
"""
        
        try:
            model = os.environ.get("WHITE_AGENT_MODEL", "gpt-4o")
            kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": planning_prompt}],
            }
            if not model.startswith("o1") and not model.startswith("o3") and "gpt-5" not in model:
                kwargs["temperature"] = 0

            response = self.client.chat.completions.create(**kwargs)
            
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
                        if len(doc_str) > 2000:
                            doc_str = doc_str[:2000] + "...(truncated)"
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
        if self.log_file is None:
            import re
            task_id_match = re.search(r'<task_id>(.*?)</task_id>', user_input, re.DOTALL)
            if task_id_match:
                task_id = task_id_match.group(1).strip()
                self.log_file = f"/tmp/mcp_tool_calls_{task_id}.jsonl"
            else:
                context_id = context.context_id or "unknown"
                self.log_file = f"/tmp/mcp_tool_calls_{context_id}.jsonl"
            
            print(f"[White Agent MCP] Log file initialized: {self.log_file}")
            self.logger = ConversationLogger(self.log_file)
            
        if self.logger:
            self.logger.debug(f"=== INCOMING REQUEST ===")
            self.logger.debug(f"User Input Length: {len(user_input)}")
            self.logger.debug(f"User Input Preview: {user_input[:200]}...")
            self.logger.debug(f"Current History Length: {len(self.history)}")
        
        # Parse input to check for MCP URL and task
        import re
        mcp_url_match = re.search(r'MCP Server URL: (http://\S+)', user_input)
        
        if mcp_url_match and not self.mcp_client:
            if self.logger: self.logger.debug("Found MCP URL, initializing connection...")
            mcp_url = mcp_url_match.group(1)
            await self.connect_to_mcp(mcp_url)
            
            # Initialize system prompt with Planning Phase if connected
            if self.mcp_client:
                # Extract task instruction for planning
                task_match = re.search(r'<task>(.*?)</task>', user_input, re.DOTALL)
                task_instruction = task_match.group(1).strip() if task_match else ""
                
                print(f"[White Agent MCP] Task extraction: {'SUCCESS' if task_instruction else 'FAILED'}")
                if self.logger: self.logger.debug(f"Extracted Task: {task_instruction}")
                
                # Perform Planning Phase
                planning_result = None
                if task_instruction:
                    print("[White Agent MCP] Starting Planning Phase...")
                    try:
                        planning_result = await self.plan_task(task_instruction)
                    except Exception as e:
                        print(f"[White Agent MCP] ✗ Planning Phase failed: {e}")
                        if self.logger: self.logger.error(f"Planning Phase Failed: {e}")
                        traceback.print_exc()
                
                # Perform Context Pre-loading
                relevant_tools = planning_result['relevant_tools'] if planning_result else self.all_tool_names
                supervisor_data = await self.preload_context(relevant_tools)
                
                # Initialize PromptManager
                planned_tools = planning_result['planned_tools'] if planning_result else []
                docs_summary = planning_result['docs_summary'] if planning_result else ""
                reasoning = planning_result['reasoning'] if planning_result else "No planning performed."
                
                self.prompt_manager = PromptManager(
                    self.all_tool_names,
                    planned_tools,
                    relevant_tools,
                    docs_summary,
                    supervisor_data
                )
                
                system_content = self.prompt_manager.get_system_prompt(reasoning)
                self.history = [{"role": "system", "content": system_content}]
                if self.logger: self.logger.debug(f"System Prompt Initialized (Len: {len(system_content)})")

        # Update history
        is_new_instruction = False
        if not self.history:
            is_new_instruction = True
        elif "<task>" in user_input and len(self.history) < 2:
            is_new_instruction = True
            
        if is_new_instruction:
            if self.logger: self.logger.debug("Processing as NEW instruction")
            # First turn: Extract task and format initial prompt
            task_match = re.search(r'<task>(.*?)</task>', user_input, re.DOTALL)
            clean_task = task_match.group(1).strip() if task_match else user_input
            initial_msg = f"Task: {clean_task}\n\nPlease start by analyzing the task and choosing the first tool."
            self.history.append({"role": "user", "content": initial_msg})
            
            self.step_count = 1
            print(f"[White Agent MCP] --- Step {self.step_count} (Start) ---")
            
        else:
             print(f"[White Agent MCP] Ignoring trigger message from Green Agent to prevent history pollution.")
             if self.logger: self.logger.debug("Ignoring trigger message (History exists)")
             
             # Subsequent turns: DO NOT add step prompt
             # The tool result has already been added to history in the previous cycle
             # We should just proceed to call the LLM with existing history
             self.step_count += 1
             print(f"[White Agent MCP] --- Step {self.step_count} ---")
             
             # Check what's in history
             if self.logger:
                 if len(self.history) >= 2:
                     last_msg = self.history[-1]
                     self.logger.debug(f"Last message in history: role={last_msg['role']}, content_preview={last_msg['content'][:200]}...")
                 else:
                     self.logger.debug(f"History has {len(self.history)} messages")

        # Generate response
        print(f"[White Agent MCP] Processing message...")
        
        try:
            model = os.environ.get("WHITE_AGENT_MODEL", "gpt-4o")
            kwargs = {
                "model": model,
                "messages": self.history,
            }
            if not model.startswith("o1") and not model.startswith("o3") and "gpt-5" not in model:
                kwargs["temperature"] = 0

            if self.logger: 
                self.logger.debug(f"Calling LLM: {model}")
                self.logger.debug(f"Message Count: {len(self.history)}")
            
            start_llm = time.time()
            response = self.client.chat.completions.create(**kwargs)
            duration_llm = time.time() - start_llm
            
            if self.logger: self.logger.debug(f"LLM Response Received in {duration_llm:.2f}s")
            
            content = response.choices[0].message.content
            
            # Handle empty LLM response
            if not content or content.strip() == "":
                if self.logger: self.logger.debug("LLM returned empty content")
                
                # Check if task was recently completed
                task_completed = False
                if len(self.history) >= 2:
                    for msg in reversed(self.history[-5:]):  # Check last 5 messages
                        if msg.get("role") == "user" and "supervisor__complete_task" in msg.get("content", ""):
                            task_completed = True
                            if self.logger: self.logger.debug("Detected task completion, breaking loop")
                            break
                
                if task_completed:
                    content = "Task has been completed. No further action needed."
                else:
                    # Empty for unknown reason - prompt LLM to continue
                    content = "Please provide your next action in JSON format."
                    if self.logger: self.logger.debug("Prompting LLM to continue after empty response")
            
            self.history.append({"role": "assistant", "content": content})
            
            print(f"[White Agent MCP] Generated response: {content[:100]}...")
            if self.logger: self.logger.debug(f"LLM Content: {content}")
            
            # Check for tool calls
            tags = parse_tags(content)
            
            # Also support markdown json blocks
            if "json" not in tags:
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
                if not json_match:
                     json_match = re.search(r'```\s*(\{.*?\})\s*```', content, re.DOTALL)
                if json_match:
                    tags["json"] = json_match.group(1)
            
            # Support raw JSON if it looks like a JSON object
            if "json" not in tags:
                # Try to extract raw JSON
                potential_json = content.strip()
                if potential_json.startswith("{") and potential_json.endswith("}"):
                    # Handle common formatting errors: extra closing braces
                    try:
                        json.loads(potential_json)
                        tags["json"] = potential_json
                    except json.JSONDecodeError:
                        # Try to fix common issues
                        # 1. Remove trailing extra braces
                        if potential_json.endswith("}}}"):
                            fixed_json = potential_json.rstrip("}") + "}"
                            try:
                                json.loads(fixed_json)
                                tags["json"] = fixed_json
                                if self.logger:
                                    self.logger.debug(f"Fixed JSON by removing extra braces")
                            except:
                                pass
            
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
                        
                        if self.logger:
                            self.logger.debug(f"Executing Tool: {tool_name}")
                            self.logger.debug(f"Arguments: {args}")
                        
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
                            if self.logger: self.logger.debug(f"Tool Result Payload (First 1000 chars): {json.dumps(result, default=str)[:1000]}...")
                            
                            # Smart truncation: keep only essential fields to reduce context pollution
                            result_for_llm = result
                            if tool_name == "spotify__show_song" and isinstance(result.get("response"), dict):
                                # Only keep essential fields for song queries
                                song_data = result["response"]
                                result_for_llm = {
                                    "response": {
                                        "song_id": song_data.get("song_id"),
                                        "title": song_data.get("title"),
                                        "like_count": song_data.get("like_count"),
                                        "rating": song_data.get("rating"),
                                        # Omit: artists, album details, play_count, etc. to reduce context
                                    }
                                }
                                if result.get("is_error"):
                                    result_for_llm["is_error"] = result["is_error"]
                                if self.logger:
                                    self.logger.debug(f"Truncated song data to essential fields only")
                            
                            elif tool_name == "spotify__show_playlist_library":
                                # If too many playlists, keep full data but truncate long lists
                                if isinstance(result.get("response"), list) and len(result["response"]) > 10:
                                    result_for_llm = {
                                        "response": result["response"][:10] + [{"truncated": f"({len(result['response']) - 10} more playlists - use pagination to access)"}]
                                    }
                                    if result.get("is_error"):
                                        result_for_llm["is_error"] = result["is_error"]
                                    if self.logger:
                                        self.logger.debug(f"Truncated playlist library to first 10 items")
                            
                            # Provide enhanced error feedback to LLM
                            if isinstance(result.get("response"), dict) and result.get("response", {}).get("is_error"):
                                error_msg = result["response"].get("message", "Unknown error")
                                tool_result_msg = f"""❌ Tool '{tool_name}' returned an ERROR:
{json.dumps(result_for_llm, indent=2, default=str)}

ANALYSIS & GUIDANCE:
- Error: {error_msg}
- Action: Check the tool schema and correct your parameters
- If this is a validation error, review the valid ranges/formats (e.g., page_limit max might be 20)
- If this is an authentication error, ensure you passed the access_token

Please try again with corrected parameters."""
                                if self.logger: self.logger.debug(f"Error detected in tool result, providing enhanced feedback")
                            
                            elif isinstance(result.get("response"), list) and len(result["response"]) == 0 and "library" in tool_name.lower():
                                # Special case: empty list from library/list queries
                                tool_result_msg = f"""⚠️ Tool '{tool_name}' returned an EMPTY list: []

POSSIBLE CAUSES:
1. **Wrong page_index**: Pagination usually starts from 0, not 1. If you used page_index=1, try page_index=0 instead.
2. No data exists for this query.
3. Missing or invalid access_token.

Please verify your parameters (especially page_index) and try again."""
                                if self.logger: self.logger.debug(f"Empty library response, providing guidance")
                            
                            else:
                                # Normal successful response
                                tool_result_msg = f"Tool '{tool_name}' returned:\n{json.dumps(result_for_llm, indent=2, default=str)}"
                            
                            # Append result to history
                            self.history.append({"role": "user", "content": tool_result_msg})
                            
                        except Exception as e:
                            success = False
                            result = {"error": str(e)}
                            
                            print(f"[Real MCP] ✗ Tool call failed: {e}")
                            if self.logger: self.logger.error(f"Tool Call Failed: {e}")
                            
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
                            if self.logger:
                                self.logger.log_turn(self.step_count, self.history[:-1], log_entry, {"result": result})
                            else:
                                try:
                                    with open(self.log_file, "a") as f:
                                        f.write(json.dumps(log_entry, default=str) + "\n")
                                except Exception as log_error:
                                    print(f"[White Agent MCP] Warning: Failed to write log: {log_error}")
                            
                except json.JSONDecodeError as e:
                    if self.logger: self.logger.error(f"JSON Decode Error for Action: {e}")
                    
                    # Provide feedback to LLM about the JSON error
                    error_feedback = f"ERROR: Your last response had invalid JSON format: {str(e)}\nPlease generate a valid JSON response with correct syntax. Ensure all braces and quotes are properly matched."
                    self.history.append({"role": "user", "content": error_feedback})
                    if self.logger: self.logger.debug("Added JSON error feedback to history")
                    # Continue loop to let LLM retry
            
            # Send response back to Green Agent
            if self.logger: self.logger.debug("Enqueuing response to Green Agent...")
            await event_queue.enqueue_event(
                new_agent_text_message(content)
            )
            if self.logger: self.logger.debug("Response enqueued.")
            
        except Exception as e:
            print(f"Error generating response: {e}")
            traceback.print_exc()
            if self.logger: self.logger.error(f"Error Generating Response: {e}")
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
