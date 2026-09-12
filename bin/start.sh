#!/usr/bin/env bash
# ShortLink 宿主机启动脚本
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/.runtime"
mkdir -p "$LOG_DIR"

BACKEND_PORT=8765
FRONTEND_PORT=5174
API_BASE="http://127.0.0.1:${BACKEND_PORT}"

start_one() {
  local name="$1"; shift
  local cwd="$1"; shift
  local logfile="$1"; shift
  local pidfile="$1"; shift

  if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo "  $name 已在运行 (PID $(cat "$pidfile"))"
    return 0
  fi
  rm -f "$pidfile"

  echo "  启动 $name ..."
  (
    cd "$cwd"
    # 用 _daemonize.py:真正脱离父会话(start_new_session=True)
    python3 "$ROOT/bin/_daemonize.py" "$logfile" "$pidfile" "$@"
  )
}

echo "==> 启动后端 (Flask + gunicorn, 端口 $BACKEND_PORT)"
start_one "backend" \
  "$ROOT/backend" \
  "$LOG_DIR/backend.log" \
  "$LOG_DIR/backend.pid" \
  gunicorn --daemon --bind "127.0.0.1:${BACKEND_PORT}" --workers 1 --threads 4 --timeout 60 \
    --pid "$LOG_DIR/backend.pid" --capture-output \
    --error-logfile "$LOG_DIR/backend-error.log" \
    --access-logfile "$LOG_DIR/backend-access.log" \
    wsgi:app

echo ""
echo "==> 启动前端 (Vite dev, 端口 $FRONTEND_PORT, 代理 -> $API_BASE)"
start_one "frontend" \
  "$ROOT/frontend" \
  "$LOG_DIR/frontend.log" \
  "$LOG_DIR/frontend.pid" \
  env VITE_API_BASE="$API_BASE" npm run dev -- --host 0.0.0.0 --port "$FRONTEND_PORT"

echo ""
echo "==> 等待服务就绪 ..."
sleep 5
bash "$ROOT/bin/status.sh"
