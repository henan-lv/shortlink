"""WSGI 入口。

开发模式:python wsgi.py
生产模式:gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
"""

import os

from app import create_app

app = create_app()


if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)
