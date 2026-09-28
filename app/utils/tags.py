"""标签解析与写库。"""
import re

from app.extensions import db
from app.models import Tag

MAX_TAGS = 5
MAX_TAG_LEN = 20
_SPLIT_RE = re.compile(r"[,，]")


def parse_tags(raw):
    """逗号（中英文）切分 → 去空白 → 去重（大小写不敏感）→ 校验数量与长度。

    返回 (标签名列表, 字段错误字典)。
    """
    if not raw:
        return [], {}

    names = []
    seen = set()
    for part in _SPLIT_RE.split(raw):
        name = part.strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(name)

    if len(names) > MAX_TAGS:
        return names, {"tags": f"最多只能添加 {MAX_TAGS} 个标签"}
    for name in names:
        if len(name) > MAX_TAG_LEN:
            return names, {"tags": f"单个标签不能超过 {MAX_TAG_LEN} 字"}
    return names, {}


def sync_note_tags(note, names):
    """按名字取或建标签，并替换笔记的标签集合。"""
    tags = []
    for name in names:
        tag = Tag.query.filter(db.func.lower(Tag.name) == name.lower()).first()
        if tag is None:
            tag = Tag(name=name)
            db.session.add(tag)
        tags.append(tag)
    note.tags = tags


def tags_to_text(note):
    return ", ".join(tag.name for tag in note.tags)
