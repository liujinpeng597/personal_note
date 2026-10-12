"""应用工厂。"""
import secrets

from flask import Flask, render_template, request
from werkzeug.exceptions import HTTPException

from app.extensions import db
from app.utils.markdown_render import render_markdown
from app.utils.responses import fail
from app.utils.security import register_csrf, register_template_context
from config import INSTANCE_DIR, UPLOAD_DIR, Config


def _ensure_secret_key(app):
    if app.config.get("SECRET_KEY"):
        return
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    key_file = INSTANCE_DIR / "secret_key"
    if key_file.exists():
        app.config["SECRET_KEY"] = key_file.read_text(encoding="utf-8").strip()
    else:
        key = secrets.token_urlsafe(32)
        key_file.write_text(key, encoding="utf-8")
        app.config["SECRET_KEY"] = key


def _wants_json():
    if request.path.startswith("/api"):
        return True
    if request.method != "GET":
        return True
    return "application/json" in (request.headers.get("Accept") or "")


def _register_error_handlers(app):
    def respond(code, status):
        if _wants_json():
            return fail(code, status=status)
        return render_template(f"errors/{status}.html"), status

    @app.errorhandler(404)
    def _not_found(_error):
        return respond("ERR_NOT_FOUND", 404)

    @app.errorhandler(410)
    def _gone(_error):
        return respond("ERR_SHARE_REVOKED", 410)

    @app.errorhandler(413)
    def _too_large(_error):
        return respond("ERR_FILE_TOO_LARGE", 413)

    @app.errorhandler(Exception)
    def _unexpected(error):
        if isinstance(error, HTTPException):
            mapping = {401: "ERR_UNAUTHORIZED", 403: "ERR_FORBIDDEN", 415: "ERR_FILE_TYPE"}
            code = mapping.get(error.code)
            if code:
                return respond(code, error.code)
            if error.code and 400 <= error.code < 500:
                return respond("ERR_VALIDATION", error.code)
        app.logger.exception("未处理异常: %s", error)
        return respond("ERR_SERVER", 500)


def _register_blueprints(app):
    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.main import bp as main_bp
    from app.blueprints.notes import bp as notes_bp
    from app.blueprints.share import bp as share_bp
    from app.blueprints.user import bp as user_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(share_bp)
    app.register_blueprint(user_bp)


def create_app(config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    _ensure_secret_key(app)
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    app.jinja_env.filters["render_md"] = render_markdown
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    register_template_context(app)
    register_csrf(app)
    _register_blueprints(app)
    _register_error_handlers(app)

    @app.cli.command("init-db")
    def init_db():
        """建表（幂等）。"""
        db.create_all()
        print("数据库已就绪：instance/notes.db")

    @app.cli.command("seed-demo")
    def seed_demo():
        """写入演示数据（幂等，可重复执行）。容器内用法：
        docker compose exec web flask --app wsgi seed-demo
        """
        from app.demo import seed_demo_data

        db.create_all()
        print(f"演示数据已就绪（本次新增 {seed_demo_data()} 条笔记）")

    return app
