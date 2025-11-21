# Prompt Engineering Fix v0.3.0

## 修复时间
2024-11-13

## 问题描述

White agent在Step 3时出现两个关键问题：

```
White agent: "Please provide your Spotify username and password for the login process."
Error: No JSON found in response
```

### 问题分析

1. **没有使用supervisor获取凭据** - 向人类请求密码，而不是从supervisor API获取
2. **违反JSON格式协议** - 返回纯文本而不是JSON

### 根本原因

- ❌ White agent没有system prompt来指导行为
- ❌ 初始消息没有充分强调supervisor的作用
- ❌ 没有容错机制处理格式错误

## 解决方案

### 1. 为White Agent添加System Prompt

**文件**: `src/white_agent/agent.py`  
**位置**: 第51-83行

**改进**: 在第一条消息前插入system prompt

```python
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
...
Remember: ALWAYS wrap your response in <json>{"action": "...", ...}</json>"""
    })
```

**关键效果**:
- ✅ 明确告知这是自动化环境
- ✅ 指出supervisor是获取凭据的来源
- ✅ 强制要求JSON格式
- ✅ 提供具体的工作流程示例

### 2. 改进Green Agent的初始消息

**文件**: `src/green_agent/agent.py`  
**位置**: 第125-185行

**改进**: 增加"IMPORTANT CONTEXT"部分，强调supervisor

```python
**IMPORTANT CONTEXT:**
- You are operating in an automated AppWorld environment
- DO NOT ask humans for any information (passwords, usernames, etc.)
- Use the 'supervisor' app to access credentials and personal information
- The supervisor has access to all login credentials for various services
- Example: To login to Spotify, first get credentials from supervisor APIs

...

**Step 1: Discover available apps**
   ...
   IMPORTANT: The 'supervisor' app contains credentials for all services!

**Step 2: Get APIs for the relevant apps**
   ...
   For credentials: api_docs.show_api_descriptions(app_name='supervisor')

**Step 4: Call the actual APIs**
   Example workflow for accessing Spotify:
   1. Get credentials: supervisor.show_credentials() (or similar supervisor API)
   2. Login: spotify.login(username='...', password='...')
   3. Use other Spotify APIs to complete your task
```

**关键效果**:
- ✅ 在多处强调supervisor的重要性
- ✅ 提供完整的工作流程示例
- ✅ 明确说明不要向人类请求信息

### 3. 添加容错处理

**文件**: `src/green_agent/agent.py`  
**位置**: 第236-261行

**改进**: 当检测到没有JSON时，发送提醒而不是终止

```python
if "json" not in tags:
    print("Error: No JSON found in response")
    # Send a reminder message instead of breaking immediately
    initial_message = """ERROR: You must respond with JSON wrapped in <json>...</json> tags.

Reminder of the correct format:
<json>
{"action": "call_api", "api_name": "...", "parameters": {...}}
</json>
...
Please respond again with the proper JSON format."""
    continue  # Continue loop instead of breaking
```

**关键效果**:
- ✅ 给white agent纠正错误的机会
- ✅ 提供具体的格式示例
- ✅ 不会因为一次错误就终止整个评估

## 预期改进的交互流程

### 之前的错误流程

```
Step 1: 调用 api_docs.show_app_descriptions() ✅
Step 2: 调用 api_docs.show_api_descriptions(app_name='spotify') ✅
Step 3: "Please provide your Spotify username and password" ❌
        Error: No JSON found ❌
        评估终止 ❌
```

### 现在的正确流程

```
Step 1: 调用 api_docs.show_app_descriptions() ✅
        看到: [{"name": "supervisor", ...}, {"name": "spotify", ...}]

Step 2: 调用 api_docs.show_api_descriptions(app_name='supervisor') ✅
        看到: [{"name": "show_profile", ...}, {"name": "show_credentials", ...}]

Step 3: 调用 supervisor.show_credentials() ✅
        获得: {"spotify": {"username": "...", "password": "..."}}

Step 4: 调用 api_docs.show_api_descriptions(app_name='spotify') ✅
        看到: [{"name": "login", ...}, {"name": "show_playlist_library", ...}]

Step 5: 调用 spotify.login(username="...", password="...") ✅
        返回: {"status": "success", "token": "..."}

Step 6: 调用 spotify.show_playlist_library() ✅
        获取播放列表数据

Step 7: 分析数据，找出最喜欢的歌曲

Step 8: 返回答案 ✅
        {"action": "answer", "content": "Song Title"}
```

## 关键改进点

### Prompt Engineering原则

1. **明确环境上下文** - "You are in an AUTOMATED environment"
2. **提供反面示例** - "NEVER say 'please provide your password'"
3. **提供正面示例** - "Use supervisor.show_credentials()"
4. **重复关键信息** - supervisor在多处被强调
5. **容错和引导** - 格式错误时提供纠正指导

### System Prompt vs User Message

- **System Prompt** (white agent内部)
  - 设定agent的角色和行为准则
  - 持久性指导，贯穿整个对话
  - 更强的约束力

- **User Message** (green agent发送)
  - 提供具体任务和可用工具
  - 补充上下文和示例
  - 任务级指导

两者配合才能达到最佳效果！

## 测试验证

```bash
cd /home/lyl610/green1112/appworld
export OPENAI_API_KEY="your-key-here"
python ../appworld_green_agent/main.py launch --task-id 82e2fac_1
```

### 预期看到的输出

```
--- Step 1 ---
Executing: api_docs.show_app_descriptions
API Result: [{'name': 'supervisor', ...}, {'name': 'spotify', ...}]

--- Step 2 ---
White agent: "我看到有supervisor和spotify，让我先查supervisor的APIs获取凭据"
Executing: api_docs.show_api_descriptions(app_name='supervisor')
API Result: [{'name': 'show_profile', ...}, {'name': 'show_credentials', ...}]

--- Step 3 ---
White agent: "好的，让我获取Spotify的凭据"
Executing: supervisor.show_credentials
API Result: {'spotify': {'username': '...', 'password': '...'}}

--- Step 4 ---
White agent: "有了凭据，现在查询Spotify的APIs"
Executing: api_docs.show_api_descriptions(app_name='spotify')
...
```

## 经验教训

1. **LLM需要明确的行为指导** - 不能假设它知道这是自动化环境
2. **System prompt很重要** - 比在user message中说明更有效
3. **重复关键信息** - supervisor需要在多处强调才能引起注意
4. **提供反例和正例** - "不要做X，应该做Y"
5. **容错机制必不可少** - 一次错误不应该导致整个评估失败

## 相关文件

- `src/white_agent/agent.py` - 添加system prompt（第53-78行）
- `src/green_agent/agent.py` - 改进初始消息（第131-184行）、添加容错（第236-261行）

## 版本历史

- v0.2.2 - 修复API结果传递问题（print机制）
- v0.3.0 - Prompt engineering改进（supervisor使用、JSON格式、容错）

## 下一步

如果white agent仍然不能正确使用supervisor：
1. 检查supervisor APIs的实际名称（可能不是show_credentials）
2. 在初始消息中提供更具体的supervisor API示例
3. 考虑在system prompt中添加更多示例对话

🚀 准备测试！


