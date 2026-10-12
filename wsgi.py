"""WSGI 入口：供容器内 gunicorn 调用（`gunicorn wsgi:app`）。

本地开发仍然用 `python run.py`（Flask 开发服务器）。
"""
from app import create_app

app = create_app()
