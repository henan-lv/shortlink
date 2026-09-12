#!/usr/bin/env bash
# 启动整套服务(开发模式)
set -euo pipefail

cd "$(dirname "$0")/.."

# 首次启动需要复制 .env
if [ ! -f ".env" ]; then
    echo "==> 复制 .env.example -> .env"
    cp .env.example .env
    echo "    请编辑 .env 填入密码等敏感字段"
fi

if [ ! -f "../backend/.env" ]; then
    echo "==> 复制 backend/.env.example -> backend/.env"
    cp ../backend/.env.example ../backend/.env
    echo "    请编辑 backend/.env 填入 DB / Redis 连接信息"
fi

echo "==> 启动开发模式"
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

echo ""
echo "==> 等待服务就绪..."
sleep 5

echo "==> 状态:"
docker compose -f docker-compose.yml -f docker-compose.dev.yml ps

echo ""
echo "==> 访问入口:"
echo "    Nginx: http://localhost:8080"
echo "    健康:  curl http://localhost:8080/health"
