# ShortLink 架构文档(ARCHITECTURE)

> 本文用 mermaid 图描述 ShortLink 的整体架构、请求链路、数据模型、监控与部署拓扑。
> 配套文档:[`PRD.md`](PRD.md)(产品需求) / [`design.md`](design.md)(技术设计) / [`../README.md`](../README.md)(项目主页)。

---

## 1. 系统总览

```mermaid
flowchart LR
    User([用户浏览器])
    Admin([管理员])
    Dev([开发者/运维])

    subgraph Edge["🌐 边缘层"]
        LB[云 LB / CDN<br/>HTTPS 终结]
    end

    subgraph FE["前端层 Docker"]
        Nginx["nginx :80<br/>静态 SPA + 反向代理"]
    end

    subgraph BE["后端层 Docker"]
        Gunicorn["gunicorn :5000<br/>4 worker × 2 thread"]
        Flask["Flask App Factory<br/>8 个蓝图"]
    end

    subgraph Data["数据层(云托管)"]
        MySQL[("云 MySQL 5.7<br/>utf8mb4 / InnoDB")]
        Redis[("云 Redis 7<br/>限流 / 缓存 / UV")]
    end

    subgraph Obs["可观测性"]
        Prom[("Prometheus<br/>:9090")]
        Grafana[("Grafana<br/>:3000")]
        Logs[/"stdout JSON<br/>ELK / Loki"/]
    end

    User --> LB
    Admin --> LB
    Dev --> LB
    LB --> Nginx
    Nginx -->|"/api/* /s/* /metrics"| Gunicorn
    Nginx -->|"/ 静态"| Nginx
    Gunicorn --> Flask
    Flask --> MySQL
    Flask --> Redis
    Flask -.->|"/metrics 拉取"| Prom
    Prom --> Grafana
    Flask -.->|stdout| Logs
```

---

## 2. 请求链路(跳转主路径)

短码跳转 `/s/{code}` 是最高频请求,完整链路:

```mermaid
sequenceDiagram
    autonumber
    participant U as 用户
    participant N as nginx
    participant F as Flask
    participant R as Redis
    participant DB as MySQL

    U->>N: GET /s/0001iV
    N->>F: proxy_pass
    F->>R: GET shortlink:0001iV (查缓存)

    alt 缓存命中
        R-->>F: 短链记录(JSON)
        Note over F: 已校验状态/有效期<br/>(cache TTL 内不再查 DB)
    else 缓存未命中
        F->>DB: SELECT * WHERE short_code=?
        DB-->>F: ShortLink row
        F->>R: SETEX shortlink:0001iV 300 ...
    end

    F->>F: 校验状态 / expire_at / click_limit
    F->>R: INCR rate:ip:1.2.3.4 (限流 LUA)

    alt 限流命中
        F-->>U: 429 Too Many Requests
    else 通过
        F->>F: 访问控制 (IP/UA/Referer)
        F->>DB: INSERT click_logs (异步)
        F->>R: SADD short:0001iV:uv ... (UV 去重)
        F-->>U: 302 Location: long_url
    end
```

**关键点:**

- 缓存命中:亚毫秒级返回,DB 不参与
- 限流 LUA 脚本保证原子性,无需 race condition 加锁
- 写日志异步,不阻塞主链路

---

## 3. 数据模型(ER 图)

```mermaid
erDiagram
    USERS ||--o{ SHORT_LINKS : "创建"
    USERS ||--o{ CLICK_LOGS : "归属"
    SHORT_LINKS ||--o{ CLICK_LOGS : "被访问"
    SHORT_LINKS ||--o{ ACCESS_RULES : "访问控制"
    SHORT_LINKS ||--o{ BLACKLIST : "风控"

    USERS {
        bigint id PK
        varchar(64) username UK
        varchar(255) password_hash
        varchar(64) api_key UK
        boolean is_admin
        boolean is_active
        datetime created_at
    }

    SHORT_LINKS {
        bigint id PK
        bigint user_id FK
        varchar(16) short_code UK
        varchar(2048) long_url
        varchar(64) url_hash UK
        varchar(128) domain
        varchar(32) channel
        int visit_count
        varchar(255) password_hash
        varchar(16) status
        boolean is_deleted
        int click_limit
        datetime effective_at
        datetime expire_at
        datetime last_visit_at
        datetime created_at
    }

    CLICK_LOGS {
        bigint id PK
        bigint short_link_id FK
        varchar(45) ip
        varchar(512) user_agent
        varchar(512) referer
        varchar(64) country
        varchar(64) province
        varchar(64) city
        varchar(64) device
        varchar(64) browser
        varchar(64) os
        varchar(64) uv_fingerprint
        datetime created_at
    }

    ACCESS_RULES {
        bigint id PK
        bigint short_link_id FK
        varchar(32) type
        varchar(255) pattern
        boolean is_enabled
    }

    BLACKLIST {
        bigint id PK
        varchar(32) target_type
        varchar(255) target_value
        datetime expire_at
    }
```

**索引设计要点:**

- `short_links.short_code` 唯一索引 → 跳转 O(log n)
- `short_links.url_hash` 唯一索引 → 去重
- `(short_links.status, is_deleted)` 复合 → 列表过滤
- `(short_links.expire_at)` → 后台过期扫描
- `(click_logs.short_link_id, created_at)` 覆盖索引 → 趋势聚合不回表

---

## 4. 短码生成算法

```mermaid
flowchart LR
    A["DB 自增 ID<br/>(如 12345)"] -->|"| x = id |"| B["仿射变换<br/>y = (a*x + b) mod 62^L"]
    B -->|"| a = 131, b = 577<br/>L = 6 |"| C["Base62 编码<br/>0-9 A-Z a-z"]
    C -->|"| y = 8824137 |"| D["6 位短码<br/>如 '0001iV'"]

    E["短码<br/>0001iV"] --> F["Base62 解码<br/>→ 8824137"]
    F -->|"| 求 a 模逆元<br/>a_inv = pow(131,-1,62^6) |"| G["仿射逆变换<br/>x = a_inv*(y-b) mod 62^L"]
    G --> H["ID = 12345"]

    style A fill:#1e3a8a,color:#fff
    style D fill:#065f46,color:#fff
    style H fill:#065f46,color:#fff
```

**特性:**

- ✅ 可逆:短码 → ID 无需查表(但生产仍会缓存)
- ✅ 可控:`a` / `b` 一改就完全打散,防止爬取
- ✅ 定长:符合作业 6~8 位要求
- ✅ 容量:6 位 ≈ 568 亿 / 8 位 ≈ 218 万亿

---

## 5. 限流与反爬流程

```mermaid
flowchart TD
    Start([请求进入]) --> Kill{kill_switch<br/>紧急熔断?}
    Kill -->|是| S503[503 Service Unavailable]
    Kill -->|否| IPWL{IP 白名单<br/>启用?}
    IPWL -->|是 & 不在白名单| F403[403 Forbidden]
    IPWL -->|否 / 通过| UA{UA 反爬<br/>检查}

    UA -->|空 / 爬虫 UA| F403B[403 Forbidden]
    UA -->|通过| LR[查短链<br/>缓存 / DB]
    LR -->|404| NF[404 Not Found]
    LR -->|found| AC[访问控制<br/>IP/UA/Referer 黑白名单]
    AC -->|blocked| B404[404 隐藏存在]
    AC -->|observed| OBS[放行 + 观察]
    AC -->|allowed| STATE{状态校验<br/>enabled/expire/limit}

    STATE -->|malicious| M403[403 标记恶意]
    STATE -->|gone/expired| G410[410 Gone]
    STATE -->|needs_password| U401[401 需要密码]
    STATE -->|not_effective| NE403[403 未到生效]
    STATE -->|OK| RL[Redis 限流 LUA]

    RL -->|超限| RL429[429 Too Many Requests]
    RL -->|通过| Click[异步写 click_logs<br/>+ UV 去重]
    Click --> OK302[302 Found<br/>→ long_url]

    style S503 fill:#7f1d1d,color:#fff
    style F403 fill:#7f1d1d,color:#fff
    style F403B fill:#7f1d1d,color:#fff
    style B404 fill:#7f1d1d,color:#fff
    style M403 fill:#7f1d1d,color:#fff
    style G410 fill:#7f1d1d,color:#fff
    style U401 fill:#7f1d1d,color:#fff
    style NE403 fill:#7f1d1d,color:#fff
    style RL429 fill:#7f1d1d,color:#fff
    style OK302 fill:#065f46,color:#fff
```

---

## 6. 部署拓扑(生产)

```mermaid
flowchart TB
    subgraph Cloud["☁️ 云服务器"]
        FW[云防火墙<br/>安全组]
        LB[云 LB<br/>HTTPS :443]

        subgraph DockerHost["Docker Host"]
            subgraph Net["shortlink_net (bridge)"]
                FE["shortlink-frontend<br/>nginx :80<br/>↓ 映射 :53607"]
                BE["shortlink-backend<br/>gunicorn :5000"]
            end
        end
    end

    subgraph Managed["🗄️ 云托管服务"]
        DB[("云 MySQL<br/>:3306")]
        RD[("云 Redis<br/>:6379")]
    end

    subgraph Observability["📊 可观测性"]
        Prom[("Prometheus<br/>:9090")]
        Graf[("Grafana<br/>:3000")]
    end

    Browser([浏览器]) -->|HTTPS| LB
    LB -->|HTTP :53607| FW
    FW --> FE

    FE -->|"/api/* /s/* /metrics"| BE
    FE -->|"/ 静态资源"| FE

    BE -->|"DB_HOST:3306"| DB
    BE -->|"REDIS_HOST:6379"| RD

    BE -.->|"每 15s 拉取<br/>/metrics"| Prom
    Prom --> Graf
```

**关键配置项(`docker/.env`):**

| 变量 | 必填 | 示例 |
|---|---|---|
| `BASE_DOMAIN` | ✅ | `https://shortlink.lvhn.top` |
| `SECRET_KEY` | ✅ | `openssl rand -hex 32` |
| `DB_HOST/PORT/USER/PASSWORD/NAME` | ✅ | 云 MySQL 连接信息 |
| `REDIS_HOST/PORT/PASSWORD` | ✅ | 云 Redis 连接信息 |
| `CORS_ORIGINS` | ✅ | `https://shortlink.lvhn.top` |
| `FRONTEND_PORT` | - | `53607`(默认) |
| `GUNICORN_WORKERS/THREADS` | - | `4 / 2`(默认) |

---

## 7. 监控指标(`/metrics`)

系统通过 `GET /metrics` 暴露 Prometheus 格式指标:

```mermaid
flowchart LR
    subgraph BE["后端进程"]
        Counters[("Counter")]
        Gauges[("Gauge")]
        Histograms[("Histogram")]
    end

    Counters -->|"暴露"| M["/metrics 端点"]
    Gauges -->|"暴露"| M
    Histograms -->|"暴露"| M

    M -->|"scrape 每 15s"| Prom[Prometheus]
    Prom -->|"查询"| Graf[Grafana Dashboard]
    Prom -->|"alert"| Alert[Alertmanager<br/>钉钉 / 飞书]
```

**核心指标列表:**

| 指标 | 类型 | Labels | 用途 |
|---|---|---|---|
| `shortlink_created_total` | Counter | `domain` | 累计创建数,按域名分布 |
| `shortlink_redirect_total` | Counter | `status` | 累计跳转数,按结果分类(ok / not_found / expired / rate_limited / malicious / needs_password) |
| `shortlink_cache_total` | Counter | `result` | 缓存命中 / 未命中 |
| `rate_limit_hits_total` | Counter | `scope` | 限流命中(global / link) |
| `http_request_duration_seconds` | Histogram | `method`, `endpoint` | 请求耗时聚合(count / sum / avg / max) |
| `shortlink_count` | Gauge | `status` | 当前短链总数(enabled / disabled / malicious / total) |
| `process_uptime_seconds` | Gauge | - | 进程启动时长 |

**Grafana 推荐面板:**

- **业务**:PV / UV 趋势、Top 10 短链、状态分布
- **系统**:QPS、P50/P95 延迟、错误率
- **告警**:5xx > 1%、限流命中 > 100/min、`malicious` 状态 > 0

---

## 8. CI / CD 流水线

```mermaid
flowchart LR
    Dev([开发者]) -->|git push| GH[GitHub]
    GH -->|触发| CI[GitHub Actions]

    subgraph CI["CI Pipeline"]
        L1["lint<br/>eslint + flake8"]
        T1["test<br/>pytest"]
        B1["build<br/>frontend + backend image"]
    end

    CI -->|main 分支| Reg[GitHub Container Registry]
    Reg -->|webhook| Server[云服务器]

    subgraph Deploy["部署"]
        Pull[git pull] --> Up[docker compose up -d --build]
        Up --> HC{health check}
        HC -->|healthy| Done([部署完成])
        HC -->|unhealthy| Rollback[回滚到上一版本]
    end

    Server --> Pull
```

---

## 9. 安全防御纵深

```mermaid
flowchart TD
    Edge["🌐 边缘层"] -->|HTTPS| TLS[TLS 1.2+]
    TLS --> WAF[WAF / 云 CDN<br/>DDoS / SQLi 拦截]

    WAF --> APP[应用层]
    APP --> AUTH{鉴权<br/>JWT / API Key}
    AUTH -->|失败| E401[401]
    AUTH -->|通过| ACL{访问控制<br/>IP/UA/Referer}
    ACL -->|blocked| B404[404 隐藏存在]
    ACL -->|通过| RL[限流<br/>Redis LUA]
    RL -->|超限| E429[429]

    RL -->|通过| DATA[数据层]
    DATA --> ORM[SQLAlchemy<br/>参数化查询]
    DATA --> BCRYPT[bcrypt<br/>密码哈希]

    DATA --> AUDIT[审计日志<br/>click_logs]
```

**七层防御:**

1. **TLS** — 云 LB 终结 HTTPS,内部 HTTP
2. **WAF** — 云厂商 DDoS 防护
3. **鉴权** — JWT (HS256) + 过期 + refresh
4. **访问控制** — 业务层 IP / UA / Referer 黑白名单
5. **限流** — Redis LUA 滑动窗口
6. **ORM** — 全参数化,无字符串拼接
7. **审计** — click_logs 留痕,可回溯恶意访问

---

## 10. 文档导航

| 文档 | 关注点 |
|---|---|
| [`README.md`](../README.md) | 项目主页、快速开始 |
| [`PRD.md`](PRD.md) | 产品需求:功能清单、字段、规则 |
| [`design.md`](design.md) | 技术设计:模块、数据模型、接口、安全、性能 |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | 架构图:本文(全 mermaid) |
| [`作业说明.md`](../作业说明.md) | 作业二规格与本项目对照 |
| [`../docker/README.md`](../docker/README.md) | 云服务部署操作手册 |
