# ShortLink 技术设计文档

> 配套文档:产品需求见 [`PRD.md`](PRD.md),部署说明见 [`docker/README.md`](../docker/README.md)。

## 0. 文档目的

本文档从**架构、模块、数据模型、接口、安全、性能**五个维度,描述 ShortLink 系统的设计与实现要点,作为后续维护与扩展的参考。

适用读者:后端 / 前端开发、SRE、Code Reviewer。

---

## 1. 系统总览

### 1.1 角色

| 角色 | 能力 |
| --- | --- |
| 匿名访客 | 通过 `/{base}/s/{code}` 访问短链,经密码 / 黑名单 / 限流校验后 302 跳转 |
| 注册用户 | 生成 / 管理自己的短链,查看统计 |
| 管理员 | 上述全部 + 进入「用户管理」增删改查 / 启停账号 / 重置 API Key |

### 1.2 部署形态

```
浏览器
  │
  ▼ HTTPS
[云 LB / Nginx]
  │
  ▼
[shortlink-frontend (nginx :80)]      ←  静态 SPA + 反向代理
  │   ├─ /         →  index.html (SPA)
  │   ├─ /assets/* →  静态资源
  │   ├─ /api/*    ─┐
  │   └─ /s/*      ─┼→  [shortlink-backend (gunicorn :5000)]
  │                 │       ├─→ 云 MySQL 5.7 (utf8mb4)
  │                 │       └─→ 云 Redis 7
  │                 │
  │           (docker 网络 shortlink_default)
```

- **仅打包前后端**,数据库与 Redis 走云服务,通过 `.env` 注入。
- 后端默认 4 worker × 2 thread(Gunicorn),通过 `GUNICORN_WORKERS` / `GUNICORN_THREADS` 调优。
- 前端外网端口默认 `53607`,可在 `docker/.env` 中改 `FRONTEND_PORT`。

---

## 2. 技术选型

### 2.1 后端

| 维度 | 选择 | 理由 |
| --- | --- | --- |
| Web 框架 | Flask 3.0 | 轻量、灵活,生态成熟,与 SQLAlchemy / Marshmallow / Flasgger 无缝配合 |
| ORM | SQLAlchemy 2.0 | 类型注解友好(`Mapped[...]`),社区标准 |
| 迁移 | Flask-Migrate(Alembic) | 模型变更可审计、可回滚 |
| 校验 | Marshmallow | 与 SQLAlchemy 模型可联动(`marshmallow-sqlalchemy`) |
| 文档 | Flasgger | 自动生成 Swagger UI,接口联调成本低 |
| 缓存 | Redis 7 | 限流、IP 黑名单缓存、UV 计数、Session |
| WSGI | Gunicorn | 生产级多进程,稳定 |

### 2.2 前端

| 维度 | 选择 | 理由 |
| --- | --- | --- |
| 框架 | Vue 3 Composition API | 组件复用度高,逻辑可抽离 `composables/` |
| 构建 | Vite 5 | 启动 / HMR 速度快,天然支持 `.env` |
| 状态 | Pinia | Vue 3 官方推荐,取代 Vuex |
| HTTP | Axios | 拦截器统一处理 401 / 错误提示 |
| 可视化 | ECharts | 折线 / 柱状 / 饼图 / 地图 覆盖统计全场景 |

### 2.3 数据存储

| 数据 | 存储 | 索引要点 |
| --- | --- | --- |
| 短链主数据 | MySQL `short_links` | `short_code` 唯一、`url_hash` 唯一、联合 `(status, is_deleted)`、`(expire_at)`、`(effective_at)` |
| 点击日志 | MySQL `click_logs` | `(short_link_id, created_at)`、`ip`、`ua` |
| 用户 | MySQL `users` | `username` 唯一、`api_key` 唯一 |
| 访问控制规则 | MySQL `access_rules` | `(short_link_id, type)` |
| 黑名单 / 限流 | Redis | `ip:{ip}` 滑动窗口、Set 结构 |

---

## 3. 架构分层

```
┌─────────────────────────────────────────────────────┐
│  前端 SPA (Vue 3)                                   │
│   ├─ Views  (Login / Generate / Links / Stats…)     │
│   ├─ Stores (Pinia: auth)                           │
│   ├─ API   (axios + 拦截器)                         │
│   └─ Router (路由守卫 + adminOnly)                  │
└─────────────────────────────────────────────────────┘
                       │  HTTPS / JSON
                       ▼
┌─────────────────────────────────────────────────────┐
│  Nginx (frontend 容器内)                            │
│   ├─ /          → 静态 SPA                          │
│   ├─ /assets/*  → 静态资源                          │
│   └─ /api/ /s/  → 反向代理 backend:5000             │
└─────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  Flask (gunicorn)                                   │
│                                                     │
│   ┌─────────────── API 蓝图层 ────────────────┐     │
│   │  short_link / links / stats / auth /      │     │
│   │  admin_users / access_rules / password /  │     │
│   │  health                                   │     │
│   └───────────────────────────────────────────┘     │
│                       │                              │
│   ┌─────────────── Service 业务层 ─────────────┐    │
│   │  short_code / short_link / access_control  │    │
│   │  anti_bot / rate_limit / analytics /       │    │
│   │  password / security / auth                │    │
│   └───────────────────────────────────────────┘     │
│                       │                              │
│   ┌─────────────── Model 数据层 ───────────────┐    │
│   │  SQLAlchemy 2.0 (Typed Mapped)             │    │
│   └───────────────────────────────────────────┘     │
│                                                     │
│   ┌─────────────── Middleware ─────────────────┐    │
│   │  auth 装饰器 / CORS / 全局异常 / 访问日志  │    │
│   └───────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────┘
              │                          │
              ▼                          ▼
        ┌──────────┐               ┌──────────┐
        │  MySQL   │               │  Redis   │
        └──────────┘               └──────────┘
```

**分层原则**

- **API 层**:只做参数解析(Schema)、调用 Service、返回统一格式,不允许直接写 SQL。
- **Service 层**:业务逻辑的核心,**事务边界**在这里控制,跨模型操作必须包在 `with db.session.begin():` 中。
- **Model 层**:只放字段映射和纯计算属性(如 `is_expired()`),不放业务规则。

---

## 4. 关键模块设计

### 4.1 短码生成(自增 ID → 仿射变换 → Base62)

**位置**:`backend/app/services/short_code.py`

**算法**

```
y = (a * x + b) mod 62^L
short_code = Base62.encode(y, pad=L)   # L = SHORT_CODE_MIN_LENGTH
```

- `x`:自增主键 `id`(从 1 开始)
- `a` = `SHORT_CODE_AFFINE_MULTIPLIER`(默认 131),与 `62^L` 互质,保证双射
- `b` = `SHORT_CODE_AFFINE_OFFSET`(默认 577)
- 逆变换:`x = a_inv * (y - b) mod 62^L`(扩展欧几里得求模逆元)

**优势**

- **可逆**:短码 → ID,无需建索引查表(但生产仍会缓存到 Redis)。
- **可控**:`SHORT_CODE_AFFINE_*` 改个值就完全打散,防止被爬取猜测下一条。
- **定长**:6 位能容纳约 568 亿条(`62^6 - 1`),8 位约 218 万亿,业务够用。

**校验**

```python
validate_params(multiplier, offset, length):
  gcd(multiplier, 62^length) == 1
  1 <= length <= 16
  0 <= offset < 62^length
```

启动时 `create_app` 会跑一次校验,失败直接拒绝启动,杜绝线上出错。

### 4.2 短链生成链路

```
POST /api/shortlinks
  ↓
[Schema] 校验 long_url / domain / channel / 有效期
  ↓
[Service]
  1. url_hash = sha256(long_url + domain + channel)
  2. SELECT * WHERE url_hash = ?  → 命中则直接返回(幂等)
  3. INSERT short_links (status=enabled, visit_count=0, ...)
     → DB 自增拿到 id
  4. short_code = encode_id(id, a, b, L)
  5. UPDATE short_links SET short_code = ? WHERE id = ?
  6. 写 click_logs(可选,记录创建事件)
  ↓
返回 { short_code, full_short_url, ... }
```

**幂等保证**:`(url_hash)` 唯一索引。同长链 + 同域名 + 同渠道重复请求,直接返回已有短码,避免重复创建。

### 4.3 短链访问链路(302 跳转)

```
GET /s/{short_code}
  ↓
1. Redis 查 short_code → 完整记录(命中走缓存,未命中回源 MySQL)
  ↓
2. 状态校验:status != enabled → 410 / malicious → 黑名单页
  ↓
3. 时间校验:expire_at / effective_at → 未到 / 已过期直接 410
  ↓
4. 访问控制(详见 4.5)
  ↓
5. 限流(Redis 滑动窗口,默认 60 req/min/IP)→ 命中 → 429
  ↓
6. 反爬(anti_bot):UA / Referer 校验
  ↓
7. ASYNC 写 click_logs(队列 / 异步任务)
  ↓
8. 302 Location: long_url
```

**性能要点**

- 缓存命中:1 次 Redis GET + 1 次 LUA → 亚毫秒级返回。
- 异步写日志:不阻塞主链路,失败可重试,避免统计误差放大。
- 限流 LUA 脚本保证原子性,见 `services/rate_limit.py`。

### 4.4 统计聚合(analytics)

```
api/shortlinks/{code}/stats       → 汇总:PV / UV / 时段
api/shortlinks/{code}/trend       → 30 天 / 24h 折线
api/shortlinks/{code}/breakdown   → 来源 / UA / 地域 饼图
api/shortlinks/{code}/visitors    → 最近访问明细(IP / UA / 时间)
api/shortlinks/{code}/realtime    → 实时近 5 分钟
api/stats/overview/*              → 全局聚合(全用户)
```

**UV 计算**:Redis `SET short:{code}:uv` + `SADD`,每次访问把 `ip + ua` 算指纹塞进去,`SCARD` 出 UV。定时清理过期数据。

**趋势数据**:基于 `click_logs` 表 `GROUP BY DATE(created_at)` / `GROUP BY HOUR(created_at)`。索引覆盖 `(short_link_id, created_at)`。

### 4.5 访问控制(access_control)

`AccessRule.type`:

| type | 含义 | 匹配 |
| --- | --- | --- |
| `ip_whitelist` | IP 白名单 | 精确 IP |
| `ip_blacklist` | IP 黑名单 | 精确 IP + CIDR(如 `192.168.1.0/24`) |
| `ua_blacklist` | UA 黑名单 | 子串匹配(忽略大小写) |
| `referer_blacklist` | Referer 黑名单 | 域名匹配 |

**优先级**

```
白名单(whitelist) > 黑名单 > 默认放行
```

白名单一旦命中,**绕过所有其他规则**(包括密码),用于紧急放行某个合作方。

**API**

```
GET    /api/access-rules?short_code=xxx        列出某短链的规则
POST   /api/access-rules                      新建
PATCH  /api/access-rules/{id}                 启停 / 修改
DELETE /api/access-rules/{id}                 删除
```

### 4.6 鉴权(auth)

- **JWT**(HS256,密钥 `SECRET_KEY`),过期 7 天。
- Header:`Authorization: Bearer <token>`
- 装饰器:
  - `@login_required` — 需要登录
  - `@admin_required` — 需要管理员(仅 `users.is_admin = 1` 通过)
- `User.is_active = 0` 的账号直接 403,管理员可在「用户管理」停用。

**首注册自动管理员**:首个 `POST /api/auth/register` 请求,注册成功后 `users.is_admin = 1`。后续注册的用户默认 `is_admin = 0`,需现有管理员在用户管理页授权。

### 4.7 管理员用户管理(admin_users)

```
GET    /api/admin/users                 列表(分页 / 搜索)
POST   /api/admin/users                 创建账号
PATCH  /api/admin/users/{id}            修改(角色 / 启停 / 重置密码)
DELETE /api/admin/users/{id}            软删除(is_active=0 或真删)
POST   /api/admin/users/{id}/regenerate-key  重置 API Key
```

**前端** `views/Users.vue` 仅 `isAdmin` 可见,导航守卫 + 路由 meta 双层保护。

---

## 5. 数据模型

### 5.1 ER 概览

```
users ───┐
         │ 1:N
         ▼
     short_links ───┐
         │ 1:N      │ 1:N
         ▼          ▼
     click_logs   access_rules
```

### 5.2 关键字段

**`users`**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | BIGINT PK | 自增 |
| `username` | VARCHAR(64) UNIQUE | 用户名 |
| `password_hash` | VARCHAR(255) | bcrypt |
| `api_key` | VARCHAR(64) UNIQUE NULL | 接口调用凭证 |
| `is_admin` | BOOLEAN | 管理员标记,首注册自动 true |
| `is_active` | BOOLEAN | 启停,默认 true |
| `created_at` | DATETIME | 注册时间 |

**`short_links`**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | BIGINT PK | 自增,短码生成的输入 |
| `user_id` | BIGINT FK | 创建者,逻辑外键 |
| `short_code` | VARCHAR(16) UNIQUE | 短码 |
| `long_url` | VARCHAR(2048) | 原始长链 |
| `url_hash` | VARCHAR(64) UNIQUE | sha256(long_url+domain+channel),幂等键 |
| `domain` | VARCHAR(128) NULL | 自定义域名 |
| `channel` | VARCHAR(32) NULL | 渠道(微信 / 公众号 / APP) |
| `visit_count` | INT | PV 冗余字段,定期与 click_logs 校对 |
| `password_hash` | VARCHAR(255) NULL | 短链访问密码(bcrypt) |
| `status` | VARCHAR(16) | enabled / disabled / malicious |
| `is_deleted` | BOOLEAN | 软删 |
| `click_limit` | INT NULL | 点击上限 |
| `effective_at` / `expire_at` / `deleted_at` | DATETIME NULL | 生命周期 |
| `last_visit_at` | DATETIME NULL | 最近访问,用于"X 分钟前"展示 |

**`click_logs`**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | BIGINT PK | |
| `short_link_id` | BIGINT | 关联短链 |
| `ip` | VARCHAR(45) | 支持 IPv6 |
| `user_agent` | VARCHAR(512) | |
| `referer` | VARCHAR(512) NULL | |
| `country` / `province` / `city` | VARCHAR(64) NULL | IP 解析 |
| `device` / `browser` / `os` | VARCHAR(64) NULL | UA 解析 |
| `uv_fingerprint` | VARCHAR(64) | sha256(ip+ua),用于 UV 去重 |
| `created_at` | DATETIME | 索引 |

**`access_rules`**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | BIGINT PK | |
| `short_link_id` | BIGINT | 关联短链 |
| `type` | VARCHAR(32) | ip_whitelist / ip_blacklist / ua_blacklist / referer_blacklist |
| `pattern` | VARCHAR(255) | 匹配值(IP / CIDR / 子串) |
| `is_enabled` | BOOLEAN | 启停 |

### 5.3 迁移

所有变更通过 Alembic:

```
backend/migrations/versions/
├── a9f2fc5aea29_init_shortlinks_click_logs_users_.py
├── b1f3a7d4c8e2_add_shortlink_effective_at.py
├── c7a1e3b9d2f4_add_shortlink_domain_channel.py
├── d4e8b2c1a9f7_add_access_rules.py
└── e5b9c4d2a1f3_add_user_admin_active.py
```

部署时:`cd backend && FLASK_APP=wsgi.py flask db upgrade`

---

## 6. 接口约定

### 6.1 统一响应格式

```json
{
  "code": 0,
  "message": "ok",
  "data": { ... }
}
```

错误:

```json
{
  "code": 40001,
  "message": "参数错误",
  "data": null,
  "errors": { "field": ["msg"] }
}
```

`code = 0` 表示成功,非 0 为业务错误码,前端 `utils/request.js` 拦截器统一弹 toast。

### 6.2 鉴权

- 登录 / 注册:`/api/auth/*`,无需 token。
- 其他 `/api/*`:`Authorization: Bearer <jwt>`,无 token → 401。
- `/s/{code}`:无需 token(匿名访问)。

### 6.3 错误码表(节选)

| code | 含义 |
| --- | --- |
| 0 | 成功 |
| 40001 | 参数校验失败 |
| 40100 | 未登录 / token 过期 |
| 40300 | 无权限(非管理员访问管理员接口) |
| 40301 | 账号已停用 |
| 40401 | 短链不存在 |
| 40402 | 访问规则不存在 |
| 41000 | 短链已过期 / 未生效 / 已停用 |
| 41001 | 短链点击上限已达 |
| 41002 | 短链需要密码 |
| 42900 | 触发限流 |
| 50000 | 服务异常 |

### 6.4 接口清单(摘要)

**链接管理**

```
POST   /api/shortlinks                 生成
GET    /api/links                      列表(分页 / 搜索 / 筛选)
GET    /api/links/{code}               详情
PATCH  /api/links/{code}               修改
DELETE /api/links/{code}               软删
POST   /api/links/{code}/restore       恢复
GET    /s/{code}                       跳转
```

**统计**

```
GET    /api/stats/overview             全局概览
GET    /api/stats/overview/trend       全局趋势
GET    /api/stats/overview/breakdown   全局维度
GET    /api/stats/overview/alerts      异常告警(过期 / 限流命中)
GET    /api/stats/overview/realtime    全局实时
GET    /api/shortlinks/{code}/stats    单链汇总
GET    /api/shortlinks/{code}/trend    单链趋势
GET    /api/shortlinks/{code}/breakdown
GET    /api/shortlinks/{code}/visitors
GET    /api/shortlinks/{code}/realtime
GET    /api/shortlinks/{code}/export   CSV 导出
```

**访问控制**

```
POST   /api/shortlinks/{code}/verify-password
GET    /api/access-rules
POST   /api/access-rules
PATCH  /api/access-rules/{id}
DELETE /api/access-rules/{id}
```

**鉴权**

```
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/auth/me
```

**管理员**

```
GET    /api/admin/users
POST   /api/admin/users
PATCH  /api/admin/users/{id}
DELETE /api/admin/users/{id}
POST   /api/admin/users/{id}/regenerate-key
```

**健康检查**

```
GET    /health                         存活
```

完整 Swagger:`http://<host>:5000/apidocs`

---

## 7. 安全设计

### 7.1 密码

- 用户密码:**bcrypt**(`werkzeug.security.generate_password_hash`)。
- 短链访问密码:**bcrypt** + 内存中校验,不写日志。
- 数据库 / Redis 密码:**环境变量**,不进仓库。

### 7.2 鉴权

- JWT(HS256) + 过期 7 天。
- 管理员接口双层校验:路由 meta + 后端装饰器。
- 关键操作(删除用户 / 重置密码)要求**二次确认**(前端 modal)。

### 7.3 输入校验

- 所有入参过 **Marshmallow Schema**,失败直接 40001,绝不进入 Service 层。
- `long_url` 限定 `http(s)://`,拒绝 `javascript:` / `file:` / `data:`。
- 短码限定 `[0-9A-Za-z]{1,16}`,并校验长度匹配。
- 域名 / Referer 长度限制 + 黑名单后缀(防 SSRF)。

### 7.4 限流 / 反爬

- 全局 IP 限流:Redis 滑动窗口,**默认 60 req/min/IP**,超过 → 429。
- 单链限流:可独立配置,默认 600 req/min/IP。
- UA 空 / 明显爬虫(`python-requests`、`scrapy`、`curl/*` 等)→ 直接 403。
- Referer 黑名单命中 → 403。
- 短时间高频访问同 IP → 自动加入临时黑名单(Redis TTL 10 分钟)。

### 7.5 风控

- 恶意链接(`status=malicious`)→ 全局黑名单,所有路径访问都拒绝。
- 创建时检测长链是否命中黑名单库(可扩展)。
- 异常峰值告警:同一短链 PV 突增 5x → 推送到管理员(预留接口)。

### 7.6 数据安全

- 所有 `.env` / 证书 / `*.pem` 已在 `.gitignore` 中排除。
- 生产环境**关闭 Flask Debug**(`FLASK_DEBUG=0`)。
- 关键 SQL 全部走 ORM / 参数化,无字符串拼接。
- CORS 白名单通过 `CORS_ORIGINS` 配置,默认拒绝跨域。

---

## 8. 性能与容量

### 8.1 容量估算(单实例)

| 维度 | 量级 |
| --- | --- |
| 短链数 | 6 位 ≈ 568 亿,8 位 ≈ 218 万亿(理论上限) |
| QPS(跳转) | 单 worker 8k ~ 15k,Gunicorn 4 worker ≈ 4w |
| MySQL 写入 | `click_logs` 是主写入源,建议日增 100w 内走单实例 |
| Redis | 限流 LUA + 短链缓存 + UV Set,8G 内存可支撑千万级 UV |

### 8.2 优化手段(已实施)

- **短链缓存**:跳转接口先查 Redis,未命中回源 MySQL 并回填。
- **限流 LUA**:Redis 单脚本完成「读 → 判 → 写 → 返」,避免 race condition。
- **UV 去重**:基于 `SADD + SCARD`,O(1) 插入 / O(1) 计数。
- **写日志异步**:click_logs 不阻塞主链路,失败可重试。
- **索引覆盖**:所有高频查询都有 `(short_link_id, created_at)` 复合索引。

### 8.3 后续可扩展点

- 短链缓存预热 / 多级缓存(本地 LRU + Redis)。
- click_logs 走分区表(按月)或迁 ClickHouse。
- 引入 CDN 边缘节点,跳转走最近节点。
- 接口幂等性:Redis Token 防重放。

---

## 9. 前端架构

### 9.1 目录

```
frontend/src/
├── api/         axios 请求封装
├── views/       页面级组件
├── components/  通用组件
├── composables/ 可复用组合式逻辑
├── stores/      Pinia
├── router/      Vue Router(守卫)
├── utils/       工具函数
└── styles/      全局样式
```

### 9.2 关键设计

- **统一拦截器** `api/request.js`:
  - 请求注入 `Authorization`
  - 响应 401 → 清 token + 跳登录
  - 业务错误 → 统一 toast,避免每页重复写
- **路由守卫**:
  - 未登录 → 跳 `/login`
  - `meta.adminOnly = true` → `isAdmin` 不通过跳 `/links`
- **Pinia `auth`** 暴露:
  - `token` / `user` / `isAdmin` / `login()` / `logout()`
- **生成弹窗** `Generate.vue`:用 `<Teleport>` 渲染到 body,避免父级 `overflow:hidden` 截断。

### 9.3 Vite 配置要点

- `loadEnv(mode, process.cwd())` 读 `.env`
- `server.proxy` 把 `/api` / `/s` 反代到后端(开发期避免 CORS)
- 生产由 Nginx 反代,前端代码里全是相对路径

---

## 10. 部署与运维

### 10.1 Docker 镜像

- **backend**:`python:3.11-slim` + Gunicorn
  - 启动:`gunicorn -w $GUNICORN_WORKERS -k gthread --threads $GUNICORN_THREADS -b 0.0.0.0:5000 wsgi:app`
  - healthcheck:`curl http://127.0.0.1:5000/health`
- **frontend**:多阶段
  - 构建:`node:20-alpine` 跑 `npm run build`
  - 运行时:`nginx:alpine` 托管 `/usr/share/nginx/html`

### 10.2 启动顺序

```
1. 云 MySQL / Redis 预创建
2. 容器外跑迁移:FLASK_APP=wsgi.py flask db upgrade
3. docker compose -p shortlink up -d --build
4. depends_on: backend healthy → frontend start
```

### 10.3 常用命令

```bash
# 查看日志
docker compose -p shortlink logs -f --tail=200 backend
docker compose -p shortlink logs -f --tail=200 frontend

# 重启
docker compose -p shortlink restart backend

# 跑迁移
docker compose -p shortlink exec backend bash
FLASK_APP=wsgi.py flask db upgrade

# 回滚
docker compose -p shortlink down
git pull && docker compose -p shortlink up -d --build
```

### 10.4 监控(预留)

- `/health`:存活探针
- 日志统一 stdout(JSON 格式可对接 ELK / Loki)
- 后续可加 Prometheus exporter(`/metrics`)

---

## 11. 未来 Roadmap

| 阶段 | 内容 |
| --- | --- |
| P1 | 短链 AB 测试(同一长链多短码,按权重分流) |
| P1 | 短链二维码 + 海报生成 |
| P1 | Webhook:访问触发回调(企业微信 / 飞书 / 钉钉) |
| P2 | 多租户:每个团队独立空间、独立域名、独立统计 |
| P2 | Open API:对外提供完整的 RESTful 接口 + OpenAPI 3.0 文档 |
| P2 | 数据看板:导出 PDF 周报 |
| P3 | AI:恶意链接自动识别 + 长链标题智能提取 |

---

## 附录 A:环境变量

完整列表见 [`backend/.env.example`](../backend/.env.example) 与 [`docker/.env.example`](../docker/.env.example)。

**关键项**

| 变量 | 说明 | 示例 |
| --- | --- | --- |
| `SECRET_KEY` | JWT / Flask session 密钥 | `openssl rand -hex 32` |
| `DATABASE_URL` 或 `DB_*` | MySQL 连接 | `mysql+pymysql://user:pwd@host:3306/db?charset=utf8mb4` |
| `REDIS_URL` 或 `REDIS_*` | Redis 连接 | `redis://:pwd@host:6379/0` |
| `BASE_DOMAIN` | 短链域名(返回时拼 full_short_url) | `https://s.example.com` |
| `SHORT_CODE_MIN_LENGTH` | 短码位数 | `6` |
| `SHORT_CODE_AFFINE_MULTIPLIER` | 仿射 a | `131` |
| `SHORT_CODE_AFFINE_OFFSET` | 仿射 b | `577` |
| `CORS_ORIGINS` | 跨域白名单 | `https://s.example.com` |
| `FRONTEND_PORT` | 前端外网端口 | `53607` |
| `GUNICORN_WORKERS` / `GUNICORN_THREADS` | 并发调优 | `4` / `2` |

## 附录 B:扩展点 Checklist

新加一个功能时,通常需要触碰的文件:

```
backend/app/
├── models/        + 新模型
├── schemas/       + 新 Schema
├── services/      + 新业务模块
├── api/           + 新蓝图(并在 __init__.py 注册)
└── migrations/    + alembic revision --autogenerate

frontend/src/
├── api/           + 新接口模块
├── views/         + 新页面(并在 router 注册)
├── stores/        (可选)新 store
└── components/    + 新组件
```
