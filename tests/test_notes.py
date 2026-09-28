import re
from urllib.parse import unquote

from helpers import login, register


def _titles_in(html):
    """从列表页 HTML 中精确提取笔记标题（笔记卡片里的详情链接文本）。"""
    return set(re.findall(r'<a href="/notes/\d+">([^<]+)</a>', html))


def test_create_draft_then_publish(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")

    res = client.post("/notes", json={"title": "第一篇", "content_md": "# 你好"})
    assert res.status_code == 201
    assert res.get_json()["message"] == "已保存草稿"
    note_id = res.get_json()["data"]["id"]

    publish = client.post(f"/notes/{note_id}/publish")
    assert publish.get_json()["message"] == "已发布"
    assert client.get(f"/notes/{note_id}").status_code == 200


def test_validation_and_publish_requires_body(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")

    blank_title = client.post("/notes", json={"title": "   ", "content_md": ""})
    assert blank_title.status_code == 400
    assert blank_title.get_json()["code"] == "ERR_VALIDATION"
    assert "标题" in blank_title.get_json()["data"]["fields"]["title"]

    draft = client.post("/notes", json={"title": "只有标题的草稿", "content_md": ""})
    note_id = draft.get_json()["data"]["id"]
    publish = client.post(f"/notes/{note_id}/publish")
    assert publish.status_code == 400
    assert "正文" in publish.get_json()["data"]["fields"]["content_md"]


def test_update_and_delete_note(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    note_id = client.post("/notes", json={"title": "标题", "content_md": "正文"}).get_json()["data"]["id"]

    updated = client.put(f"/notes/{note_id}", json={"title": "新标题", "content_md": "新正文"})
    assert updated.get_json()["code"] == "OK"
    assert "新标题" in client.get(f"/notes/{note_id}").get_data(as_text=True)

    assert client.delete(f"/notes/{note_id}").get_json()["message"] == "已删除"
    assert client.get(f"/notes/{note_id}").status_code == 404


def test_other_user_note_is_404_for_every_operation(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    note_id = client.post("/notes", json={"title": "A 的笔记", "content_md": "x"}).get_json()["data"]["id"]
    client.post("/auth/logout")

    register(client, "bob", "b@e.com")
    login(client, "b@e.com")
    calls = [
        lambda: client.get(f"/notes/{note_id}"),
        lambda: client.get(f"/notes/{note_id}/edit"),
        lambda: client.put(f"/notes/{note_id}", json={"title": "hack", "content_md": "x"}),
        lambda: client.post(f"/notes/{note_id}/publish"),
        lambda: client.delete(f"/notes/{note_id}"),
    ]
    for call in calls:
        assert call().status_code == 404


def test_anonymous_write_is_401_json(client):
    res = client.post("/notes", json={"title": "x", "content_md": "y"})
    assert res.status_code == 401
    assert res.get_json()["code"] == "ERR_UNAUTHORIZED"


def test_anonymous_page_redirects_to_login(client):
    res = client.get("/notes")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]
    assert "next=/notes" in res.headers["Location"]
    assert res.headers["Location"].split("next=")[1] == "/notes", "next 不应带多余的问号"

    with_query = client.get("/notes?tab=draft")
    target = unquote(with_query.headers["Location"].split("next=")[1])
    assert target == "/notes?tab=draft", "带查询条件的回跳地址要完整保留"


def test_preview_returns_sanitized_html(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    res = client.post("/api/preview", json={"content_md": "# 标题\n\n<script>alert(1)</script>"})
    html = res.get_json()["data"]["html"]
    assert "<h1>" in html
    assert "<script" not in html.lower()


def test_editor_pages_render(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    assert "写笔记" in client.get("/notes/new").get_data(as_text=True)

    note_id = client.post("/notes", json={"title": "草稿标题", "content_md": "正文内容"}).get_json()["data"]["id"]
    html = client.get(f"/notes/{note_id}/edit").get_data(as_text=True)
    assert "草稿标题" in html
    assert "正文内容" in html


def test_list_filters_and_paginates(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")

    published, drafts = [], []
    for index in range(12):
        note_id = client.post("/notes", json={"title": f"笔记{index}", "content_md": "正文"}).get_json()["data"]["id"]
        if index % 2 == 0:
            client.post(f"/notes/{note_id}/publish")
            published.append(f"笔记{index}")
        else:
            drafts.append(f"笔记{index}")

    page1 = client.get("/notes?tab=all&page=1").get_data(as_text=True)
    page2 = client.get("/notes?tab=all&page=2").get_data(as_text=True)
    assert page1.count('<article class="note-card">') == 10
    assert page2.count('<article class="note-card">') == 2

    all_titles = {f"笔记{index}" for index in range(12)}
    page1_titles = _titles_in(page1)
    page2_titles = _titles_in(page2)
    assert len(page1_titles) == 10
    assert len(page2_titles) == 2
    assert not (page1_titles & page2_titles), "两页不应重复"
    assert page1_titles | page2_titles == all_titles, "两页合起来应覆盖全部笔记"

    draft_titles = _titles_in(client.get("/notes?tab=draft").get_data(as_text=True))
    assert draft_titles == set(drafts)

    published_titles = _titles_in(client.get("/notes?tab=published").get_data(as_text=True))
    assert published_titles == set(published)


def test_empty_state_copy(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    assert "还没有笔记。写下第一行，它会留在这里。" in client.get("/notes").get_data(as_text=True)
    assert "草稿箱是空的。" in client.get("/notes?tab=draft").get_data(as_text=True)
    assert "还没有发布的笔记。发布后它会出现在这里。" in client.get("/notes?tab=published").get_data(as_text=True)


def test_detail_renders_markdown_inside_paper(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    note_id = client.post("/notes", json={"title": "标题", "content_md": "## 小节\n\n**粗体**"}).get_json()["data"]["id"]
    client.post(f"/notes/{note_id}/publish")
    html = client.get(f"/notes/{note_id}").get_data(as_text=True)
    assert 'class="paper"' in html
    assert "<h2>小节</h2>" in html
    assert "<strong>粗体</strong>" in html


def test_detail_empty_body_placeholder(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    note_id = client.post("/notes", json={"title": "只有标题的草稿", "content_md": ""}).get_json()["data"]["id"]
    html = client.get(f"/notes/{note_id}").get_data(as_text=True)
    assert "（这篇笔记还没有正文）" in html


def test_card_excerpt_strips_markdown_noise(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    body = "## 小节\n\n| 语法 | 效果 |\n| --- | --- |\n| `# 标题` | 一级标题 |\n\n- 项目一\n\n**粗体**\n\n[站点](https://example.com)"
    client.post("/notes", json={"title": "表格笔记", "content_md": body})

    html = client.get("/notes").get_data(as_text=True)
    excerpt = re.search(r'<p class="note-card__excerpt">([^<]*)</p>', html).group(1)
    for noise in ("##", "|", "---", "**", "](", "```"):
        assert noise not in excerpt, f"摘要不应包含 Markdown 记号 {noise}"
    assert "小节" in excerpt and "站点" in excerpt
