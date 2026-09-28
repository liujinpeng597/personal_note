from app.extensions import db
from app.models import Comment, Favorite, Note, Share, Tag, User


def test_cascade_delete_and_to_dict_whitelist(app):
    with app.app_context():
        alice = User(username="alice", email="a@e.com", password_hash="scrypt:x")
        bob = User(username="bob", email="b@e.com", password_hash="scrypt:y")
        db.session.add_all([alice, bob])
        db.session.commit()

        note = Note(user_id=alice.id, title="标题", content_md="正文")
        note.tags.append(Tag(name="读书"))
        db.session.add(note)
        db.session.commit()

        db.session.add_all([
            Favorite(user_id=bob.id, note_id=note.id),
            Comment(note_id=note.id, user_id=bob.id, content="第一条"),
            Share(note_id=note.id, token="tok-1234567890"),
        ])
        db.session.commit()

        alice_id = alice.id
        assert "password_hash" not in alice.to_dict()
        assert "email" not in alice.to_dict()
        assert alice.to_dict()["username"] == "alice"
        assert note.excerpt == "正文"
        assert note.is_published is False

        db.session.delete(note)
        db.session.commit()

        assert Favorite.query.count() == 0
        assert Comment.query.count() == 0
        assert Share.query.count() == 0
        assert Tag.query.count() == 1, "标签本身不应被删除"
        assert db.session.get(User, alice_id) is not None


def test_status_check_constraint(app):
    with app.app_context():
        user = User(username="carol", email="c@e.com", password_hash="scrypt:z")
        db.session.add(user)
        db.session.commit()
        db.session.add(Note(user_id=user.id, title="x", content_md="y", status="weird"))
        try:
            db.session.commit()
            raised = False
        except Exception:
            db.session.rollback()
            raised = True
        assert raised, "status 只允许 draft / published"
