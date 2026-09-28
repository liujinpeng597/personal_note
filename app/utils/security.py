"""登录态、所有权与 CSRF。"""
import hmac
import secrets
from functools import wraps

from flask import abort, redirect, request, session, url_for

from app.extensions import db
from app.models import Note, User
from app.utils.responses import fail

CSRF_SESSION_KEY = "_csrf_token"
WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")


def generate_csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(24)
        session[CSRF_SESSION_KEY] = token
    return token


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return db.session.get(User, uid)


def login_required(view):
    """页面视图：未登录跳转登录页并带回跳地址。"""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect(url_for("auth.login_page", next=request.full_path.rstrip("?")))
        return view(*args, **kwargs)

    return wrapper


def api_login_required(view):
    """接口视图：未登录返回 401 ERR_UNAUTHORIZED。"""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user():
            return fail("ERR_UNAUTHORIZED", status=401)
        return view(*args, **kwargs)

    return wrapper


def owned_note_or_404(note_id):
    """取当前用户的笔记；不存在或不属于当前用户一律 404（不暴露存在性）。"""
    note = db.session.get(Note, note_id)
    if note is None or note.user_id != session.get("user_id"):
        abort(404)
    return note


def register_csrf(app):
    @app.before_request
    def _check_csrf():
        if not app.config.get("CSRF_ENABLED", True):
            return None
        if request.method not in WRITE_METHODS:
            return None
        expected = session.get(CSRF_SESSION_KEY)
        provided = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
        if not expected or not provided or not hmac.compare_digest(str(expected), str(provided)):
            return fail("ERR_CSRF", status=403)
        return None


def register_template_context(app):
    app.jinja_env.globals["csrf_token"] = generate_csrf_token

    @app.context_processor
    def _inject_user():
        return {"current_user": current_user()}
