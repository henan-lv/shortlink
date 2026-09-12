#!/usr/bin/env bash
# 停止整套服务
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> 停止所有服务"
docker compose -f docker-compose.yml -f docker-compose.dev.yml down

echo "==> 完成(数据卷保留)"
