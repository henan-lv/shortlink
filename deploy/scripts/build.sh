#!/usr/bin/env bash
# 构建后端镜像(以及按需构建前端)
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

echo "==> 构建后端镜像"
docker build -t shortlink-backend:latest "$ROOT/../backend"

if [ -d "$ROOT/../frontend" ]; then
    echo "==> 构建前端产物"
    (cd "$ROOT/../frontend" && npm install && npm run build)
fi

echo "==> 构建完成"
docker images | grep shortlink || true
