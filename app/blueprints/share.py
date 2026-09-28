"""分享（生成 / 撤销 / 访问 / 密码解锁）与评论。"""
import secrets
from datetime import datetime

from flask import Blueprint, abort, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import Comment, Favorite, Note, Share
from app.utils.responses import fail, ok
from app.utils.security import api_login_required, current_user, owned_note_or_404

bp = Blueprint("share", __name__)


def _payload():
    return request.get_json(silent=True) or request.form


def _active_share_or_abort(token):
    share = Share.query.filter_by(token=token).first()
    if share is None:
        abort(404)
    if share.revoked_at is not None:
        abort(410)
    return share


# --------------------------------------------------------------------------- 作者侧


@bp.post("/notes/<int:note_id>/share")
@api_login_required
def create_share(note_id):
    note = owned_note_or_404(note_id)
    if note.status != "published":
        return fail("ERR_VALIDATION", "草稿不能分享，请先发布")

    password = (_payload().get("password") or "").strip()
    if password and not (4 <= len(password) <= 64):
        fields = {"password": "分享密码长度需为 4–64 位"}
        return fail("ERR_VALIDATION", "请检查填写内容", fields=fields)

    share = Share.query.filter_by(note_id=note.id).first()
    if share is None:
        share = Share(note_id=note.id, token=secrets.token_urlsafe(16))
        db.session.add(share)
    elif share.revoked_at is not None:
        share.token = secrets.token_urlsafe(16)

    share.revoked_at = None
    share.password_hash = generate_password_hash(password) if password else None
    db.session.commit()
    return ok(
        {"url": url_for("share.view", token=share.token), "has_password": bool(password)},
        "已生成分享链接",
    )


@bp.delete("/notes/<int:note_id>/share")
@api_login_required
def revoke_share(note_id):
    note = owned_note_or_404(note_id)
    share = Share.query.filter_by(note_id=note.id).first()
    if share is not None and share.revoked_at is None:
        share.revoked_at = datetime.now()
        db.session.commit()
    return ok(message="已取消分享")


# --------------------------------------------------------------------------- 访客侧


@bp.get("/s/<token>", endpoint="view")
def view(token):
    share = _active_share_or_abort(token)
    if share.password_hash and session.get(f"share_ok:{token}") is not True:
        return render_template("share/password.html", token=token)

    note = share.note
    user = current_user()
    favorite_row = None
    if user is not None:
        favorite_row = Favorite.query.filter_by(user_id=user.id, note_id=note.id).first()
    comments = Comment.query.filter_by(note_id=note.id).order_by(Comment.created_at.asc()).all()
    return render_template(
        "share/view.html",
        note=note,
        comments=comments,
        favorited=favorite_row is not None,
        favorite_count=Favorite.query.filter_by(note_id=note.id).count(),
    )


@bp.post("/s/<token>/unlock")
def unlock(token):
    share = _active_share_or_abort(token)
    password = _payload().get("password") or ""
    if not share.password_hash or check_password_hash(share.password_hash, password):
        session[f"share_ok:{token}"] = True
        return ok({"redirect": url_for("share.view", token=token)}, "密码正确，可以阅读了")
    return fail("ERR_SHARE_PASSWORD")


# --------------------------------------------------------------------------- 评论


@bp.post("/notes/<int:note_id>/comments")
@api_login_required
def add_comment(note_id):
    note = db.session.get(Note, note_id)
    if note is None or note.status != "published":
        return fail("ERR_NOT_FOUND", status=404)

    content = (_payload().get("content") or "").strip()
    if not content:
        return fail("ERR_VALIDATION", "评论内容不能为空", fields={"content": "评论内容不能为空"})
    if len(content) > 500:
        return fail("ERR_VALIDATION", "评论不能超过 500 字", fields={"content": "评论不能超过 500 字"})

    comment = Comment(note_id=note.id, user_id=session["user_id"], content=content)
    db.session.add(comment)
    db.session.commit()
    return ok({"comment": comment.to_dict()}, "已发表评论", status=201)


@bp.delete("/comments/<int:comment_id>")
@api_login_required
def delete_comment(comment_id):
    comment = db.session.get(Comment, comment_id)
    if comment is None or comment.user_id != session.get("user_id"):
        abort(404)
    db.session.delete(comment)
    db.session.commit()
    return ok(message="已删除评论")
