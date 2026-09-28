from helpers import login, register


def _publish_note(client, title="可收藏"):
    note_id = client.post("/notes", json={"title": title, "content_md": "正文"}).get_json()["data"]["id"]
    client.post(f"/notes/{note_id}/publish")
    return note_id


def test_favorite_toggle_is_idempotent(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    note_id = _publish_note(client)

    first = client.post(f"/notes/{note_id}/favorite").get_json()["data"]
    assert first == {"favorited": True, "count": 1}

    second = client.post(f"/notes/{note_id}/favorite").get_json()["data"]
    assert second == {"favorited": False, "count": 0}


def test_favorite_count_seen_by_other_user(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    note_id = _publish_note(client)
    client.post(f"/notes/{note_id}/favorite")
    client.post("/auth/logout")

    register(client, "bob", "b@e.com")
    login(client, "b@e.com")
    data = client.post(f"/notes/{note_id}/favorite").get_json()["data"]
    assert data == {"favorited": True, "count": 2}


def test_favorite_requires_login_and_published_note(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    draft_id = client.post("/notes", json={"title": "草稿", "content_md": "x"}).get_json()["data"]["id"]
    client.post("/auth/logout")

    assert client.post(f"/notes/{draft_id}/favorite").status_code == 401

    register(client, "bob", "b@e.com")
    login(client, "b@e.com")
    assert client.post(f"/notes/{draft_id}/favorite").status_code == 404


def test_detail_page_renders_favorite_state(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    note_id = _publish_note(client)
    html = client.get(f"/notes/{note_id}").get_data(as_text=True)
    assert 'aria-pressed="false"' in html

    client.post(f"/notes/{note_id}/favorite")
    html = client.get(f"/notes/{note_id}").get_data(as_text=True)
    assert 'aria-pressed="true"' in html
    assert '<span class="favorite-btn__count">1</span>' in html
