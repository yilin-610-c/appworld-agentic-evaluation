#!/bin/bash
# 启动 Green Agent 和 Quick Tunnel

echo "=================================="
echo "启动 Green Agent (Quick Tunnel)"
echo "=================================="

# 激活 conda 环境
source /home/lyl610/miniconda3/etc/profile.d/conda.sh
conda activate appworld_agent_py313

# 设置环境变量
export APPWORLD_ROOT=/home/lyl610/green1112/appworld
export PATH="$HOME/bin:$PATH"

# 检查 OPENAI_API_KEY
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  警告: OPENAI_API_KEY 未设置"
    echo "请运行: export OPENAI_API_KEY=your-key-here"
    exit 1
fi

# 进入项目目录
cd /home/lyl610/green1112/appworld_green_agent

echo ""
echo "=== 启动 Green Agent (端口 8010) ==="
python main.py green --host 0.0.0.0 --port 8010 --mcp &
GREEN_PID=$!
echo "Green Agent PID: $GREEN_PID"

# 等待 Agent 启动
echo "等待 Agent 启动..."
sleep 8

# 测试 Agent
echo "=== 测试 Agent ==="
curl -s http://localhost:8010/.well-known/agent-card.json | head -3
if [ $? -eq 0 ]; then
    echo "✓ Green Agent 启动成功"
else
    echo "✗ Green Agent 启动失败"
    kill $GREEN_PID 2>/dev/null
    exit 1
fi

echo ""
echo "=== 启动 Quick Tunnel ==="
echo "⚠️  请记下生成的 URL，稍后需要在 AgentBeats 平台注册"
echo ""

# 启动 Quick Tunnel 并捕获 URL
~/bin/cloudflared tunnel --url http://localhost:8010 2>&1 | tee /tmp/cloudflared_green.log &
TUNNEL_PID=$!

# 等待 Tunnel 生成 URL
echo "等待 Quick Tunnel 生成 URL..."
sleep 5

# 提取并显示 URL
TUNNEL_URL=$(grep -oP 'https://[a-z0-9\-]+\.trycloudflare\.com' /tmp/cloudflared_green.log | head -1)
if [ -n "$TUNNEL_URL" ]; then
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║              🎉 Green Agent Quick Tunnel 已就绪               ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "  Controller URL: $TUNNEL_URL"
    echo ""
    echo "  请在 AgentBeats 平台注册时使用此 URL"
    echo ""
    echo "  现在您需要："
    echo "  1. 设置环境变量: export CLOUDRUN_HOST=${TUNNEL_URL#https://}"
    echo "  2. 重启 Green Agent 以使用新的 URL"
    echo ""
    echo "  按 Ctrl+C 停止 Agent 和 Tunnel"
    echo ""
    echo "════════════════════════════════════════════════════════════════"
fi

# 等待 cloudflared 进程
wait $TUNNEL_PID

