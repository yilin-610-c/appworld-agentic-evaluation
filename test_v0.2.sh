#!/bin/bash
# 测试修改后的Green Agent

echo "================================"
echo "测试 AppWorld Green Agent v0.2.0"
echo "================================"
echo ""

# 检查环境
echo "1. 检查Conda环境..."
if conda env list | grep -q "appworld_agent_py313"; then
    echo "   ✓ Conda环境存在"
else
    echo "   ✗ Conda环境不存在"
    exit 1
fi

# 检查API Key
echo ""
echo "2. 检查OpenAI API Key..."
if [ -z "$OPENAI_API_KEY" ]; then
    echo "   ⚠ OPENAI_API_KEY未设置"
    echo "   请运行: export OPENAI_API_KEY='your-key-here'"
    exit 1
else
    echo "   ✓ API Key已设置"
fi

# 激活环境
echo ""
echo "3. 激活Conda环境..."
source ~/miniconda3/etc/profile.d/conda.sh
conda activate appworld_agent_py313
echo "   ✓ 环境已激活"

# 测试导入
echo ""
echo "4. 测试模块导入..."
cd /home/lyl610/green1112/appworld_green_agent
python -c "from src.green_agent import start_green_agent; print('   ✓ Green agent导入成功')" || exit 1
python -c "from src.white_agent import start_white_agent; print('   ✓ White agent导入成功')" || exit 1

# 列出任务
echo ""
echo "5. 列出可用任务..."
cd /home/lyl610/green1112/appworld
python ../appworld_green_agent/main.py list-tasks | head -15

# 运行评估
echo ""
echo "================================"
echo "开始运行评估 (任务: 82e2fac_1)"
echo "================================"
echo ""
echo "这将启动Green和White agents并运行一个完整的评估周期。"
echo "预期行为:"
echo "  1. White agent首先调用api_docs APIs来发现可用APIs"
echo "  2. 查询Spotify相关APIs的文档"
echo "  3. 调用实际的Spotify APIs完成任务"
echo "  4. 返回最终答案"
echo "  5. Evaluation结果正确显示"
echo ""
read -p "按Enter键继续，或Ctrl+C取消..."
echo ""

python ../appworld_green_agent/main.py launch --task-id 82e2fac_1

echo ""
echo "================================"
echo "测试完成！"
echo "================================"


