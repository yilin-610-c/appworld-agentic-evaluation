# Conversation History Compression v0.4.0

## 修复时间
2024-11-13

## 问题描述

在长时间对话中遇到Rate Limit错误：

```
Rate limit reached for gpt-4o:
Limit 30000 TPM, Used 23730, Requested 6600
Total: 30330 > 30000 ❌
```

## 根本原因

### OpenAI API的无状态特性

**关键概念**: OpenAI API **不保存任何对话历史**！

```
ChatGPT网页版: 会"记住"你的对话历史
OpenAI API: 每次调用都是全新的，完全忘记之前的内容
```

### 我们如何实现"记忆"？

通过在**我们的代码中**维护对话历史，然后每次都把整个历史发送给OpenAI：

```python
# 在我们的内存中保存对话
messages = self.ctx_id_to_messages[context.context_id]

# 每次都发送完整历史
response = completion(
    messages=messages,  # ← 包含所有之前的对话！
    model="openai/gpt-4o",
    ...
)
```

### Token累积问题

**Step 1**:
```python
messages = [system_prompt, user_msg1]
发送: 2500 tokens
```

**Step 5**:
```python
messages = [system_prompt, user_msg1, assistant_msg1, user_msg2, ..., user_msg5]
发送: 8000 tokens
```

**Step 10**:
```python
messages = [system_prompt, user_msg1, ..., user_msg10]
发送: 23730 tokens
再加上GPT要生成的: 6600 tokens
总计: 30330 > 30000 limit 💥
```

## 解决方案：对话历史压缩

### 核心思想

不是发送**完整历史**，而是发送：
- System prompt（必需）
- **之前对话的总结**（压缩！）
- 最近的对话（保持上下文）

### 实现原理

```python
# 原始历史（20条消息）
original = [system, msg1, msg2, ..., msg19, msg20]

# 压缩后（12条消息）
compressed = [
    system,                    # 保留
    "Summary: earlier steps",  # 总结 msg1-msg10
    msg11, msg12, ..., msg20   # 保留最近10条
]

# Token使用: 23730 → ~12000 ✅
```

### 代码实现

**文件**: `src/white_agent/agent.py`  
**位置**: 第112-161行

#### 关键参数

```python
MAX_MESSAGES = 12  # 系统提示 + 总结 + 最近10条消息
```

为什么是12？
- 1条 system prompt
- 1条 summary
- 10条 最近对话（5轮user+assistant）

#### 压缩逻辑

```python
if len(messages) > MAX_MESSAGES:
    # 1. 保留system prompt
    system_msg = messages[0]
    
    # 2. 保留最近10条消息
    recent_messages = messages[-(MAX_MESSAGES - 2):]
    
    # 3. 总结中间的对话
    middle_messages = messages[1:-(MAX_MESSAGES - 2)]
    summary_parts = []
    
    for msg in middle_messages:
        if "API call result" in msg["content"]:
            summary_parts.append("- Called APIs and received results")
        elif "call_api" in msg["content"]:
            summary_parts.append("- Made API calls to gather information")
    
    summary_text = "Previous conversation summary:\n" + "\n".join(unique_summary)
    
    # 4. 重构消息列表
    compressed_messages = [system_msg, summary_message] + recent_messages
```

#### 使用压缩后的消息

```python
response = completion(
    messages=messages_to_send,  # 使用压缩后的消息！
    model="openai/gpt-4o",
    ...
)
```

## 额外改进：添加Retry

同时添加了`num_retries=3`来处理临时的rate limit：

```python
response = completion(
    messages=messages_to_send,
    model="openai/gpt-4o",
    temperature=0.0,
    api_key=api_key,
    num_retries=3,  # ← 新增：自动重试
)
```

当遇到rate limit时，LiteLLM会：
1. 等待一小段时间
2. 自动重试
3. 最多重试3次

## 工作原理示例

### 场景：第13步的对话

**没有压缩**（会失败）:
```python
messages = [
    system_prompt,        # 1500 tokens
    task,                 # 1000 tokens
    assistant_response_1, # 200 tokens
    api_result_1,         # 500 tokens
    assistant_response_2, # 200 tokens
    ...                   # 继续累积
    api_result_12,        # 800 tokens
]
# 总计: 30000+ tokens → Rate Limit! ❌
```

**有压缩**（成功）:
```python
messages_to_send = [
    system_prompt,                    # 1500 tokens
    "Summary: earlier steps...",      # 200 tokens
    api_result_3,                     # 500 tokens
    assistant_response_3,             # 200 tokens
    ...                               # 最近5轮
    api_result_12,                    # 800 tokens
]
# 总计: ~12000 tokens → 成功! ✅
```

### LLM仍然能理解上下文！

因为LLM可以从总结中理解之前发生了什么：

```
Summary: Previous conversation summary:
- Called APIs and received results
- Made API calls to gather information

[最近的对话...]
User: API result: [data from step 10]
Assistant: Let me analyze this...
User: API result: [data from step 11]
```

LLM知道：
- ✅ 之前已经调用过一些APIs
- ✅ 当前在分析最新的数据
- ✅ 需要继续完成任务

## 效果对比

### Before（无压缩）

```
Step 1-9: 正常运行
Step 10: Rate Limit Error 💥
→ 对话中断
→ Agent无法完成推理
→ 可能返回错误答案
```

### After（有压缩）

```
Step 1-11: 正常运行
Step 12: 触发压缩
  Compressing: 24 messages → 12 messages
  Summary: Previous conversation summary: ...
  Kept recent 10 messages
Step 13-20: 继续正常运行 ✅
```

## 配置参数

可以根据需要调整：

```python
MAX_MESSAGES = 12  # 基础配置（推荐）

# 如果仍然遇到rate limit，可以减小：
MAX_MESSAGES = 10  # 更激进的压缩

# 如果想保留更多上下文：
MAX_MESSAGES = 16  # 更宽松的压缩
```

## 权衡考虑

### 优点 ✅

1. **避免Token限制** - 不会超过TPM上限
2. **避免Rate Limit** - 减少token使用
3. **节省成本** - 更少的tokens = 更低的费用
4. **保持性能** - LLM仍能理解上下文

### 潜在缺点 ⚠️

1. **可能丢失细节** - 总结不如完整历史详细
2. **总结质量依赖实现** - 当前是简单的关键词匹配

但对于我们的用例，这些缺点影响很小，因为：
- Agent主要需要最近的上下文
- 早期的API调用结果通常不需要再次引用

## 测试验证

```bash
cd /home/lyl610/green1112/appworld
export OPENAI_API_KEY="your-key-here"
python ../appworld_green_agent/main.py launch --task-id 82e2fac_1
```

### 预期输出

```
--- Step 11 ---
Sending message to white agent...
INFO: White agent response...

--- Step 12 ---
Compressing message history: 24 -> 12 messages
Summary: Previous conversation summary:
- Called APIs and received results
- Made API calls to gather information
Kept recent 10 messages
Sending message to white agent...
INFO: White agent response...

--- Step 13+ ---
继续正常运行... ✅
```

## 未来改进

### 1. 智能总结

使用LLM来总结对话（而不是关键词匹配）：

```python
def create_intelligent_summary(middle_messages):
    # 使用便宜的模型（如gpt-3.5-turbo）来总结
    summary_prompt = "Summarize these conversation steps briefly:"
    ...
    return summary
```

### 2. 动态阈值

根据实际token使用动态调整：

```python
def calculate_token_count(messages):
    # 估算token数量
    return sum(len(msg["content"]) / 4 for msg in messages)

if calculate_token_count(messages) > 20000:
    # 触发压缩
    ...
```

### 3. 选择性保留

保留关键信息（如凭据、重要API结果）：

```python
important_messages = []
for msg in middle_messages:
    if "credential" in msg["content"] or "login" in msg["content"]:
        important_messages.append(msg)
```

## 相关文件

- `src/white_agent/agent.py` - 第112-183行

## 版本历史

- v0.2.2 - API结果传递修复
- v0.3.0 - Prompt engineering
- v0.3.1 - 答案提交修复
- v0.3.2 - 答案格式优化
- v0.3.3 - 数据分析指导
- v0.4.0 - **对话历史压缩 + Retry机制**

## 经验教训

1. **理解API的工作原理很重要** - OpenAI API是无状态的
2. **Token管理是关键** - 长对话需要主动管理
3. **总结比完整历史更高效** - LLM能理解压缩的上下文
4. **Retry是必要的** - 网络/rate limit问题不可避免

🎉 现在系统可以处理更长的对话而不会遇到token限制了！


