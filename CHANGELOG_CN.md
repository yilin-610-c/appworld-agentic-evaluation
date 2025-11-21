# 更新日志 (CHANGELOG)

## 版本 0.2.0 - 2024-11-13

### 重大改进

#### 1. API发现机制优化 (Tool Delivery优化)

**问题**: 之前的实现尝试获取所有457个API的文档，导致：
- 效率低下
- White agent收到的信息过载
- 与AppWorld设计理念不符

**解决方案**: 实现了**渐进式API发现机制**

现在Green Agent只提供3个meta-APIs：
- `api_docs.show_app_descriptions()` - 查看所有可用的应用
- `api_docs.show_api_descriptions(app_name='...')` - 查看特定应用的API列表
- `api_docs.show_api_doc(api_name='...')` - 查看具体API的详细文档

**优势**:
- ✅ 符合AppWorld设计理念 - agent需要自己探索
- ✅ 更真实的评估场景 - 测试agent的探索和推理能力
- ✅ 灵活性更高 - agent可以根据任务需要查询相关APIs
- ✅ 初始消息更简洁清晰

#### 2. 修复Evaluation结果处理

**问题**: 原代码假设`eval_result`有`.correct`属性，但AppWorld返回的是`TestTracker`对象。

**解决方案**: 实现了健壮的evaluation结果提取逻辑

基于用户提供的`summarize_eval`函数，现在支持：
- ✅ 使用`.to_dict()`方法获取评估结果
- ✅ 多种字段名称的fallback (passes/passed/successes等)
- ✅ 从tests列表中推断通过/失败数量
- ✅ 解析report文本作为最终fallback
- ✅ 详细的评估结果输出

**新增指标**:
```python
metrics = {
    "task_id": "...",
    "steps": 5,
    "success": True,
    "passes": 3,
    "fails": 0,
    "total": 3,
    "score": 1.0
}
```

### 技术细节

#### 修改的文件
- `src/green_agent/agent.py`

#### 新增函数
```python
def get_meta_api_specs() -> list:
    """返回用于API发现的meta-API规范"""
```

#### 修改的函数
- `run_appworld_task()` - 完全重写了API文档获取和初始消息生成逻辑
- Evaluation处理部分 - 使用`.to_dict()`和多级fallback机制

### 使用示例

现在White Agent会看到这样的初始消息：

```
Your task is to help answer the following question:

<task>
What is the title of the most-liked song in my Spotify playlists.
</task>

You have access to AppWorld APIs. To discover and use them, follow this process:

**Step 1: Discover available apps and APIs**
   - Call api_docs.show_app_descriptions() to see all available apps
   - Call api_docs.show_api_descriptions() to see all API names
   - Or call api_docs.show_api_descriptions(app_name='spotify') to see app-specific APIs

**Step 2: Get detailed API documentation**
   - Call api_docs.show_api_doc(api_name='spotify.login') to see how to use a specific API

**Step 3: Use the APIs to complete the task**
   - Call the actual APIs like spotify.login(username='...', password='...')

Here are the discovery/documentation APIs you can use:
[3 meta-APIs listed]
```

### 预期行为

White Agent应该：
1. 先调用`api_docs.show_api_descriptions(app_name='spotify')`发现Spotify APIs
2. 然后调用`api_docs.show_api_doc(api_name='spotify.login')`获取登录API文档
3. 依次调用相关APIs完成任务
4. 最终返回答案

### 向后兼容性

⚠️ **Breaking Changes**:
- 初始消息格式完全改变
- 不再预先提供所有API文档
- White Agent需要有能力进行API探索

### 测试建议

```bash
# 重新运行评估
cd /home/lyl610/green1112/appworld
export OPENAI_API_KEY="your-key"
python ../appworld_green_agent/main.py launch --task-id 82e2fac_1
```

预期会看到：
1. White Agent首先调用discovery APIs
2. 然后查询具体API文档
3. 最后调用实际APIs完成任务
4. Evaluation结果正确显示（无AttributeError）

### 已知问题

- 无

### 下一步计划

- [ ] 添加更多样化的任务测试
- [ ] 优化White Agent的prompt让它更好地理解discovery流程
- [ ] 添加缓存机制避免重复查询相同的API文档
- [ ] 支持批量任务评估

### 致谢

感谢用户提供的`summarize_eval`函数参考和对API发现机制的深入讨论。


