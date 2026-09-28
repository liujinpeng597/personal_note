"""数据模型：users / notes / tags / note_tags / favorites / comments / shares。"""
import re
from datetime import datetime

from sqlalchemy import CheckConstraint, UniqueConstraint

from app.extensions import db

note_tags = db.Table(
    "note_tags",
    db.Column("note_id", db.Integer, db.ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

_CODE_BLOCK_RE = re.compile(r"```.*?```", re.S)
_INLINE_CODE_RE = re.compile(r"`([^`]*)`")
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_BLOCK_MARKER_RE = re.compile(r"^\s{0,3}(#{1,6}\s*|[-*+]\s+|\d+\.\s+|>\s*)", re.M)


def _plain_text(markdown_text, limit=80):
    """把 Markdown 摘成一行纯文本，用于列表卡片摘要。"""
    text = markdown_text or ""
    text = _CODE_BLOCK_RE.sub(" ", text)
    text = _IMAGE_RE.sub(" ", text)
    text = _LINK_RE.sub(r"\1", text)
    text = _INLINE_CODE_RE.sub(r"\1", text)
    text = _BLOCK_MARKER_RE.sub("", text)
    text = re.sub(r"[-=]{2,}", " ", text)
    text = text.replace("|", " ").replace("*", "").replace("_", "").replace("~", "")
    text = text.replace(">", " ").replace("#", " ").replace("\\", "")
    text = " ".join(text.split())
    return text[:limit]


def _now():
    return datetime.now()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar_url = db.Column(db.String(255))
    bio = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, nullable=False, default=_now)

    notes = db.relationship("Note", back_populates="author", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "created_at": self.created_at.strftime("%Y-%m-%d") if self.created_at else None,
        }


class Note(db.Model):
    __tablename__ = "notes"
    __table_args__ = (CheckConstraint("status IN ('draft', 'published')", name="ck_notes_status"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    content_md = db.Column(db.Text, nullable=False, default="")
    status = db.Column(db.String(10), nullable=False, default="draft", index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=_now, onupdate=_now)
    published_at = db.Column(db.DateTime)

    author = db.relationship("User", back_populates="notes")
    tags = db.relationship("Tag", secondary=note_tags, backref="notes")
    comments = db.relationship("Comment", back_populates="note", cascade="all, delete-orphan")
    favorites = db.relationship("Favorite", back_populates="note", cascade="all, delete-orphan")
    shares = db.relationship("Share", back_populates="note", cascade="all, delete-orphan")

    @property
    def is_published(self):
        return self.status == "published"

    @property
    def excerpt(self):
        return _plain_text(self.content_md)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content_md": self.content_md,
            "status": self.status,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M") if self.updated_at else None,
            "published_at": self.published_at.strftime("%Y-%m-%d %H:%M") if self.published_at else None,
            "tags": [tag.name for tag in self.tags],
            "author": self.author.username if self.author else None,
        }


class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)


class Favorite(db.Model):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "note_id", name="uq_favorites_user_note"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    note_id = db.Column(db.Integer, db.ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=_now)

    note = db.relationship("Note", back_populates="favorites")


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=_now)

    note = db.relationship("Note", back_populates="comments")
    author = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else None,
            "user": self.author.username if self.author else None,
            "user_id": self.user_id,
        }


class Share(db.Model):
    __tablename__ = "shares"

    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, unique=True)
    token = db.Column(db.String(32), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, default=_now)
    revoked_at = db.Column(db.DateTime)

    note = db.relationship("Note", back_populates="shares")

    @property
    def is_active(self):
        return self.revoked_at is None
