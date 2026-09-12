#!/usr/bin/env bash
# ShortLink 停止脚本
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/.runtime"

stop_one() {
  local name="$1" pidfile="$2"
  if [ ! -f "$pidfile" ]; then
    echo "  $name 未运行"
    return 0
  fi
  local pid
  pid="$(cat "$pidfile")"
  if kill -0 "$pid" 2>/dev/null; then
    # 杀整个进程组(因为 start_new_session 创建了新会话)
    kill -- -"$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
    sleep 1
    kill -9 -- -"$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null || true
    echo "  已停止 $name (PID $pid)"
  else
    echo "  $name 进程已不存在"
  fi
  rm -f "$pidfile"
}

stop_one "frontend" "$LOG_DIR/frontend.pid"
stop_one "backend"  "$LOG_DIR/backend.pid"
