# Phase 5: 标签与搜索

**Goal:** 每篇笔记可打标签，列表可按标签筛选、按关键词搜索（标题/正文/标签），无结果有明确文案。
**Prerequisites:** Phase 4 完成（笔记列表页、编辑器、卡片片段）。
**Deliverables:** 标签解析与存储；编辑器标签输入；标签筛选；搜索框；空结果文案；相关测试。

**Interface Decisions Implemented:** 标签 chip 组件（`--leaf-soft` 底、999px 圆角）；列表页筛选行布局（tab + 搜索框 + 标签筛选）；搜索无结果文案「没有找到包含「关键词」的笔记。」；标签约束「每篇最多 5 个、每个 ≤ 20 字」的中文校验提示。

---

## Task 1: 标签解析、存储与展示

**Goal:** 标签从输入到入库再到展示全链路正确，超限有中文提示。

**Files:**
- Create: `app/utils/tags.py`（解析与写库）
- Modify: `app/blueprints/notes.py`（`POST /notes`、`PUT /notes/<id>` 接受 `tags` 字段；详情与列表传入标签）、`app/templates/notes/editor.html`（标签输入）、`app/templates/notes/detail.html`（chip 展示）、`app/templates/partials/note_card.html`（chip 展示）
- Test: `tests/test_tags_search.py`

**Steps:**
- [x] 写 `app/utils/tags.py`：

```python
MAX_TAGS, MAX_TAG_LEN = 5, 20

def parse_tags(raw: str) -> tuple[list[str], dict]:
    """逗号（中英文）切分 → 去空白 → 去重（小写比较）→ 校验数量与长度。
    返回 (标签列表, 字段错误字典)。"""
```

  - 错误文案：数量超限 → `"最多只能添加 5 个标签"`；单个超长 → `"单个标签不能超过 20 字"`，键名 `tags`。

- [x] 写 `sync_note_tags(note, names)`：按名字取或建 `Tag`（名字原样保留大小写，比较用小写），替换 `note.tags`。
- [x] `notes.py` 的创建与更新路径接收 `tags`（字符串），解析失败时与标题/正文校验合并进 `fail('ERR_VALIDATION', fields=...)`。
- [x] 编辑器加标签输入：`<input id="tags" name="tags" placeholder="用逗号分隔，最多 5 个">`，回填时用 `, ` 连接已有标签；提交时随 `tags` 一起发送。
- [x] 详情页与卡片渲染 chip：`{% for tag in note.tags %}<a class="chip" href="{{ url_for('notes.list', tag=tag.name) }}">{{ tag.name }}</a>{% endfor %}`。
- [x] 写用例：

```python
def test_tags_saved_and_rendered(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    nid = client.post("/notes", json={"title": "带标签", "content_md": "正文", "tags": "读书, 效率，读书"}).get_json()["data"]["id"]
    html = client.get(f"/notes/{nid}").get_data(as_text=True)
    assert "读书" in html and "效率" in html and html.count('class="chip"') == 2  # 去重

def test_tag_limits_return_chinese_error(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    r = client.post("/notes", json={"title": "x", "content_md": "y", "tags": "a,b,c,d,e,f"})
    assert r.get_json()["code"] == "ERR_VALIDATION" and "最多" in r.get_json()["data"]["fields"]["tags"]
    r2 = client.post("/notes", json={"title": "x", "content_md": "y", "tags": "一" * 21})
    assert "20" in r2.get_json()["data"]["fields"]["tags"]
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_tags_search.py -q`
  - Expected: 通过；重复标签只留一个。

**Security/Boundary Notes:** 标签名入库前必须限长与限量，避免超长字符串写入；标签不接受 HTML（模板自动转义，渲染时不得用 `|safe`）。

---

## Task 2: 搜索与标签筛选

**Goal:** 列表页可组合 tab、关键词、标签、分页，搜索无结果文案准确。

**Files:**
- Modify: `app/blueprints/notes.py`（`GET /notes` 支持 `?q=` 与 `?tag=`）、`app/templates/notes/list.html`（搜索表单与筛选行）、`app/static/css/pages/notes.css`
- Test: `tests/test_tags_search.py`

**Steps:**
- [x] `GET /notes` 查询构造：始终限定 `Note.user_id == session['user_id']`；`tab=draft` → `status=='draft'`，`tab=published` → `status=='published'`；`q` 非空 → `or_(Note.title.ilike(f'%{q}%'), Note.content_md.ilike(f'%{q}%'), Note.tags.any(Tag.name.ilike(f'%{q}%')))`；`tag` 非空 → `Note.tags.any(Tag.name == tag)`；`q` 与 `tag` 可同时生效；排序 `Note.updated_at.desc()`；`paginate(page=page, per_page=10, error_out=False)`。
- [x] 列表页加筛选行：`<form method="get" action="{{ url_for('notes.list') }}">` 内含搜索框 `name="q"`、保留当前 `tab` 与 `tag` 的隐藏字段、提交按钮「搜索」；当前标签显示为可移除的 chip（点击回无标签列表）。
- [x] 空结果文案：当 `q` 非空且结果为空时渲染「没有找到包含「{{ q }}」的笔记。」；当 `tag` 非空且为空时渲染「标签「{{ tag }}」下还没有笔记。」；两者都有时优先展示搜索文案。
- [x] 写用例：

```python
def test_search_matches_title_body_and_tag(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    a = client.post("/notes", json={"title": "读书笔记", "content_md": "正文", "tags": "阅读"}).get_json()["data"]["id"]
    b = client.post("/notes", json={"title": "别的", "content_md": "里面有 读书 两个字"}).get_json()["data"]["id"]
    c = client.post("/notes", json={"title": "第三篇", "content_md": "无关", "tags": "读书"}).get_json()["data"]["id"]
    for nid in (a, b, c):
        client.post(f"/notes/{nid}/publish")
    for nid in (a, b, c):
        assert f"/notes/{nid}" in client.get("/notes?q=读书").get_data(as_text=True)

def test_search_isolated_to_owner_and_empty_copy(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    client.post("/notes", json={"title": "秘密", "content_md": "只有我有"})
    client.post("/auth/logout"); register(client, "bob", "b@e.com"); login(client, "b@e.com")
    html = client.get("/notes?q=秘密").get_data(as_text=True)
    assert not _titles_in(html) and '没有找到包含「秘密」的笔记。' in html

def test_tag_filter_and_combination(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    client.post("/notes", json={"title": "甲", "content_md": "x", "tags": "工作"})
    client.post("/notes", json={"title": "乙", "content_md": "x", "tags": "生活"})
    html = client.get("/notes?tag=工作").get_data(as_text=True)
    assert "甲" in html and "乙" not in html
    assert "标签「工作」下还没有笔记。" in client.get("/notes?tag=不存在").get_data(as_text=True)
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_tags_search.py -q`
  - Expected: 通过；搜索永不越出当前用户。

**Security/Boundary Notes:** 关键词要经 ORM 参数化（`ilike` + 绑定参数），禁止字符串拼 SQL；搜索结果同样受 `user_id` 限制，草稿也在自己范围内可见。

**Visual Verification:** 筛选行在 1440×900 单行显示、390×844 自动换行；焦点顺序 tab → 搜索框 → 搜索按钮 → 标签 chip；chip 在卡片与详情页样式一致。

---

## Phase Completion Checklist

- [x] 所有任务完成
- [x] `.venv\Scripts\python.exe -m pytest -q` 全绿
- [ ] 标签、搜索、筛选与分页可组合手工验证通过　—　未执行：需真实浏览器交互或人工确认，见 `visual-check.md` 第五节
- [x] 列表页筛选行截图核对通过（记入 `visual-check.md`）
- [x] 可以进入 Phase 6
