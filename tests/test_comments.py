from helpers import login, register


def _published_note(client, title="可评论"):
    note_id = client.post("/notes", json={"title": title, "content_md": "正文"}).get_json()["data"]["id"]
    client.post(f"/notes/{note_id}/publish")
    return note_id


def test_comment_crud_and_permissions(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    note_id = _published_note(client)

    created = client.post(f"/notes/{note_id}/comments", json={"content": "第一条\n换行"})
    assert created.status_code == 201
    comment_id = created.get_json()["data"]["comment"]["id"]
    assert "第一条" in client.get(f"/notes/{note_id}").get_data(as_text=True)

    client.post("/auth/logout")
    assert client.post(f"/notes/{note_id}/comments", json={"content": "游客"}).status_code == 401
    assert client.delete(f"/comments/{comment_id}").status_code == 401

    register(client, "bob", "b@e.com")
    login(client, "b@e.com")
    assert client.delete(f"/comments/{comment_id}").status_code == 404

    login(client, "a@e.com")
    assert client.delete(f"/comments/{comment_id}").get_json()["code"] == "OK"
    assert "第一条" not in client.get(f"/notes/{note_id}").get_data(as_text=True)


def test_comment_validation_and_empty_copy(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    note_id = _published_note(client)

    assert "还没有评论，来说点什么。" in client.get(f"/notes/{note_id}").get_data(as_text=True)

    blank = client.post(f"/notes/{note_id}/comments", json={"content": "   "})
    assert blank.status_code == 400
    assert blank.get_json()["data"]["fields"]["content"]

    too_long = client.post(f"/notes/{note_id}/comments", json={"content": "字" * 501})
    assert too_long.status_code == 400


def test_draft_cannot_be_commented(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    draft_id = client.post("/notes", json={"title": "草稿", "content_md": "x"}).get_json()["data"]["id"]
    assert client.post(f"/notes/{draft_id}/comments", json={"content": "hi"}).status_code == 404


def test_guest_sees_login_prompt_on_share_page(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    note_id = _published_note(client, title="分享笔记")
    url = client.post(f"/notes/{note_id}/share", json={}).get_json()["data"]["url"]
    client.post("/auth/logout")

    html = client.get(url).get_data(as_text=True)
    assert "登录后可以评论" in html
    assert 'id="comment-form"' not in html


def test_logged_in_user_sees_comment_form_on_detail(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    note_id = _published_note(client)
    html = client.get(f"/notes/{note_id}").get_data(as_text=True)
    assert 'id="comment-form"' in html, "登录用户应看到评论输入框"
    assert "登录后可以评论" not in html


def test_logged_in_visitor_sees_comment_form_on_share_page(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    note_id = _published_note(client, title="分享笔记")
    url = client.post(f"/notes/{note_id}/share", json={}).get_json()["data"]["url"]
    client.post("/auth/logout")

    register(client, "bob", "b@e.com")
    login(client, "b@e.com")
    html = client.get(url).get_data(as_text=True)
    assert 'id="comment-form"' in html
    assert "登录后可以评论" not in html


def test_own_comment_shows_delete_button(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    note_id = _published_note(client)
    comment_id = client.post(f"/notes/{note_id}/comments", json={"content": "我的评论"}).get_json()["data"]["comment"]["id"]
    html = client.get(f"/notes/{note_id}").get_data(as_text=True)
    assert f'data-comment-delete="{comment_id}"' in html
