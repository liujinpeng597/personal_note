"""个人主页与设置。"""
import re

from flask import Blueprint, abort, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import Favorite, Note, User
from app.utils.responses import fail, ok
from app.utils.security import api_login_required, current_user, login_required

bp = Blueprint("user", __name__)

PER_PAGE = 10
USERNAME_RE = re.compile(r"^[\w\u4e00-\u9fa5]{3,20}$")


def _payload():
    return request.get_json(silent=True) or request.form


@bp.get("/u/<username>", endpoint="profile")
def profile(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)

    tab = request.args.get("tab", "notes")
    if tab not in ("notes", "favorites"):
        tab = "notes"
    page = request.args.get("page", 1, type=int) or 1

    published_notes = db.paginate(
        db.select(Note).where(Note.user_id == user.id, Note.status == "published")
        .order_by(Note.published_at.desc(), Note.updated_at.desc()),
        page=page, per_page=PER_PAGE, error_out=False,
    )
    favorite_notes = db.paginate(
        db.select(Note).join(Favorite, Favorite.note_id == Note.id)
        .where(Favorite.user_id == user.id, Note.status == "published")
        .order_by(Favorite.created_at.desc()),
        page=page, per_page=PER_PAGE, error_out=False,
    )

    viewer = current_user()
    return render_template(
        "user/profile.html",
        user=user,
        tab=tab,
        notes=published_notes.items,
        notes_page=published_notes,
        favorites=favorite_notes.items,
        favorites_page=favorite_notes,
        note_count=published_notes.total,
        favorite_count=favorite_notes.total,
        is_self=bool(viewer and viewer.id == user.id),
    )


@bp.get("/settings", endpoint="settings")
@login_required
def settings():
    return render_template("user/settings.html")


@bp.post("/settings/profile")
@api_login_required
def update_profile():
    data = _payload()
    user = current_user()
    username = (data.get("username") or "").strip()
    bio = (data.get("bio") or "").strip()
    avatar_url = (data.get("avatar_url") or "").strip()

    if username and username != user.username:
        if not USERNAME_RE.match(username):
            return fail("ERR_VALIDATION", "用户名需为 3–20 个中英文、数字或下划线",
                        fields={"username": "用户名需为 3–20 个中英文、数字或下划线"})
        taken = User.query.filter(User.username == username, User.id != user.id).first()
        if taken is not None:
            return fail("ERR_USERNAME_TAKEN", fields={"username": "该用户名已被使用"})
        user.username = username

    if len(bio) > 200:
        return fail("ERR_VALIDATION", "请检查填写内容", fields={"bio": "简介不能超过 200 字"})

    if avatar_url and not (avatar_url.startswith("http://") or avatar_url.startswith("https://")):
        message = "头像地址必须以 http:// 或 https:// 开头"
        return fail("ERR_VALIDATION", message, fields={"avatar_url": message})

    user.bio = bio
    user.avatar_url = avatar_url or None
    db.session.commit()
    return ok({"user": user.to_dict()}, "资料已更新")


@bp.post("/settings/password")
@api_login_required
def change_password():
    user = current_user()
    data = _payload()
    old_password = data.get("old_password") or ""
    new_password = data.get("new_password") or ""
    confirm = data.get("new_password_confirm") or ""

    if not check_password_hash(user.password_hash, old_password):
        return fail("ERR_BAD_CREDENTIALS", "原密码不正确")

    fields = {}
    if len(new_password) < 8 or not re.search(r"[A-Za-z]", new_password) or not re.search(r"\d", new_password):
        fields["new_password"] = "密码至少 8 位，且同时包含字母和数字"
    if new_password != confirm:
        fields["new_password_confirm"] = "两次输入的密码不一致"
    if fields:
        return fail("ERR_VALIDATION", "请检查填写内容", fields=fields)

    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    session["user_id"] = user.id
    return ok(message="密码已修改")
