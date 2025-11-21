# Critical Fix v0.2.2 - API结果传递问题

## 问题时间
2024-11-13

## 问题描述

White agent反复调用 `api_docs.show_app_descriptions()` 但始终抱怨"没有收到预期的数据"：

```
White agent response:
It seems there was an issue with retrieving the app descriptions. 
Let's try calling the API again...

Executing: api_docs.show_app_descriptions with {}
API Result: Execution successful.
```

## 根本原因

### AppWorld的执行机制

AppWorld的 `world.execute(code)` 通过**捕获stdout**来返回结果：

```python
# appworld/src/appworld/environment.py 第1035-1047行
cell_capture = capture_output(stdout=True, stderr=True, display=True)
with cell_capture as cap:
    result = self._shell_run_cell(code)

if result.success:
    message = cap.stdout  # ← 返回stdout的内容
    if not message.strip():
        message = "Execution successful."  # stdout为空的fallback
```

### 之前的错误代码

```python
# ❌ 错误：API返回值没有打印到stdout
code = f"apis.{api_name}({params_str})"
# 例如: "apis.api_docs.show_app_descriptions()"

api_result = world.execute(code)
# 返回: "Execution successful." （因为stdout是空的）
```

执行流程：
1. ✅ API被调用
2. ✅ API返回数据（如app列表）
3. ❌ **返回值消失了**（没有赋值给变量，也没有打印）
4. ❌ stdout为空
5. ❌ `world.execute()` 返回 `"Execution successful."`
6. ❌ White agent收到无用的字符串

## 解决方案

```python
# ✅ 正确：先赋值给变量，然后print到stdout
code = f"result = apis.{api_name}({params_str})\nprint(result)"
# 例如: "result = apis.api_docs.show_app_descriptions()\nprint(result)"

api_result = world.execute(code)
# 返回: "[{'name': 'spotify', 'description': '...'}, ...]"
```

执行流程：
1. ✅ API被调用，返回值赋给 `result`
2. ✅ `print(result)` 输出到stdout
3. ✅ AppWorld捕获stdout内容
4. ✅ `world.execute()` 返回实际数据
5. ✅ White agent收到可用的数据

## 代码修改

**文件**: `src/green_agent/agent.py`

**修改位置**: 第247-251行

**修改前**:
```python
# Build the API call
params_str = ", ".join([f"{k}={repr(v)}" for k, v in parameters.items()])
code = f"apis.{api_name}({params_str})"
```

**修改后**:
```python
# Build the API call
# IMPORTANT: Must print the result so it's captured in stdout
# Otherwise world.execute() only returns "Execution successful."
params_str = ", ".join([f"{k}={repr(v)}" for k, v in parameters.items()])
code = f"result = apis.{api_name}({params_str})\nprint(result)"
```

## 完整数据流

```
┌─────────────────────────────────────────────────────────────┐
│ White Agent: 请求调用API                                     │
│ {"action": "call_api", "api_name": "api_docs.show_app_...", │
│  "parameters": {}}                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Green Agent: 构造执行代码                                    │
│ code = "result = apis.api_docs.show_app_descriptions()      │
│         print(result)"                                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ AppWorld执行: world.execute(code)                           │
│ 1. 执行: result = apis.api_docs.show_app_descriptions()    │
│    返回: [{"name": "spotify", ...}, {"name": "gmail", ...}] │
│ 2. 执行: print(result)                                      │
│    stdout: "[{'name': 'spotify', ...}, ...]"                │
│ 3. 捕获stdout并返回                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Green Agent: 收到实际数据                                    │
│ api_result = "[{'name': 'spotify', ...}, ...]"              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Green Agent → White Agent: 发送结果                         │
│ "API call result:                                           │
│  <api_result>[{'name': 'spotify', ...}, ...]</api_result>"  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ White Agent: 处理实际数据                                    │
│ "好的，我看到有spotify app，现在查询它的APIs..."             │
└─────────────────────────────────────────────────────────────┘
```

## 预期改进

修复后，当运行evaluation时，应该看到：

```
--- Step 1 ---
Executing: api_docs.show_app_descriptions with {}
API Result: [{'name': 'api_docs', 'description': '...'}, 
            {'name': 'supervisor', 'description': '...'}, 
            {'name': 'spotify', 'description': '...'},
            ...]

--- Step 2 ---
White agent: "太好了！我看到有spotify，让我查询它的APIs..."
Executing: api_docs.show_api_descriptions with {'app_name': 'spotify'}
API Result: [{'name': 'login', 'description': '...'},
            {'name': 'show_playlist_library', 'description': '...'},
            ...]

--- Step 3 ---
White agent: "好的，让我获取login的详细文档..."
Executing: api_docs.show_api_doc with {'app_name': 'spotify', 'api_name': 'login'}
API Result: {'app_name': 'spotify', 'api_name': 'login', 
            'parameters': [...], 'response_schemas': {...}}
```

## 验证

```bash
cd /home/lyl610/green1112/appworld
export OPENAI_API_KEY="your-key-here"
python ../appworld_green_agent/main.py launch --task-id 82e2fac_1
```

## 经验教训

1. **AppWorld使用stdout作为返回值传递机制** - 必须显式print
2. **Python的return值不会自动打印** - 需要手动print
3. **"Execution successful."是stdout为空的标志** - 提示没有捕获到任何输出
4. **在交互式评估中，数据流向很重要** - 每一环节都要确保数据正确传递

## 相关文件

- `src/green_agent/agent.py` - 第247-251行修改
- `appworld/src/appworld/environment.py` - 第1035-1047行（AppWorld的stdout捕获机制）

## 测试状态

- ✅ 代码语法检查通过
- ⏳ 等待完整evaluation测试

## 版本

v0.2.2 - Critical fix for API result passing


