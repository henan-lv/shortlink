# 短链接服务 ShortLink

> 长链转短链 · 302 跳转 · 访问统计 · 生命周期管理 · 访问控制 · 多人协作

一个面向运营 / 推广场景的短链平台:支持自定义短码、密码保护、有效期、点击上限、按 IP / CIDR 黑白名单、按渠道分流,以及 PV / UV / 时段 / 来源 / 地域等维度的访问监控。

- 📄 需求文档:[`docs/PRD.md`](docs/PRD.md)
- 🏗️ 技术设计:[`docs/design.md`](docs/design.md)
- 🗺️ 架构图(含 mermaid):[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- 🚀 云服务部署:[`docker/README.md`](docker/README.md)

---

## ✨ 功能特性

**核心能力**

- 🔗 长链 → 短链,6 位定长短码(可配置 1–16 位),Base62 + 仿射变换
- 🚀 短链访问 302 跳转,带访问控制校验后才放行
- 📊 访问统计:PV / UV / 24h 时段 / 30 天趋势 / 来源 / 地域 / UA / Referer
- ⏱️ 生命周期:`effective_at` 生效时间 / `expire_at` 过期时间 / `click_limit` 点击上限
- 🔐 访问控制:链接密码、IP 黑白名单、CIDR 网段、UA 黑名单、Referer 黑名单

**平台能力**

- 👤 多用户系统,首个注册用户自动成为管理员
- 🛡️ 管理员后台:用户管理(增删改查 / 启停 / 重置密码 / 重置 API Key)
- 🔑 用户级 API Key,支持接口调用鉴权
- 🧰 Swagger 接口文档(`/apidocs`)
- 📈 Prometheus 监控指标(`/metrics`):创建数 / 跳转结果 / 限流命中 / 请求耗时 / 短链总数
- 🐳 一键 Docker 部署(仅前后端,DB / Redis 走云)

---

## 🧱 技术栈

**后端** `backend/`

| 模块 | 技术 |
| --- | --- |
| Web 框架 | Flask 3.0 |
| ORM | SQLAlchemy 2.0 + Flask-Migrate(Alembic) |
| 校验 / 序列化 | Marshmallow |
| 接口文档 | Flasgger(Swagger UI) |
| 数据库 | MySQL 5.7+(utf8mb4,InnoDB) |
| 缓存 / 限流 | Redis 7 |
| WSGI | Gunicorn(生产) / Flask dev server(本地) |

**前端** `frontend/`

| 模块 | 技术 |
| --- | --- |
| 框架 | Vue 3(Composition API) |
| 构建 | Vite 5 |
| 路由 / 状态 | Vue Router 4 + Pinia |
| HTTP | Axios(统一拦截 + 401 自动跳转登录) |
| 可视化 | ECharts(折线 / 柱状 / 饼图 / 地图) |

**部署** `docker/`

- 后端镜像: `python:3.11-slim` + Gunicorn
- 前端镜像: 多阶段 Node 构建 → Nginx 静态托管 + 反向代理
- 编排: Docker Compose v2
- 数据库 / Redis: 走云服务,环境变量注入

---

## 📁 目录结构

```
短链服务/
├── backend/                     # Flask 后端
│   ├── app/
│   │   ├── api/                 # 蓝图路由
│   │   │   ├── short_link.py    #   生成 / 跳转 / 链接管理
│   │   │   ├── stats.py         #   访问监控
│   │   │   ├── auth.py          #   登录 / 注册 / 鉴权
│   │   │   ├── admin_users.py   #   用户管理(管理员)
│   │   │   ├── access_rules.py  #   IP / UA / Referer 黑白名单
│   │   │   ├── password.py      #   密码访问
│   │   │   └── health.py        #   健康检查
│   │   ├── models/              # SQLAlchemy 模型
│   │   │   ├── short_link.py    #   短链表
│   │   │   ├── click_log.py     #   点击日志
│   │   │   ├── user.py          #   用户表
│   │   │   ├── access_rule.py   #   访问控制规则
│   │   │   └── blacklist.py     #   恶意黑名单
│   │   ├── schemas/             # Marshmallow 请求 / 响应校验
│   │   ├── services/            # 业务逻辑层
│   │   │   ├── short_code.py    #   仿射变换 + Base62 短码算法
│   │   │   ├── short_link.py    #   短链 CRUD
│   │   │   ├── access_control.py#   IP / UA / Referer / CIDR 校验
│   │   │   ├── anti_bot.py      #   UA / Referer / 速率 反爬
│   │   │   ├── rate_limit.py    #   Redis 滑动窗口限流
│   │   │   ├── analytics.py     #   统计聚合(PV/UV/时段/来源)
│   │   │   ├── password.py      #   短链密码
│   │   │   └── security.py      #   风控 / 恶意拦截
│   │   ├── middleware/          # 鉴权 / CORS / 全局异常
│   │   ├── utils/               # Base62 / 哈希 / IP / 统一响应
│   │   ├── config.py
│   │   ├── extensions.py        # db / ma / migrate 实例
│   │   └── __init__.py          # create_app 工厂
│   ├── migrations/              # Alembic 迁移脚本
│   ├── tests/
│   ├── .env.example
│   ├── requirements.txt
│   └── wsgi.py                  # 入口(支持 dev / gunicorn)
│
├── frontend/                    # Vue 3 前端
│   ├── src/
│   │   ├── api/                 # axios 请求封装
│   │   │   ├── request.js       #   拦截器(401 → 登录 / 错误提示)
│   │   │   ├── auth.js
│   │   │   ├── shortlink.js
│   │   │   └── users.js         #   管理员用户管理接口
│   │   ├── views/
│   │   │   ├── Login.vue        #   登录 + 注册(弹窗,首位自动管理员)
│   │   │   ├── Generate.vue     #   生成短链(Teleport 弹窗)
│   │   │   ├── Links.vue        #   短链列表(搜索 / 启停 / 删除)
│   │   │   ├── Stats.vue        #   全局统计
│   │   │   ├── StatsDetail.vue  #   单链详情(高级设置 + 多维图表)
│   │   │   ├── Password.vue     #   短链密码输入
│   │   │   └── Users.vue        #   用户管理(管理员)
│   │   ├── stores/auth.js       #   Pinia(token / user / isAdmin)
│   │   ├── router/index.js      #   路由 + adminOnly 守卫
│   │   ├── components/
│   │   ├── composables/
│   │   ├── styles/
│   │   └── App.vue              #   全局壳(导航 + 主题)
│   ├── vite.config.js           #   代理 / 端口 / 路径
│   └── package.json
│
├── docker/                      # 云服务部署包(仅前后端)
│   ├── docker-compose.yaml
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── nginx.conf
│   ├── .env.example
│   └── README.md
│
├── docs/
│   ├── PRD.md                   # 产品需求
│   └── design.md                # 技术设计(本文档姊妹篇)
│
├── deploy/                      # 本地全栈部署(可选,含 MySQL / Redis)
├── bin/
├── .gitignore
└── README.md
```

---

## 🚀 快速开始(本地开发)

### 0. 环境要求

- Python ≥ 3.11(推荐 Conda 隔离环境)
- Node.js ≥ 18
- MySQL 5.7+(或本地 Docker 起一个)
- Redis 7+

### 1. 准备数据库 & Redis

最省事的方式是用项目自带的 `deploy/`:

```bash
cd deploy
docker compose -f docker-compose.dev.yml up -d mysql redis
```

### 2. 启动后端

```bash
cd backend
cp .env.example .env
# 编辑 .env:DATABASE_URL / REDIS_URL / SECRET_KEY / BASE_DOMAIN ...

pip install -r requirements.txt
FLASK_APP=wsgi.py flask db upgrade     # 跑迁移建表
python wsgi.py                          # 默认 http://127.0.0.1:5000
```

**接口文档:**

- Swagger UI:<http://127.0.0.1:5000/apidocs>
- Prometheus 监控指标:<http://127.0.0.1:5000/metrics>(文本格式,接 Prometheus / Grafana)

**监控示例:**

```bash
curl http://127.0.0.1:5000/metrics | head -30
# 关键指标:
#   shortlink_created_total{domain="..."}     累计创建数
#   shortlink_redirect_total{status="..."}    累计跳转数(ok/not_found/expired/...)
#   rate_limit_hits_total{scope="..."}        限流命中
#   shortlink_count{status="..."}             当前短链总数
#   http_request_duration_seconds             请求耗时
```

接 Prometheus 只需在 `prometheus.yml` 加:

```yaml
scrape_configs:
  - job_name: shortlink
    scrape_interval: 15s
    metrics_path: /metrics
    static_configs:
      - targets: ["shortlink.lvhn.top:443"]
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev     # 默认 http://127.0.0.1:5173
```

前端 `vite.config.js` 通过 `VITE_BASE_DOMAIN` 决定 `/api` / `/s` 反向代理的目标后端,无需前端单独配置 CORS。

### 4. 第一个账号

打开 <http://127.0.0.1:5173>,点「立即注册」,**首位注册的用户自动成为管理员**,可以进入「用户管理」管理后续注册的账号。

---

## 🐳 一键部署(云服务)

详细步骤见 [`docker/README.md`](docker/README.md)。

**TL;DR:**

```bash
cd docker
cp .env.example .env
vim .env   # 填入 DB_* / REDIS_* / SECRET_KEY / CORS_ORIGINS

# 跑迁移(在容器外,直连云 MySQL)
cd ../backend
FLASK_APP=wsgi.py flask db upgrade

# 启动
cd ../docker
docker compose -p shortlink up -d --build
```

**网络拓扑:**

```
浏览器
  ↓ HTTPS
云 LB / API 网关
  ↓
shortlink-frontend (nginx :80 / :53607)
  ├─ /api/*  ──→  shortlink-backend (gunicorn :5000)
  └─ /s/*    ──→  shortlink-backend
                  ├─→ 云 MySQL
                  └─→ 云 Redis
```

---

## 📚 文档导航

| 文档 | 用途 |
| --- | --- |
| [`docs/PRD.md`](docs/PRD.md) | 产品需求:功能清单、字段定义、业务规则 |
| [`docs/design.md`](docs/design.md) | 技术设计:架构、模块、数据模型、接口、安全、性能 |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | 架构图(9 张 mermaid):系统总览、请求链路、ER、部署拓扑、监控、CI/CD 等 |
| [`docker/README.md`](docker/README.md) | 云服务部署:Docker Compose、环境变量、运维命令、排错 |

---

## 🔐 安全提示

仓库 `.gitignore` 已默认排除:

- `.env` / `.envrc` 及各种 `.env.*` 文件
- 证书文件:`*.pem` / `*.key` / `*.crt` / `*.p12`
- 本地数据库:`*.sqlite3` / `*.db` / `backend/instance/`
- 云厂商凭证:`.aws/` / `.aliyun/` / `.tencent/` 等
- 部署密钥文件:`docker/.env`

提交前请再次确认没有把真实密钥、数据库密码、云 API Key 推到仓库。

---

## 📝 License

仅供学习与个人项目使用,商用需自行评估合规风险。
