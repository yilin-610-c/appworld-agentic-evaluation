# Concise Answer Format Fix v0.3.2

## 修复时间
2024-11-13

## 问题描述

答案成功提交到supervisor，但格式太啰嗦：

```
Final Answer: The title of the most-liked song in your Spotify playlists is 'A Love That Never Was' with 18 likes.
Task completion result: {"message": "Marked the active task complete."}

Evaluation Results:
  Success: False  ← 仍然失败
```

## 根本原因

AppWorld的评估器可能期望**简洁的答案**，而不是完整的句子。

White agent返回了：
```
"The title of the most-liked song in your Spotify playlists is 'A Love That Never Was' with 18 likes."
```

但Ground Truth可能只是：
```
"A Love That Never Was"
```

评估器可能使用精确匹配或相似度匹配，啰嗦的答案会导致匹配失败。

## 解决方案选择

### 方案A: 训练White Agent提供简洁答案 ✅ (采用)

**优点**:
- 符合评估理念 - 测试agent的答题能力
- 通用性好 - 适用于所有Question-style任务
- 让agent学会正确的答题格式

**缺点**:
- 依赖LLM理解和遵守指令

### 方案B: Green Agent提取答案 ❌ (不采用)

**优点**:
- 更可靠 - 不依赖LLM

**缺点**:
- 违反评估原则 - Green agent不应该"帮助"white agent
- 需要复杂的答案提取逻辑
- 可能误判某些答案

## 实现：方案A

### 修改内容

**文件**: `src/white_agent/agent.py`  
**位置**: 第53-97行 (system prompt)

**新增内容**:

```python
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
```

### 设计考虑

1. **不泄露答案** ✅
   - 使用通用例子 ("Midnight Dreams", "john.doe@email.com")
   - 避免使用实际任务中的答案 ("A Love That Never Was")

2. **多样化例子** ✅
   - 歌曲标题 (字符串)
   - 邮箱地址 (特定格式)
   - 数量 (数字)
   
3. **清晰的对比** ✅
   - 使用 ✅ 和 ❌ 标记好坏例子
   - 展示常见的错误模式

## 预期改进

### 之前的行为

```
White Agent思考: "我找到了答案，让我详细说明..."
返回: "The title of the most-liked song in your Spotify playlists is 'A Love That Never Was' with 18 likes."

AppWorld评估器: 
  期望: "A Love That Never Was"
  收到: "The title of the most-liked song in your Spotify playlists is 'A Love That Never Was' with 18 likes."
  匹配: ❌ 失败 (字符串不匹配)
```

### 现在的行为

```
White Agent思考: "我找到了答案，根据指令，我应该只返回歌曲名称..."
返回: "A Love That Never Was"

AppWorld评估器:
  期望: "A Love That Never Was"
  收到: "A Love That Never Was"
  匹配: ✅ 成功！
```

## GPT-4的行为模式

### 为什么之前会啰嗦？

GPT-4默认倾向于：
- 提供完整、礼貌的回答
- 添加上下文和解释
- 使用完整的句子

这在正常对话中很好，但在评估环境中会导致问题。

### System Prompt的作用

通过明确的指令和对比例子：
- ✅ 覆盖默认行为
- ✅ 建立新的响应模式
- ✅ 提供具体的"好"和"坏"例子

## 测试验证

```bash
cd /home/lyl610/green1112/appworld
export OPENAI_API_KEY="your-key-here"
python ../appworld_green_agent/main.py launch --task-id 82e2fac_1
```

### 预期输出

```
--- Step 22 ---
White agent: "After checking all songs, 'A Love That Never Was' has the highest like count."
<json>{"action": "answer", "content": "A Love That Never Was"}</json>

Final Answer: A Love That Never Was
Submitting answer to supervisor...
Task completion result: {"message": "Marked the active task complete."}

================================================================================
Evaluating task...
================================================================================

Evaluation Results:
  Success: True   ← ✅ 成功！
  Passed: 2/2     ← ✅ 全部通过！
  Failed: 0/2
  Score: 1.0      ← ✅ 满分！
```

## 备选方案：如果还是失败

如果修改后仍然失败，可能需要进一步调试：

### 1. 检查Ground Truth格式

```python
# 在green agent的代码中添加调试输出
print(f"Ground Truth: {world.task.ground_truth.answer}")
print(f"White Agent Answer: {final_answer}")
```

### 2. 使用更激进的指令

在system prompt中添加：
```
CRITICAL: For question-style tasks, your answer must be EXACTLY what is asked for.
- If asked for a title, return ONLY the title
- If asked for a name, return ONLY the name
- NO additional words, NO punctuation at the end, NO explanations
```

### 3. 方案B作为后备

如果方案A完全不work，可以考虑在green agent端做简单的答案清理：

```python
# 简单的答案清理（不是完整的提取）
final_answer = action.get("content", "")
# 移除常见的前缀
final_answer = final_answer.replace("The title is ", "")
final_answer = final_answer.replace("The answer is ", "")
# 移除引号
final_answer = final_answer.strip("'\"")
# 移除尾部的额外信息
if " with " in final_answer:
    final_answer = final_answer.split(" with ")[0]
```

但这应该作为最后的手段，因为它模糊了white agent的真实能力。

## 经验教训

1. **评估格式很重要** - 不只是找到答案，还要正确格式化
2. **System prompt是强大的工具** - 可以塑造LLM的输出风格
3. **具体例子胜过抽象规则** - ✅/❌ 对比很有效
4. **保持评估纯粹性** - 尽量不让green agent"修正"white agent

## 相关文件

- `src/white_agent/agent.py` - 第77-94行：新增答案格式指导

## 版本历史

- v0.2.2 - 修复API结果传递
- v0.3.0 - Prompt engineering (supervisor使用)
- v0.3.1 - 修复答案提交 + timeout
- v0.3.2 - 答案格式优化（简洁化）

## 下一步

如果这次测试成功：
- 🎉 恭喜！系统已经完整work了
- 可以尝试更多AppWorld任务
- 可以开始优化性能和成功率

如果还是失败：
- 检查ground truth的实际格式
- 考虑更激进的prompt修改
- 作为最后手段，考虑方案B

🚀 期待测试结果！


