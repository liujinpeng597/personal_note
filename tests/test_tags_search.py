import re

from helpers import login, register


def _titles_in(html):
    """精确提取列表页的笔记标题（详情链接文本）。"""
    return set(re.findall(r'<a href="/notes/\d+">([^<]+)</a>', html))


def test_tags_saved_and_deduplicated(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    note_id = client.post("/notes", json={
        "title": "带标签", "content_md": "正文", "tags": "读书, 效率，读书",
    }).get_json()["data"]["id"]

    html = client.get(f"/notes/{note_id}").get_data(as_text=True)
    assert "读书" in html and "效率" in html
    assert html.count('class="chip"') == 2, "重复标签只保留一个"


def test_tag_limits_return_chinese_error(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")

    too_many = client.post("/notes", json={"title": "x", "content_md": "y", "tags": "a,b,c,d,e,f"})
    assert too_many.get_json()["code"] == "ERR_VALIDATION"
    assert "最多" in too_many.get_json()["data"]["fields"]["tags"]

    too_long = client.post("/notes", json={"title": "x", "content_md": "y", "tags": "一" * 21})
    assert too_long.get_json()["code"] == "ERR_VALIDATION"
    assert "20" in too_long.get_json()["data"]["fields"]["tags"]


def test_search_matches_title_body_and_tag(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")

    ids = []
    ids.append(client.post("/notes", json={"title": "读书笔记", "content_md": "正文", "tags": "阅读"}).get_json()["data"]["id"])
    ids.append(client.post("/notes", json={"title": "别的", "content_md": "里面有 读书 两个字"}).get_json()["data"]["id"])
    ids.append(client.post("/notes", json={"title": "第三篇", "content_md": "无关", "tags": "读书"}).get_json()["data"]["id"])
    for note_id in ids:
        client.post(f"/notes/{note_id}/publish")

    html = client.get("/notes?q=读书").get_data(as_text=True)
    for note_id in ids:
        assert f'<a href="/notes/{note_id}">' in html


def test_search_isolated_to_owner_and_empty_copy(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    client.post("/notes", json={"title": "秘密", "content_md": "只有我有"})
    client.post("/auth/logout")

    register(client, "bob", "b@e.com")
    login(client, "b@e.com")
    html = client.get("/notes?q=秘密").get_data(as_text=True)
    assert not _titles_in(html), "不能搜到别人的笔记"
    assert '没有找到包含「秘密」的笔记。' in html


def test_tag_filter_and_empty_copy(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    client.post("/notes", json={"title": "甲", "content_md": "x", "tags": "工作"})
    client.post("/notes", json={"title": "乙", "content_md": "x", "tags": "生活"})

    work = client.get("/notes?tag=工作").get_data(as_text=True)
    assert _titles_in(work) == {"甲"}
    assert "标签「不存在」下还没有笔记。" in client.get("/notes?tag=不存在").get_data(as_text=True)


def test_search_and_tag_combine(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    client.post("/notes", json={"title": "会议记录", "content_md": "x", "tags": "工作"})
    client.post("/notes", json={"title": "购物清单", "content_md": "x", "tags": "生活"})

    html = client.get("/notes?q=会议&tag=工作").get_data(as_text=True)
    assert "会议记录" in html and "购物清单" not in html
