# 更新说明 v0.2.1

## 修复时间
2024-11-13

## 问题描述

在v0.2.0版本中，meta-API的定义与AppWorld实际API返回格式不匹配，导致white agent无法正确理解如何调用API。

### 具体问题

1. **`show_api_doc` 缺少 `app_name` 参数**
   - 实际调用格式：`apis.api_docs.show_api_doc(app_name='spotify', api_name='login')`
   - 之前定义只有：`api_name` 参数

2. **返回值描述不准确**
   - 之前描述过于简单，没有说明实际返回的数据结构
   - 缺少example字段来指导white agent

3. **API名称格式混淆**
   - `show_api_descriptions` 返回的是不带app前缀的名称（如 `login`）
   - 但调用实际API时需要完整名称（如 `spotify.login`）
   - 之前的说明不够清晰

## 修复内容

### 1. 更新 `get_meta_api_specs()` 函数

**修改前**:
```python
{
    "name": "api_docs.show_api_doc",
    "description": "Get detailed documentation for a specific API",
    "parameters": {
        "api_name": {  # ❌ 只有一个参数
            "type": "string", 
            "required": True, 
            "description": "Full API name like 'spotify.login'"
        }
    },
    "returns": {"type": "dict", "description": "API documentation..."}  # ❌ 太简单
}
```

**修改后**:
```python
{
    "name": "api_docs.show_api_doc",
    "description": "Get detailed documentation for a specific API",
    "parameters": {
        "app_name": {  # ✅ 添加了app_name参数
            "type": "string",
            "required": True,
            "description": "The app name (e.g., 'spotify', 'gmail')"
        },
        "api_name": {  # ✅ 改为不带前缀的名称
            "type": "string", 
            "required": True, 
            "description": "The API name without app prefix (e.g., 'login', 'send_email')"
        }
    },
    "returns": {  # ✅ 添加详细的example
        "type": "dict", 
        "description": "Detailed API documentation including app_name, api_name, method, path, parameters, response_schemas",
        "example": {
            "app_name": "spotify",
            "api_name": "login",
            "method": "POST",
            "parameters": [...],
            "response_schemas": {...}
        }
    }
}
```

### 2. 更新所有meta-API的返回值说明

为所有3个meta-APIs添加了详细的`example`字段：

**api_docs.show_app_descriptions()**:
```json
{
  "example": [
    {"name": "spotify", "description": "A music streaming app..."},
    {"name": "gmail", "description": "An email app..."}
  ]
}
```

**api_docs.show_api_descriptions(app_name='spotify')**:
```json
{
  "example": [
    {"name": "login", "description": "Login to your account."},
    {"name": "show_account", "description": "Show your account information."}
  ]
}
```

### 3. 改进初始消息说明

**修改前**:
```
You have access to AppWorld APIs. To discover:
   - Call api_docs.show_app_descriptions() to see all available apps
   - Call api_docs.show_api_descriptions(app_name='spotify') to see app-specific APIs
   - Call apis.api_docs.show_api_doc(app_name='spotify', api_name='login') to see how to use a specific API
```

**修改后**:
```
You have access to AppWorld APIs. Follow these steps to discover and use them:

**Step 1: Discover available apps**
   Call: api_docs.show_app_descriptions()
   Returns: [{"name": "spotify", "description": "..."}, {"name": "gmail", "description": "..."}, ...]

**Step 2: Get APIs for the relevant app**
   Call: api_docs.show_api_descriptions(app_name='spotify')
   Returns: [{"name": "login", "description": "..."}, {"name": "show_playlist_library", "description": "..."}, ...]
   Note: API names returned here do NOT include the app prefix

**Step 3: Get detailed API documentation**
   Call: api_docs.show_api_doc(app_name='spotify', api_name='login')
   Returns: Full API details including parameters, types, response schemas, etc.

**Step 4: Call the actual APIs**
   Call: spotify.login(username='...', password='...')
   Important: Use the FULL API name (app_name.api_name) when calling actual APIs
```

### 4. 添加具体的调用示例

```
**Communication Protocol:**
- To call an API, respond with JSON:
  {"action": "call_api", "api_name": "app.function", "parameters": {"param1": "value1"}}
  Example: {"action": "call_api", "api_name": "api_docs.show_app_descriptions", "parameters": {}}
  Example: {"action": "call_api", "api_name": "spotify.login", "parameters": {"username": "user@example.com", "password": "pass123"}}
```

## 测试结果

```bash
$ python -c "from src.green_agent.agent import get_meta_api_specs; import json; print(json.dumps(get_meta_api_specs(), indent=2))"
```

输出正确显示3个meta-APIs，每个都有：
- ✅ 正确的参数定义
- ✅ 详细的返回值描述
- ✅ 清晰的example示例

## 预期改进

有了这些修复，white agent现在应该能够：

1. ✅ 正确理解如何调用 `api_docs.show_api_doc(app_name='...', api_name='...')`
2. ✅ 从返回的example中学习数据结构
3. ✅ 区分discovery API（返回不带前缀的名称）和实际API调用（需要完整名称）
4. ✅ 按照明确的4步流程完成任务

## 相关文件

- `src/green_agent/agent.py` - 主要修改文件
  - 第28-93行：`get_meta_api_specs()` 函数
  - 第125-170行：初始消息（initial_message）

## 下一步

测试修改后的代码：

```bash
cd /home/lyl610/green1112/appworld
export OPENAI_API_KEY="your-key"
python ../appworld_green_agent/main.py launch --task-id 82e2fac_1
```

预期white agent的行为：
1. 调用 `api_docs.show_app_descriptions()` 
2. 调用 `api_docs.show_api_descriptions(app_name='spotify')`  # ✅ 有app_name参数
3. 调用 `api_docs.show_api_doc(app_name='spotify', api_name='login')`  # ✅ 两个参数都有
4. 调用 `spotify.login(username=..., password=...)`  # ✅ 使用完整名称

## 致谢

感谢用户提供的实际API返回值示例，这些示例帮助准确定义了meta-API的规范。


