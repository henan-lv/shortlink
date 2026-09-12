# =============================================================================
# ShortLink 前端 - 多阶段构建
# Stage 1: node 构建产物到 /app/dist
# Stage 2: nginx 镜像直接服务静态文件
# =============================================================================

FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json ./
RUN npm install --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
