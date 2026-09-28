"""笔记：写作、草稿、发布、列表、详情、收藏、上传。"""
from flask import Blueprint, current_app, render_template, request, session, url_for

from app.extensions import db
from app.models import Comment, Favorite, Note, Share, Tag
from app.utils.responses import fail, ok
from app.utils.security import api_login_required, login_required, owned_note_or_404
from app.utils.tags import parse_tags, sync_note_tags, tags_to_text
from app.utils.uploads import save_image

bp = Blueprint("notes", __name__)

PER_PAGE = 10
TABS = (("all", "全部"), ("published", "已发布"), ("draft", "草稿"))


def _payload():
    return request.get_json(silent=True) or request.form


def _validate(data, require_body):
    title = (data.get("title") or "").strip()
    content = (data.get("content_md") or "")
    tag_names, tag_fields = parse_tags(data.get("tags") or "")

    fields = {}
    if not title:
        fields["title"] = "标题不能为空"
    elif len(title) > 120:
        fields["title"] = "标题不能超过 120 字"
    if require_body and not content.strip():
        fields["content_md"] = "发布前请先写点正文"
    fields.update(tag_fields)
    return title, content, tag_names, fields


# --------------------------------------------------------------------------- 接口


@bp.post("/notes")
@api_login_required
def create():
    data = _payload()
    title, content, tag_names, fields = _validate(data, require_body=False)
    if fields:
        return fail("ERR_VALIDATION", "请检查填写内容", fields=fields)

    note = Note(user_id=session["user_id"], title=title, content_md=content, status="draft")
    db.session.add(note)
    db.session.flush()
    sync_note_tags(note, tag_names)
    db.session.commit()
    return ok({"id": note.id, "url": url_for("notes.detail", note_id=note.id)}, "已保存草稿", status=201)


@bp.put("/notes/<int:note_id>")
@api_login_required
def update(note_id):
    note = owned_note_or_404(note_id)
    data = _payload()
    title, content, tag_names, fields = _validate(data, require_body=False)
    if fields:
        return fail("ERR_VALIDATION", "请检查填写内容", fields=fields)

    note.title = title
    note.content_md = content
    sync_note_tags(note, tag_names)
    db.session.commit()
    return ok({"id": note.id, "updated_at": note.to_dict()["updated_at"]}, "已保存")


@bp.post("/notes/<int:note_id>/publish")
@api_login_required
def publish(note_id):
    note = owned_note_or_404(note_id)
    data = _payload()
    title, content, tag_names, fields = _validate(
        {"title": data.get("title", note.title), "content_md": data.get("content_md", note.content_md),
         "tags": data.get("tags", tags_to_text(note))},
        require_body=True,
    )
    if fields:
        return fail("ERR_VALIDATION", "请检查填写内容", fields=fields)

    note.title = title
    note.content_md = content
    sync_note_tags(note, tag_names)
    note.status = "published"
    if note.published_at is None:
        from datetime import datetime
        note.published_at = datetime.now()
    db.session.commit()
    return ok({"id": note.id, "url": url_for("notes.detail", note_id=note.id)}, "已发布")


@bp.delete("/notes/<int:note_id>")
@api_login_required
def delete(note_id):
    note = owned_note_or_404(note_id)
    db.session.delete(note)
    db.session.commit()
    return ok(message="已删除")


@bp.post("/notes/<int:note_id>/favorite")
@api_login_required
def favorite(note_id):
    note = db.session.get(Note, note_id)
    if note is None or note.status != "published":
        return fail("ERR_NOT_FOUND", status=404)

    existing = Favorite.query.filter_by(user_id=session["user_id"], note_id=note_id).first()
    if existing:
        db.session.delete(existing)
        favorited = False
    else:
        db.session.add(Favorite(user_id=session["user_id"], note_id=note_id))
        favorited = True
    db.session.commit()
    count = Favorite.query.filter_by(note_id=note_id).count()
    return ok({"favorited": favorited, "count": count}, "已收藏" if favorited else "已取消收藏")


@bp.post("/api/upload")
@api_login_required
def upload():
    file_storage = request.files.get("file")
    if file_storage is None or not file_storage.filename:
        return fail("ERR_VALIDATION", "请选择要上传的图片", fields={"file": "请选择要上传的图片"})

    url, error_code = save_image(file_storage, current_app.config["UPLOAD_FOLDER"])
    if error_code:
        return fail(error_code)
    return ok({"url": url}, "图片已上传", status=201)


# --------------------------------------------------------------------------- 页面


@bp.get("/notes", endpoint="list")
@login_required
def list_notes():
    tab = request.args.get("tab", "all")
    if tab not in dict(TABS):
        tab = "all"
    keyword = (request.args.get("q") or "").strip()
    tag_name = (request.args.get("tag") or "").strip()
    page = request.args.get("page", 1, type=int) or 1

    stmt = db.select(Note).where(Note.user_id == session["user_id"])
    if tab == "draft":
        stmt = stmt.where(Note.status == "draft")
    elif tab == "published":
        stmt = stmt.where(Note.status == "published")
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(db.or_(
            Note.title.ilike(like),
            Note.content_md.ilike(like),
            Note.tags.any(Tag.name.ilike(like)),
        ))
    if tag_name:
        stmt = stmt.where(Note.tags.any(Tag.name == tag_name))
    stmt = stmt.order_by(Note.updated_at.desc())

    pagination = db.paginate(stmt, page=page, per_page=PER_PAGE, error_out=False)
    return render_template(
        "notes/list.html",
        notes=pagination.items,
        pagination=pagination,
        tab=tab,
        tabs=TABS,
        q=keyword,
        tag=tag_name,
        total_for_tab=pagination.total,
    )


@bp.get("/notes/new", endpoint="editor_new")
@login_required
def editor_new():
    return render_template("notes/editor.html", note=None, tags_text="")


@bp.get("/notes/<int:note_id>", endpoint="detail")
@login_required
def detail(note_id):
    note = owned_note_or_404(note_id)
    favorite_row = Favorite.query.filter_by(user_id=session["user_id"], note_id=note.id).first()
    share = Share.query.filter_by(note_id=note.id).first()
    comments = Comment.query.filter_by(note_id=note.id).order_by(Comment.created_at.asc()).all()
    return render_template(
        "notes/detail.html",
        note=note,
        favorited=favorite_row is not None,
        favorite_count=Favorite.query.filter_by(note_id=note.id).count(),
        share=share,
        comments=comments,
        can_comment=note.is_published,
    )


@bp.get("/notes/<int:note_id>/edit", endpoint="editor_edit")
@login_required
def editor_edit(note_id):
    note = owned_note_or_404(note_id)
    return render_template("notes/editor.html", note=note, tags_text=tags_to_text(note))
