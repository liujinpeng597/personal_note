"""项目配置。"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
STATIC_DIR = BASE_DIR / "app" / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"


class Config:
    """默认配置。SECRET_KEY 允许由 create_app() 在运行时补全。"""

    SECRET_KEY = os.environ.get("NOTES_SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{INSTANCE_DIR.as_posix()}/notes.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 上传限制：2 MB
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    UPLOAD_FOLDER = str(UPLOAD_DIR)

    # 会话与 CSRF
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_ENABLED = True

    # 登录后的默认落地端点（Phase 4 起可用 notes.list）
    DEFAULT_LANDING_ENDPOINT = "main.home"
