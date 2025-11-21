# Improved Compression Strategy v0.4.1

## 修改时间
2024-11-13

## 之前的问题（v0.4.0）

### 症状
```
Step 8: White agent返回
{"action": "provide_final_answer", ...}  ❌ 错误格式

Green agent: Unknown action: provide_final_answer
Result: Task failed
```

### 根本原因

**压缩过于激进，丢失了关键上下文**：

```
原始消息:
[system_prompt, initial_task, msg3, msg4, ..., msg13, msg14]

v0.4.0压缩 (MAX_MESSAGES=12):
[system_prompt, summary, msg5, msg6, ..., msg13, msg14]
              ↑ 丢失了 initial_task！

初始任务消息包含:
- 任务描述（"find the most-liked song"）
- 通信协议（{"action": "call_api", ...}）
- 工具列表和使用说明

全部被压缩掉了！❌
```

### White Agent的困惑

```
White Agent看到的上下文:
- System: "你是一个AI agent..."
- Summary: "Made API calls..." (太简单)
- Recent: [一些API调用和结果]

White Agent思考: 
"我完成了API调用，应该返回了...但具体格式是什么来着？"
→ 编造了一个格式: {"action": "provide_final_answer", ...}
→ 失败 ❌
```

## 新的三层保留策略 v0.4.1

### 核心理念

**不是所有消息都同等重要！**

```
重要性级别:
Level 1 (关键): System prompt + Initial task  → 永远保留
Level 2 (可压缩): 中间的API交互            → 压缩为总结
Level 3 (上下文): 最近的对话               → 完整保留
```

### 实现细节

#### 参数调整

```python
MAX_MESSAGES = 20  # 从12增加到20
```

为什么是20？
- 给予更多buffer，不要过早压缩
- 平衡token使用和上下文保留

#### 三层结构

```python
if len(messages) > 20:
    # Layer 1: 永远保留（关键信息）
    system_msg = messages[0]           # System prompt
    initial_task_msg = messages[1]     # 任务描述 + 协议
    
    # Layer 3: 必须保留（当前上下文）
    recent_messages = messages[-12:]   # 最近12条（6轮对话）
    
    # Layer 2: 可以压缩（历史记录）
    middle_messages = messages[2:-12]  # 中间的所有消息
    summary = create_summary(middle_messages)
    
    # 重构
    compressed = [system_msg, initial_task_msg, summary] + recent_messages
```

#### 智能总结

不再是简单的关键词匹配，而是提取有意义的进度：

```python
Summary包含:
1. 进度摘要
   - "Obtained user credentials"
   - "Successfully authenticated"
   - "Retrieved playlist information"
   - "Examined song details"

2. 协议提醒（关键！）
   === Protocol Reminder ===
   Use: {"action": "call_api", "api_name": "...", "parameters": {...}}
   Or: {"action": "answer", "content": "your answer"}
   Always wrap in <json>...</json> tags
```

### 压缩后的结构

```python
messages_to_send = [
    # Layer 1: 关键上下文（永远保留）
    {
        "role": "system",
        "content": "You are an AI agent... [完整的system prompt]"
    },
    {
        "role": "user",
        "content": "Your task is: find most-liked song... [完整的任务和协议]"
    },
    
    # Layer 2: 历史压缩
    {
        "role": "user",
        "content": """=== Progress Summary ===
Obtained user credentials
Successfully authenticated
Retrieved playlist information

=== Protocol Reminder ===
Use: {"action": "call_api", ...}
Or: {"action": "answer", "content": "..."}
Always wrap in <json>...</json> tags"""
    },
    
    # Layer 3: 最近上下文（完整保留）
    {"role": "assistant", "content": "[Step N-5的回复]"},
    {"role": "user", "content": "[Step N-4的API结果]"},
    ...
    {"role": "user", "content": "[当前输入]"},
]
```

## 效果对比

### Before (v0.4.0)

```
压缩时机: 14条消息就压缩
压缩方式: [system, summary, recent_10]

丢失内容:
❌ Initial task（任务描述）
❌ 通信协议说明
❌ 工具使用指南

结果:
White agent困惑 → 编造错误格式 → 失败
```

### After (v0.4.1)

```
压缩时机: 20条消息才压缩
压缩方式: [system, initial_task, summary, recent_12]

保留内容:
✅ System prompt（规则和指导）
✅ Initial task（任务和协议）
✅ Progress summary（进度总结）
✅ Protocol reminder（协议提醒）
✅ Recent context（最近对话）

结果:
White agent清楚理解 → 使用正确格式 → 成功
```

## 关键改进点

### 1. 永远保留Initial Task

```python
initial_task_msg = messages[1]  # 永远不压缩这条！
```

这条消息包含：
- 完整的任务描述
- 通信协议格式
- 可用工具列表
- 使用示例

### 2. 增加MAX_MESSAGES阈值

```python
MAX_MESSAGES = 12  # 太小 → 过早压缩
MAX_MESSAGES = 20  # 更合理 → 适时压缩
```

### 3. 更智能的总结

```python
# Before: 简单关键词
"- Called APIs and received results"

# After: 具体进度
"Obtained user credentials"
"Successfully authenticated"
"Retrieved playlist information"
+ Protocol Reminder
```

### 4. 协议提醒

在summary中添加协议提醒，即使initial task被"遗忘"，agent也能从summary中回忆起正确格式：

```
=== Protocol Reminder ===
Use: {"action": "call_api", ...}
Or: {"action": "answer", "content": "..."}
```

## Token使用对比

### 场景：25条消息

**v0.4.0 (会过早触发压缩)**:
```
Messages: [system, summary, msg16-25]
Initial task: ❌ 被压缩掉
Token: ~10,000
问题: 丢失关键信息
```

**v0.4.1 (适时压缩)**:
```
Messages: [system, initial_task, summary, msg14-25]
Initial task: ✅ 永远保留
Token: ~13,000 (稍多，但保留了关键信息)
结果: 正确理解任务和协议
```

## 测试预期

```bash
cd /home/lyl610/green1112/appworld
export OPENAI_API_KEY="your-key"
python ../appworld_green_agent/main.py launch --task-id 82e2fac_1
```

### 预期输出

```
Step 1-19: 正常运行（无压缩）

Step 20: 触发压缩
Compressing message history: 22 -> 20 messages
Summary created: 8 messages compressed
Kept: system + initial_task + summary + 12 recent
Final message count: 16

Step 21: White agent正常运行
<json>{"action": "call_api", ...}</json>  ✅ 正确格式

Step N: 最终回答
<json>{"action": "answer", "content": "A Love That Never Was"}</json>  ✅

Result: Success! ✅
```

## 配置建议

可根据具体情况调整：

```python
# 保守配置（保留更多上下文）
MAX_MESSAGES = 24
num_recent = 14

# 标准配置（当前）
MAX_MESSAGES = 20
num_recent = 12

# 激进配置（更多压缩）
MAX_MESSAGES = 16
num_recent = 10
```

## 未来优化

### 1. 动态阈值

根据token实际使用量动态调整：

```python
if estimate_tokens(messages) > 25000:
    MAX_MESSAGES = 16  # 更激进
elif estimate_tokens(messages) > 20000:
    MAX_MESSAGES = 20  # 标准
```

### 2. 使用LLM总结

使用便宜的模型（GPT-3.5）来创建更好的总结：

```python
summary_response = completion(
    model="gpt-3.5-turbo",
    messages=[{
        "role": "user",
        "content": f"Summarize this conversation: {middle_messages}"
    }]
)
```

### 3. 选择性保留

识别并保留特别重要的中间消息（如获得凭据）：

```python
critical_messages = []
for msg in middle_messages:
    if is_critical(msg):  # credentials, important results
        critical_messages.append(msg)

compressed = [system, initial, *critical, summary, *recent]
```

## 相关文件

- `src/white_agent/agent.py` - 第112-195行

## 版本历史

- v0.4.0 - 基础压缩机制（有问题）
- v0.4.1 - 三层保留策略（改进）

## 经验教训

1. **不是所有消息都同等重要** - 需要区分关键信息和临时信息
2. **Initial task是核心** - 包含了任务理解和协议规范
3. **协议提醒很重要** - 即使在summary中也要重申
4. **压缩阈值要合理** - 不要过早压缩，给予足够buffer
5. **总结要有意义** - 不只是"调用了API"，要说清楚做了什么

🎯 现在的压缩策略既能避免token限制，又能保持white agent对任务的正确理解！


