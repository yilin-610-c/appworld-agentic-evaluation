# 轨迹分析评估系统 - 安装与故障排查指南

## ✅ 系统要求

在运行更新后的评估系统之前，请确保满足以下要求：

### 必需组件
- **Python 3.13+**
- **Conda** (推荐用于环境管理)
- **Git**
- **OpenAI API Key**
- **AppWorld 数据集** (需要独立下载)

---

## 📥 完整安装步骤

### 1. 克隆仓库

```bash
git clone git@github.com:yilin-610-c/appworld-agentic-evaluation.git
cd appworld-agentic-evaluation
```

### 2. 创建并激活 Conda 环境

```bash
conda create -n appworld_agent_py313 python=3.13
conda activate appworld_agent_py313
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

**验证关键包已安装：**

```bash
python -c "import mcp; print('✓ MCP installed')"
python -c "from src.evaluator.trajectory_analyzer import analyze_mcp_trajectory; print('✓ Trajectory analyzer available')"
```

### 4. 安装 AppWorld 基准数据集

**重要：** AppWorld 数据集需要单独安装，不包含在本仓库中。

```bash
# 回到父目录
cd ..

# 克隆 AppWorld 仓库
git clone https://github.com/stonybrooknlp/appworld.git
cd appworld

# 下载数据集 (约 200MB)
python -m appworld.cli download --dataset-version v1

# 验证安装
ls data/tasks/ | head -5  # 应该看到任务文件
```

### 5. 配置环境变量

```bash
# 方式 1: 临时设置 (仅当前会话)
export APPWORLD_ROOT=/path/to/appworld
export OPENAI_API_KEY=your-openai-api-key-here

# 方式 2: 永久设置 (推荐)
# 添加到 ~/.bashrc 或 ~/.zshrc
echo 'export APPWORLD_ROOT=/absolute/path/to/appworld' >> ~/.bashrc
echo 'export OPENAI_API_KEY=your-key-here' >> ~/.bashrc
source ~/.bashrc
```

**验证配置：**

```bash
echo $APPWORLD_ROOT
echo $OPENAI_API_KEY
ls $APPWORLD_ROOT/data  # 应该看到 tasks/ 目录
```

---

## 🧪 验证安装

运行测试任务以确保一切正常：

```bash
cd appworld-agentic-evaluation
conda activate appworld_agent_py313

# 测试轨迹分析器
python test_trajectory_analyzer.py

# 应该看到：
# ✓ ALL TESTS PASSED
# VERIFICATION SUMMARY: 11/11 checks passed
```

运行完整评估（包含轨迹分析）：

```bash
python main.py launch --task-id 82e2fac_1 --mcp
```

**预期输出应包含：**

1. 任务评估结果
2. **轨迹分析结果** (新增部分)：
   ```
   ================================================================================
   TRAJECTORY ANALYSIS RESULTS
   ================================================================================
   
   📊 BASIC EFFICIENCY METRICS
   ...
   ```

---

## 🚨 常见问题与解决方案

### 问题 1: `ModuleNotFoundError: No module named 'mcp'`

**症状：**
```
ModuleNotFoundError: No module named 'mcp'
```

**解决方案：**
```bash
conda activate appworld_agent_py313
pip install mcp
```

### 问题 2: `Warning: Log file not found`

**症状：**
```
Warning: Log file not found: /tmp/mcp_tool_calls_None.jsonl
Trajectory analysis skipped.
```

**原因：** 使用的是旧版本代码，task_id 没有正确传递。

**解决方案：**
```bash
# 确保使用最新代码
git pull origin main

# 验证文件是最新的
git log --oneline -1 src/green_agent/agent_mcp.py
# 应该看到包含 "Fix trajectory logging" 的提交
```

### 问题 3: `FileNotFoundError: APPWORLD_ROOT not set`

**症状：**
```
FileNotFoundError: [Errno 2] No such file or directory: '.../appworld/data'
```

**解决方案：**
```bash
# 检查环境变量
echo $APPWORLD_ROOT
# 如果为空，设置它：
export APPWORLD_ROOT=/absolute/path/to/appworld

# 验证路径存在
ls $APPWORLD_ROOT/data/tasks/
```

### 问题 4: `ImportError: cannot import name 'analyze_mcp_trajectory'`

**症状：**
```
ImportError: cannot import name 'analyze_mcp_trajectory' from 'src.evaluator.trajectory_analyzer'
```

**原因：** 文件未正确下载或损坏。

**解决方案：**
```bash
# 检查文件是否存在
ls -lh src/evaluator/trajectory_analyzer.py

# 如果文件不存在或大小为 0，重新拉取
git fetch origin
git checkout origin/main -- src/evaluator/trajectory_analyzer.py

# 验证文件内容
head -20 src/evaluator/trajectory_analyzer.py
# 应该看到函数定义
```

### 问题 5: `TypeError: AppWorldWhiteAgentMCPExecutor.__init__() missing self.log_file`

**症状：**
```
AttributeError: 'AppWorldWhiteAgentMCPExecutor' object has no attribute 'log_file'
```

**原因：** White Agent 代码未更新。

**解决方案：**
```bash
# 确保 White Agent 代码是最新的
git pull origin main
git checkout origin/main -- src/white_agent/agent_mcp.py

# 验证更新
grep "self.log_file" src/white_agent/agent_mcp.py
# 应该看到：self.log_file = None
```

### 问题 6: OpenAI API 错误

**症状：**
```
openai.AuthenticationError: Invalid API key
```

**解决方案：**
```bash
# 验证 API key
echo $OPENAI_API_KEY

# 测试 API 访问
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" | head -20

# 如果失败，重新设置正确的 key
export OPENAI_API_KEY=sk-proj-...
```

### 问题 7: 端口占用

**症状：**
```
ERROR: [Errno 98] error while attempting to bind on address ('0.0.0.0', 9000): address already in use
```

**解决方案：**
```bash
# 查找占用端口的进程
lsof -i :9000 -i :10000

# 终止进程
kill -9 <PID>

# 或者使用清理脚本
pkill -f "appworld"
```

---

## 📊 验证轨迹分析功能

运行评估后，检查输出是否包含所有指标：

### 必需的输出部分

1. **任务评估结果** (AppWorld 官方):
   ```json
   {
     "success": true/false,
     "difficulty": 1-3,
     "num_tests": N,
     "passes": [...],
     "failures": [...]
   }
   ```

2. **轨迹分析结果** (新增):
   ```json
   {
     "trajectory_analysis": {
       "total_api_calls": N,
       "total_duration_seconds": X.X,
       "calls_per_minute": X.X,
       "avg_duration_ms": X.X,
       "error_rate": 0.XXX,
       "failed_calls": N,
       "successful_calls": N,
       "retry_count": N,
       "pagination_sequences": N,
       "unique_tools": N,
       "unique_tool_list": [...]
     }
   }
   ```

### 检查日志文件

轨迹分析依赖于 JSONL 日志文件：

```bash
# 运行评估后，检查日志文件是否生成
ls -lh /tmp/mcp_tool_calls_*.jsonl

# 查看日志内容
cat /tmp/mcp_tool_calls_82e2fac_1.jsonl | head -3 | python -m json.tool

# 应该看到类似：
# {
#   "timestamp": "2024-01-15T10:00:00.000000",
#   "tool_name": "spotify__login",
#   "arguments": {...},
#   "success": true,
#   "duration_ms": 120.5,
#   "result": {...}
# }
```

---

## 🔍 独立测试轨迹分析器

如果您想单独测试轨迹分析功能：

```bash
# 运行单元测试
python test_trajectory_analyzer.py

# 分析已有的日志文件
python src/evaluator/trajectory_analyzer.py /tmp/mcp_tool_calls_82e2fac_1.jsonl

# 在 Python 中使用
python << EOF
from src.evaluator.trajectory_analyzer import analyze_mcp_trajectory

metrics = analyze_mcp_trajectory("/tmp/mcp_tool_calls_82e2fac_1.jsonl")
print(f"Total API calls: {metrics['total_api_calls']}")
print(f"Error rate: {metrics['error_rate']:.1%}")
print(f"Retry count: {metrics['retry_count']}")
EOF
```

---

## 📁 关键文件检查清单

确保以下文件存在且是最新版本：

```bash
# 检查所有关键文件
git ls-files | grep -E "trajectory_analyzer|agent_mcp.py" | while read file; do
  echo "✓ $file ($(git log -1 --format=%cd --date=short $file))"
done

# 应该看到：
# ✓ src/evaluator/trajectory_analyzer.py (最近日期)
# ✓ src/green_agent/agent_mcp.py (最近日期)
# ✓ src/white_agent/agent_mcp.py (最近日期)
# ✓ test_trajectory_analyzer.py (最近日期)
```

---

## 🆘 仍然无法工作？

如果按照上述步骤仍然无法运行，请：

1. **收集诊断信息：**

```bash
# 运行诊断脚本
python << EOF
import sys
import os

print("=== 环境诊断 ===")
print(f"Python version: {sys.version}")
print(f"Python path: {sys.executable}")
print(f"APPWORLD_ROOT: {os.environ.get('APPWORLD_ROOT', 'NOT SET')}")
print(f"OPENAI_API_KEY: {'SET' if os.environ.get('OPENAI_API_KEY') else 'NOT SET'}")

try:
    import mcp
    print("✓ mcp installed")
except ImportError as e:
    print(f"✗ mcp not installed: {e}")

try:
    from src.evaluator.trajectory_analyzer import analyze_mcp_trajectory
    print("✓ trajectory_analyzer available")
except ImportError as e:
    print(f"✗ trajectory_analyzer not available: {e}")

# 检查文件
import os.path
files = [
    "src/evaluator/trajectory_analyzer.py",
    "src/green_agent/agent_mcp.py",
    "src/white_agent/agent_mcp.py",
    "test_trajectory_analyzer.py"
]
for f in files:
    exists = os.path.exists(f)
    size = os.path.getsize(f) if exists else 0
    print(f"{'✓' if exists else '✗'} {f} ({size} bytes)")
EOF
```

2. **提供完整错误信息：**
   - 完整的错误堆栈
   - 运行的命令
   - Python 版本
   - 操作系统

3. **联系支持：**
   - 在 GitHub 仓库开 Issue
   - 提供上述诊断信息

---

## ✅ 成功标志

如果看到以下输出，说明系统运行正常：

```
================================================================================
TRAJECTORY ANALYSIS RESULTS
================================================================================

📊 BASIC EFFICIENCY METRICS
--------------------------------------------------------------------------------
  Total API Calls:        15
  Total Duration:         12.50 seconds
  Throughput:             72.00 calls/min
  Average Latency:        833.33 ms

⚠️  ERROR AND STABILITY METRICS
--------------------------------------------------------------------------------
  Successful Calls:       13
  Failed Calls:           2
  Error Rate:             13.3%
  Retry Count:            1 (self-correction)

🔍 BEHAVIORAL PATTERN METRICS
--------------------------------------------------------------------------------
  Pagination Sequences:   2
  Unique Tools Used:      8
```

**恭喜！您的轨迹分析评估系统已成功运行！** 🎉

---

## 📞 快速支持检查表

在寻求帮助之前，请确认：

- [ ] 使用最新代码：`git pull origin main`
- [ ] 环境变量已设置：`echo $APPWORLD_ROOT $OPENAI_API_KEY`
- [ ] AppWorld 数据已下载：`ls $APPWORLD_ROOT/data/tasks/`
- [ ] 依赖已安装：`pip install -r requirements.txt`
- [ ] 单元测试通过：`python test_trajectory_analyzer.py`
- [ ] 关键文件存在：`ls src/evaluator/trajectory_analyzer.py`

如果以上都确认无误但仍有问题，请在 GitHub Issue 中提供详细信息。


