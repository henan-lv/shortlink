# ShortLink 云服务部署

只打包前后端两个服务,数据库 / Redis 都走云服务,通过环境变量注入。

## 目录结构

```
docker/
├── docker-compose.yaml   # 编排:backend + frontend
├── Dockerfile.backend    # 后端 Python 镜像(gunicorn)
├── Dockerfile.frontend   # 前端 nginx 镜像(多阶段:node 构建 → nginx 托管)
├── nginx.conf            # 反向代理 + SPA 静态托管
└── .env.example          # 环境变量模板
```

## 部署步骤

### 1. 准备云服务

- **云 MySQL**:创建实例,创建库 `shortlink` 和账号
  ```bash
  # 在容器外跑迁移
  cd backend && FLASK_APP=wsgi.py flask db upgrade
  ```
- **云 Redis**:开通实例,拿到 host/port/password

### 2. 配置环境变量

```bash
cd docker
cp .env.example .env
vim .env  # 填入 DB_HOST / REDIS_HOST / SECRET_KEY / CORS_ORIGINS
```

必填:

| 项 | 说明 |
| --- | --- |
| `SECRET_KEY` | `openssl rand -hex 32` 生成 |
| `DB_HOST` `DB_USER` `DB_PASSWORD` `DB_NAME` | 云 MySQL 连接信息 |
| `REDIS_HOST` `REDIS_PASSWORD` | 云 Redis 连接信息 |
| `CORS_ORIGINS` | 前端域名,多域名用英文逗号 |

### 3. 构建并启动

```bash
docker compose -p shortlink up -d --build
```

### 4. 验证

```bash
docker compose -p shortlink ps

docker compose -p shortlink exec backend curl -fsS http://127.0.0.1:5000/health
curl http://your-server/healthz
```

### 5. 创建首个管理员

```bash
docker compose -p shortlink exec backend python -c "
from app import create_app
from app.extensions import db
from app.models import User
from app.services import password
app = create_app()
with app.app_context():
    u = User(username='admin', password_hash=password.hash_password('your-password'), is_admin=True, is_active=True)
    db.session.add(u); db.session.commit()
    print('admin created:', u.id)
"
```

### 6. 接入域名 / HTTPS

compose 只暴露 `FRONTEND_PORT:80`,建议云服务前面再挂一层:

- **云负载均衡 / API 网关**:监听 443,终止 SSL,转发到 `FRONTEND_PORT`(80)
- 或在前端容器前再加一个 caddy / nginx-proxy:自动签发证书

云服务器安全组需开放 `FRONTEND_PORT`(默认 80)。

## 常用运维命令

```bash
# 查看日志
docker compose -p shortlink logs -f --tail=200 backend
docker compose -p shortlink logs -f --tail=200 frontend

# 重启某个服务
docker compose -p shortlink restart backend

# 回滚
docker compose -p shortlink down
git pull && docker compose -p shortlink up -d --build

# 进入后端跑迁移
docker compose -p shortlink exec backend bash
cd /app && FLASK_APP=wsgi.py flask db upgrade
```

## 网络拓扑

```
[浏览器/HTTPS]
        │
        ▼
[云 LB / API 网关]:443
        │
        ▼
[shortlink-frontend nginx]:80   ←  静态 + /api/ /s/ 反代
        │
        ▼  (docker 网络 shortlink_net)
[shortlink-backend gunicorn]:5000
        │
        ├──→ [云 MySQL]:3306  (凭 DB_* env)
        └──→ [云 Redis]:6379  (凭 REDIS_* env)
```

## 排错速查

| 现象 | 检查 |
| --- | --- |
| 502 Bad Gateway | `docker compose ps` 看 backend 是否 healthy;查看 backend 日志 |
| 前端白屏 | 浏览器 F12 → Console;确认 nginx.conf `try_files` |
| 后端连不上 MySQL | 容器内 `mysql -h$DB_HOST -u$DB_USER -p` 验证;DB 安全组放行 |
| 后端连不上 Redis | `redis-cli -h $REDIS_HOST -a $REDIS_PASSWORD ping` |
| CORS 报错 | `CORS_ORIGINS` 没把前端域名加进去 |
