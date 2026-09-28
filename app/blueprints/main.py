from flask import Blueprint, render_template, request

from app.utils.markdown_render import render_markdown
from app.utils.responses import ok
from app.utils.security import api_login_required

bp = Blueprint("main", __name__)


@bp.post("/api/preview")
@api_login_required
def preview():
    data = request.get_json(silent=True) or request.form
    return ok({"html": render_markdown(data.get("content_md") or "")})


@bp.get("/")
def home():
    features = [
        {"icon": "pen", "title": "写笔记", "text": "干净的编辑器，专注写下当下的想法。"},
        {"icon": "markdown", "title": "Markdown 排版", "text": "标题、列表、代码块与表格，排版由服务端渲染。"},
        {"icon": "share", "title": "一键分享", "text": "生成一条链接，也可以加一道密码。"},
        {"icon": "heart", "title": "评论与收藏", "text": "朋友可以留言，喜欢的笔记点一下那颗心。"},
    ]
    return render_template("main/home.html", features=features)


@bp.get("/about")
def about():
    return render_template("main/about.html")
