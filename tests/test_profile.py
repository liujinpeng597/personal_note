from helpers import login, register


def test_profile_hides_drafts_and_private_fields(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    published = client.post("/notes", json={"title": "已发布标题", "content_md": "x"}).get_json()["data"]["id"]
    client.post(f"/notes/{published}/publish")
    client.post("/notes", json={"title": "草稿标题", "content_md": "x"})
    client.post("/auth/logout")

    register(client, "bob", "b@e.com")
    login(client, "b@e.com")
    html = client.get("/u/alice").get_data(as_text=True)
    assert "已发布标题" in html
    assert "草稿标题" not in html
    assert "a@e.com" not in html


def test_profile_empty_copy_for_self_and_other(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    assert "你还没有收藏任何笔记。看到喜欢的，点一下那颗心。" in client.get("/u/alice?tab=favorites").get_data(as_text=True)
    assert "你还没有发布任何笔记。" in client.get("/u/alice").get_data(as_text=True)
    client.post("/auth/logout")

    register(client, "bob", "b@e.com")
    login(client, "b@e.com")
    other = client.get("/u/alice?tab=favorites").get_data(as_text=True)
    assert "alice 还没有收藏任何笔记。" in other


def test_profile_favorites_tab_lists_favorited_note(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    note_id = client.post("/notes", json={"title": "被收藏的笔记", "content_md": "x"}).get_json()["data"]["id"]
    client.post(f"/notes/{note_id}/publish")
    client.post(f"/notes/{note_id}/favorite")

    html = client.get("/u/alice?tab=favorites").get_data(as_text=True)
    assert "被收藏的笔记" in html


def test_unknown_user_is_404(client):
    assert client.get("/u/nobody").status_code == 404


def test_settings_page_requires_login(client):
    res = client.get("/settings")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]
