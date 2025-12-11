#!/bin/bash
# 一键启动 Green Agent 并自动配置 CLOUDRUN_HOST

echo "=================================="
echo "Green Agent 智能启动脚本"
echo "=================================="

# 激活 conda 环境
source /home/lyl610/miniconda3/etc/profile.d/conda.sh
conda activate appworld_agent_py313

# 设置必要的环境变量
export APPWORLD_ROOT=/home/lyl610/green1112/appworld
export PATH="$HOME/bin:$PATH"

# 检查 OPENAI_API_KEY
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  错误: OPENAI_API_KEY 未设置"
    echo "请运行: export OPENAI_API_KEY=your-key-here"
    exit 1
fi

cd /home/lyl610/green1112/appworld_green_agent

# 步骤 1: 启动 Quick Tunnel 获取 URL
echo ""
echo "=== 步骤 1: 启动 Quick Tunnel 获取公网 URL ==="
~/bin/cloudflared tunnel --url http://localhost:8010 > /tmp/cloudflared_green.log 2>&1 &
TUNNEL_PID=$!
echo "Tunnel PID: $TUNNEL_PID"

# 等待 URL 生成
echo "等待 URL 生成..."
for i in {1..15}; do
    TUNNEL_URL=$(grep -oP 'https://[a-z0-9\-]+\.trycloudflare\.com' /tmp/cloudflared_green.log | head -1)
    if [ -n "$TUNNEL_URL" ]; then
        break
    fi
    sleep 1
done

if [ -z "$TUNNEL_URL" ]; then
    echo "✗ 无法获取 Tunnel URL"
    kill $TUNNEL_PID 2>/dev/null
    exit 1
fi

echo "✓ Quick Tunnel URL: $TUNNEL_URL"

# 步骤 2: 提取域名并设置 CLOUDRUN_HOST
CLOUDRUN_HOST=${TUNNEL_URL#https://}
export CLOUDRUN_HOST
echo "✓ CLOUDRUN_HOST 已设置: $CLOUDRUN_HOST"

# 步骤 3: 启动 Green Agent（现在会使用正确的 URL）
echo ""
echo "=== 步骤 2: 启动 Green Agent ==="
python main.py green --host 0.0.0.0 --port 8010 --mcp &
GREEN_PID=$!
echo "Green Agent PID: $GREEN_PID"

# 等待 Agent 启动
sleep 8

# 验证 Agent
echo ""
echo "=== 步骤 3: 验证 Agent ==="
AGENT_CARD=$(curl -s http://localhost:8010/.well-known/agent-card.json)
CARD_URL=$(echo "$AGENT_CARD" | grep -oP '"url":"[^"]+' | cut -d'"' -f4)

echo "Agent Card URL 字段: $CARD_URL"

if [[ "$CARD_URL" == "https://"* ]]; then
    echo "✓ Agent Card 使用公网 URL (正确)"
else
    echo "⚠️  Agent Card 仍使用本地 URL (可能需要重启)"
fi

# 公网验证
echo ""
echo "=== 步骤 4: 公网验证 ==="
sleep 5
echo "测试公网访问..."
PUBLIC_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$TUNNEL_URL/.well-known/agent-card.json")
HTTP_CODE=$(echo "$PUBLIC_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ 公网访问成功 (HTTP 200)"
else
    echo "⚠️  公网访问异常 (HTTP $HTTP_CODE)"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║              🎉 Green Agent 已成功启动！                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "  Controller URL: $TUNNEL_URL"
echo ""
echo "  请在 AgentBeats 平台注册时使用此 URL"
echo ""
echo "  Agent 状态:"
echo "    • Agent PID: $GREEN_PID"
echo "    • Tunnel PID: $TUNNEL_PID"
echo "    • Agent Card URL: $CARD_URL"
echo ""
echo "  按 Ctrl+C 停止（会自动清理所有进程）"
echo ""
echo "════════════════════════════════════════════════════════════════"

# 设置清理函数
cleanup() {
    echo ""
    echo "=== 清理进程 ==="
    kill $GREEN_PID 2>/dev/null
    kill $TUNNEL_PID 2>/dev/null
    echo "✓ 已停止所有进程"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 保持脚本运行
echo ""
echo "监控日志中... (按 Ctrl+C 停止)"
tail -f /tmp/cloudflared_green.log

