# =============================================================================
# ShortLink 后端镜像
# 基础镜像:python:3.11-slim(轻量,Debian)
# 启动:gunicorn -w N -b 0.0.0.0:5000 wsgi:app
# =============================================================================

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Shanghai

# 系统依赖:pymysql / cryptography 可能需要 build-essential
RUN apt-get update && apt-get install -y --no-install-recommends \
        tzdata \
        curl \
        gcc \
        libc-dev \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先装依赖(利用 Docker 缓存)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 再复制源码
COPY . .

# 非 root 运行
RUN useradd -m -u 1000 shortlink && chown -R shortlink:shortlink /app
USER shortlink

EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:5000/health || exit 1

# 默认启动 gunicorn(开发环境会改用 python wsgi.py)
CMD ["gunicorn", "--workers", "2", "--threads", "2", "--bind", "0.0.0.0:5000", "--access-logfile", "-", "--error-logfile", "-", "wsgi:app"]
