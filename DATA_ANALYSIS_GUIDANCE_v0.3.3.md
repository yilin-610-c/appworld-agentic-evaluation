# Data Analysis Guidance Fix v0.3.3

## 修复时间
2024-11-13

## 问题描述

同一任务（"What is the title of the most-liked song in my Spotify playlists"）出现不一致的结果：

### 之前（成功，17步）
- 获取播放列表
- **逐个调用`show_song()`检查每首歌**
- 比较所有歌曲的`like_count`
- 正确返回："A Love That Never Was" (18 likes) ✅

### 现在（失败，10步）
- 获取播放列表
- 调用`show_liked_songs`
- **误以为liked songs = most-liked song**
- 错误返回："Mysteries of the Silent Sea" ❌

## 根本原因

### LLM的非确定性行为

即使是相同的prompt和`temperature=0.0`，LLM也可能选择不同的推理路径：

**路径A（正确）**：
```
看到playlist → "我需要检查每首歌的详细信息"
→ 逐个调用show_song()
→ 比较like_count字段
→ 找到最大值 ✅
```

**路径B（错误）**：
```
看到playlist → "哦，有个show_liked_songs API"
→ "liked songs"这个名字听起来就是"most-liked"
→ 直接返回第一首 ❌
```

### API名称的误导性

```python
show_liked_songs()  # 用户自己喜欢的歌曲列表
vs
"most-liked song"   # 被最多人点赞的歌曲（需要检查like_count字段）
```

White agent混淆了这两个概念。

## 解决方案：通用数据分析指导

### 修改内容

**文件**: `src/white_agent/agent.py`  
**位置**: 第77-83行

**新增内容**:

```python
**IMPORTANT - Data Analysis:**
When tasks require finding "most/highest/best":
1. Gather ALL relevant items first
2. Retrieve detailed information for EACH item
3. Compare the specific metric (count, rating, etc.)
4. Find the maximum/minimum based on data, not assumptions
5. Do NOT rely on API names or ordering - always check the actual data fields
```

### 设计考虑

1. **通用性** ✅
   - 不针对特定任务
   - 适用于所有"寻找最大/最小值"类型的任务
   - 不泄露答案或特定API名称

2. **明确的方法论** ✅
   - 5步清晰的流程
   - 强调"检查所有项目"
   - 强调"基于数据而非假设"

3. **关键警告** ✅
   - "不要依赖API名称" → 针对`show_liked_songs`误导问题
   - "不要依赖排序" → 避免假设数据已排序

## 预期改进

### 之前的错误行为

```
White Agent看到: show_liked_songs API
思考: "liked songs应该就是most-liked songs吧"
行动: 调用一次API，返回第一个结果
结果: 错误答案 ❌
```

### 现在的预期行为

```
White Agent看到: 任务要求"most-liked"
回忆System Prompt: "需要gathering ALL items并比较metric"
思考: "我需要检查每首歌的like_count字段"
行动: 
  1. 获取所有song_ids
  2. 逐个调用show_song()
  3. 比较like_count值
  4. 返回最大值
结果: 正确答案 ✅
```

## Pass@k 评估的必要性

### 为什么需要？

由于LLM的非确定性：
- **单次评估** = 可能运气好或运气坏
- **Pass@k评估** = 更可靠的性能指标

### 定义

```
pass@k = P(至少1次成功 | k次独立尝试)
```

### 示例

假设agent真实成功率是60%：
- pass@1 = 0.6 (60%)
- pass@3 = 1 - (0.4)³ = 0.936 (93.6%)
- pass@5 = 1 - (0.4)⁵ = 0.99 (99%)

### 实现建议（未来）

```python
async def launch_evaluation_with_passk(task_id: str, k: int = 3):
    results = []
    for attempt in range(k):
        result = await launch_single_evaluation(task_id)
        results.append(result)
    
    successes = sum(1 for r in results if r["success"])
    return {
        "pass@k": successes / k,
        "attempts": results
    }
```

## 其他可能的改进

### 1. 降低Temperature（如果有必要）

虽然已经设置为0.0，但某些LLM provider可能有最小值。可以尝试：
```python
temperature=0.0,
top_p=0.1,  # 额外约束
```

### 2. Self-Correction机制

在返回答案前self-check：
```
Before providing final answer, ask yourself:
- Did I check ALL items?
- Did I compare the actual metric values?
- Is my answer based on DATA, not API names?
```

### 3. Few-Shot Examples

在初始消息中包含类似任务的示例：
```
Example: Find the most expensive product
Wrong: Call show_featured_products() and return first
Right: Get all products, check each price, find maximum
```

但这可能会使初始消息过长。

## 测试验证

```bash
cd /home/lyl610/green1112/appworld
export OPENAI_API_KEY="your-key-here"
python ../appworld_green_agent/main.py launch --task-id 82e2fac_1
```

### 预期输出

```
Step 8: show_playlist_library → 获得song_ids
Step 9: show_song(song_id=70) → {"like_count": 15, ...}
Step 10: show_song(song_id=78) → {"like_count": 7, ...}
Step 11: show_song(song_id=124) → {"like_count": 18, ...}  ← 最高
...
Step N: 比较完所有歌曲
Final Answer: A Love That Never Was

Evaluation Results:
  Success: True ✅
  Score: 1.0
```

## 如果还是失败？

### 诊断步骤

1. **检查是否遵循了指导**
   - 看trace：agent是否逐个检查了每首歌？
   - 还是又走了捷径？

2. **增强指导**
   - 在初始消息中也提醒（除了system prompt）
   - 使用更强的语言："NEVER take shortcuts"

3. **考虑Pass@k**
   - 如果3次中有2次成功，说明agent有能力但不稳定
   - 可以通过多次采样提高可靠性

4. **检查Temperature**
   - 确认LiteLLM确实使用了temperature=0.0
   - 某些provider可能有默认值override

## 经验教训

1. **LLM是概率性的** - 即使temperature=0，行为也可能变化
2. **API名称很重要** - 误导性的名称会影响LLM推理
3. **通用指导优于特定指导** - 不会泄露任务细节
4. **需要多次评估** - Pass@k比单次评估更可靠
5. **System Prompt是强大的工具** - 但不能100%保证行为

## 版本历史

- v0.2.2 - 修复API结果传递
- v0.3.0 - Prompt engineering (supervisor)
- v0.3.1 - 答案提交修复
- v0.3.2 - 答案格式优化
- v0.3.3 - 数据分析通用指导

## 下一步

- **短期**：测试改进后的prompt，看成功率是否提高
- **中期**：实现Pass@k评估框架
- **长期**：收集更多失败案例，持续优化prompt和评估机制

🎯 现在agent应该更稳定地采用正确的推理路径！


