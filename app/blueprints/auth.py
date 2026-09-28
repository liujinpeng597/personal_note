"""注册、登录、退出。"""
import re

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import User
from app.utils.responses import fail, ok
from app.utils.security import current_user

bp = Blueprint("auth", __name__)

USERNAME_RE = re.compile(r"^[\w\u4e00-\u9fa5]{3,20}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


def _payload():
    return request.get_json(silent=True) or request.form


def _landing_endpoint():
    return current_app.config.get("DEFAULT_LANDING_ENDPOINT", "main.home")


def _safe_next(target):
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return None


def _validate_registration(data):
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    confirm = data.get("password_confirm") or ""

    fields = {}
    if not USERNAME_RE.match(username):
        fields["username"] = "用户名需为 3–20 个中英文、数字或下划线"
    if not EMAIL_RE.match(email):
        fields["email"] = "请输入有效的邮箱地址"
    if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        fields["password"] = "密码至少 8 位，且同时包含字母和数字"
    if password != confirm:
        fields["password_confirm"] = "两次输入的密码不一致"
    return username, email, password, fields


def _validate_password(password):
    if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "密码至少 8 位，且同时包含字母和数字"
    return None


@bp.post("/auth/register")
def register():
    data = _payload()
    username, email, password, fields = _validate_registration(data)
    if fields:
        return fail("ERR_VALIDATION", "请检查表单填写", fields=fields)
    if User.query.filter_by(email=email).first():
        return fail("ERR_EMAIL_TAKEN", fields={"email": "该邮箱已被注册"})
    if User.query.filter_by(username=username).first():
        return fail("ERR_USERNAME_TAKEN", fields={"username": "该用户名已被使用"})

    user = User(username=username, email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    session["user_id"] = user.id
    return ok({"user": user.to_dict(), "redirect": url_for(_landing_endpoint())}, "注册成功", status=201)


@bp.post("/auth/login")
def login():
    data = _payload()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    user = User.query.filter_by(email=email).first()
    if user is None or not check_password_hash(user.password_hash, password):
        return fail("ERR_BAD_CREDENTIALS")

    session["user_id"] = user.id
    target = _safe_next(data.get("next")) or url_for(_landing_endpoint())
    return ok({"user": user.to_dict(), "redirect": target}, "登录成功")


@bp.post("/auth/logout")
def logout():
    session.clear()
    return ok(message="已退出登录")


@bp.post("/logout", endpoint="logout_form")
def logout_form():
    """顶栏「退出」表单提交入口（与 /auth/logout 等价）。"""
    return logout()


@bp.get("/login", endpoint="login_page")
def login_page():
    if current_user():
        return redirect(url_for(_landing_endpoint()))
    return render_template("auth/login.html", next=request.args.get("next", ""))


@bp.get("/register", endpoint="register_page")
def register_page():
    if current_user():
        return redirect(url_for(_landing_endpoint()))
    return render_template("auth/register.html")
