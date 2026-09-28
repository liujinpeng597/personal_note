from helpers import login, register


def _published_note(client, title="可分享", body="内容"):
    note_id = client.post("/notes", json={"title": title, "content_md": body}).get_json()["data"]["id"]
    client.post(f"/notes/{note_id}/publish")
    return note_id


def test_share_generate_and_revoke(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    note_id = _published_note(client)

    res = client.post(f"/notes/{note_id}/share", json={})
    assert res.get_json()["code"] == "OK"
    assert res.get_json()["data"]["has_password"] is False
    url = res.get_json()["data"]["url"]
    assert client.get(url).status_code == 200

    assert client.delete(f"/notes/{note_id}/share").get_json()["message"] == "已取消分享"
    assert client.get(url).status_code == 410


def test_draft_cannot_be_shared(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    note_id = client.post("/notes", json={"title": "草稿", "content_md": "x"}).get_json()["data"]["id"]

    res = client.post(f"/notes/{note_id}/share", json={})
    assert res.status_code == 400
    assert "草稿" in res.get_json()["message"]


def test_password_share_flow(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    note_id = _published_note(client, title="加密笔记", body="机密内容")
    url = client.post(f"/notes/{note_id}/share", json={"password": "s3cret"}).get_json()["data"]["url"]
    client.post("/auth/logout")

    locked = client.get(url)
    assert "机密内容" not in locked.get_data(as_text=True)
    assert "这篇笔记需要密码才能查看。" in locked.get_data(as_text=True)

    assert client.post(url + "/unlock", json={"password": "bad"}).status_code == 403
    assert client.post(url + "/unlock", json={"password": "s3cret"}).get_json()["code"] == "OK"
    assert "机密内容" in client.get(url).get_data(as_text=True)


def test_password_required_per_session(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    note_id = _published_note(client, title="X", body="秘密")
    url = client.post(f"/notes/{note_id}/share", json={"password": "pw12"}).get_json()["data"]["url"]
    client.post("/auth/logout")

    assert "这篇笔记需要密码才能查看。" in client.get(url).get_data(as_text=True)
    client.post(url + "/unlock", json={"password": "pw12"})
    assert "秘密" in client.get(url).get_data(as_text=True)

    with client.session_transaction() as sess:
        sess.clear()
    assert "这篇笔记需要密码才能查看。" in client.get(url).get_data(as_text=True)


def test_only_owner_can_share_or_revoke(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    note_id = _published_note(client, title="A", body="x")
    url = client.post(f"/notes/{note_id}/share", json={}).get_json()["data"]["url"]
    client.post("/auth/logout")

    register(client, "bob", "b@e.com")
    login(client, "b@e.com")
    assert client.post(f"/notes/{note_id}/share", json={}).status_code == 404
    assert client.delete(f"/notes/{note_id}/share").status_code == 404
    assert client.get(url).status_code == 200, "他人不能撤销我的分享"


def test_token_is_random_and_rotates_after_revoke(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    note_id = _published_note(client, title="A", body="x")

    first = client.post(f"/notes/{note_id}/share", json={}).get_json()["data"]["url"].rstrip("/").split("/")[-1]
    client.delete(f"/notes/{note_id}/share")
    second = client.post(f"/notes/{note_id}/share", json={}).get_json()["data"]["url"].rstrip("/").split("/")[-1]
    assert first != second
    assert len(first) >= 20


def test_unknown_and_revoked_token(client):
    assert client.get("/s/not-a-real-token").status_code == 404

    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    note_id = _published_note(client, title="X", body="y")
    url = client.post(f"/notes/{note_id}/share", json={}).get_json()["data"]["url"]
    client.delete(f"/notes/{note_id}/share")

    res = client.get(url)
    assert res.status_code == 410
    assert "已失效" in res.get_data(as_text=True)


def test_share_page_hides_private_fields(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    note_id = _published_note(client, title="公开笔记", body="正文")
    url = client.post(f"/notes/{note_id}/share", json={}).get_json()["data"]["url"]
    client.post("/auth/logout")

    html = client.get(url).get_data(as_text=True)
    assert "这是他人分享给你的笔记" in html
    assert "a@e.com" not in html
    assert "编辑" not in html and "删除" not in html
