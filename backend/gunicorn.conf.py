"""生产环境 gunicorn 配置。"""

import multiprocessing
import os

bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:5000")
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
threads = int(os.environ.get("GUNICORN_THREADS", 2))
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "gthread")

timeout = int(os.environ.get("GUNICORN_TIMEOUT", 60))
graceful_timeout = 30
keepalive = 5

# 日志
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s '
    '%(b)s "%(f)s" "%(a)s" %(L)s'
)

# 进程名
proc_name = "shortlink"

# 预加载应用(节省内存,加快 worker 启动)
preload_app = True
