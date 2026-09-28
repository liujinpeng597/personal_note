"""演示数据：`python run.py --demo`。

幂等：重复执行不会重复插入。
"""
from app.extensions import db
from app.models import Comment, Favorite, Note, Share, Tag, User
from werkzeug.security import generate_password_hash

DEMO_USERNAME = "demo"
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Demo1234"

DEMO_NOTES = [
    {
        "title": "清晨的第一行字",
        "content_md": (
            "把桌子擦干净，泡一杯咖啡，然后写下今天的第一句话。\n\n"
            "- 不做计划，只记录\n"
            "- 写满一页就停下\n"
            "- 不删改，先让它存在\n\n"
            "> 写作最难的部分，是坐下来。\n"
        ),
        "tags": ["随笔", "习惯"],
        "published": True,
    },
    {
        "title": "Markdown 速查（自用）",
        "content_md": (
            "## 常用语法\n\n"
            "| 语法 | 效果 |\n| --- | --- |\n| `# 标题` | 一级标题 |\n| `**粗体**` | **粗体** |\n"
            "| `- 项目` | 无序列表 |\n\n"
            "### 代码块\n\n```python\nfor i in range(3):\n    print(i)\n```\n\n"
            "### 链接与图片\n\n[本站关于页](/about)\n"
        ),
        "tags": ["Markdown", "工具"],
        "published": True,
    },
    {
        "title": "周末读到的三段话",
        "content_md": (
            "1. 人需要一段不被打扰的时间。\n"
            "2. 记录比记忆可靠。\n"
            "3. 把想法写下来，它才真正属于你。\n\n"
            "—— 记于周六下午\n"
        ),
        "tags": ["读书"],
        "published": True,
    },
    {
        "title": "还没写完的草稿",
        "content_md": "（先占个位置，等想清楚了再写。）\n",
        "tags": [],
        "published": False,
    },
]


def seed_demo_data():
    """返回本次新增的笔记数量。"""
    user = User.query.filter_by(username=DEMO_USERNAME).first()
    if user is None:
        user = User(
            username=DEMO_USERNAME,
            email=DEMO_EMAIL,
            password_hash=generate_password_hash(DEMO_PASSWORD),
            bio="这是演示账号，用来看看个人笔记长什么样。",
        )
        db.session.add(user)
        db.session.commit()

    created = 0
    first_published = None
    for item in DEMO_NOTES:
        note = Note.query.filter_by(user_id=user.id, title=item["title"]).first()
        if note is None:
            note = Note(user_id=user.id, title=item["title"], content_md=item["content_md"])
            db.session.add(note)
            db.session.flush()
            created += 1

        note.content_md = item["content_md"]
        tags = []
        for name in item["tags"]:
            tag = Tag.query.filter(db.func.lower(Tag.name) == name.lower()).first()
            if tag is None:
                tag = Tag(name=name)
                db.session.add(tag)
            tags.append(tag)
        note.tags = tags

        if item["published"]:
            note.status = "published"
            if note.published_at is None:
                from datetime import datetime
                note.published_at = datetime.now()
            if first_published is None:
                first_published = note
        db.session.commit()

    if first_published is not None:
        if not Comment.query.filter_by(note_id=first_published.id).first():
            db.session.add(Comment(note_id=first_published.id, user_id=user.id,
                                   content="给自己留个批注：下次试试写得更短一点。"))
            db.session.add(Comment(note_id=first_published.id, user_id=user.id,
                                   content="第二遍读，还是喜欢最后那句。"))
        if Share.query.filter_by(note_id=first_published.id).first() is None:
            db.session.add(Share(note_id=first_published.id, token="demo-share-token-0001"))
        favorite_note = Note.query.filter_by(user_id=user.id, title=DEMO_NOTES[1]["title"]).first()
        if favorite_note is not None:
            exists = Favorite.query.filter_by(user_id=user.id, note_id=favorite_note.id).first()
            if exists is None:
                db.session.add(Favorite(user_id=user.id, note_id=favorite_note.id))
        db.session.commit()

    return created
