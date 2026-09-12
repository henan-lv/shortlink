#!/usr/bin/env bash
# ShortLink 状态检查
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/.runtime"
BACKEND_PORT=8765
FRONTEND_PORT=5174

check() {
  local name="$1" port="$2" pidfile="$3" path="${4:-/}"
  local pid=""
  [ -f "$pidfile" ] && pid="$(cat "$pidfile" 2>/dev/null)"
  local alive="✗"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    alive="✓ PID=$pid"
  fi
  local code
  code="$(curl -s -o /dev/null -m 3 -w "%{http_code}" "http://127.0.0.1:${port}${path}" 2>/dev/null || echo "000")"
  printf "  %-10s port=%-6s %-15s http=%s\n" "$name" "$port" "$alive" "$code"
}

echo "服务状态:"
check "backend"  "$BACKEND_PORT"  "$LOG_DIR/backend.pid"  "/health"
check "frontend" "$FRONTEND_PORT" "$LOG_DIR/frontend.pid" "/"

echo ""
echo "健康检查 (JSON):"
curl -s -m 3 "http://127.0.0.1:${BACKEND_PORT}/health" || echo "  (无响应)"
