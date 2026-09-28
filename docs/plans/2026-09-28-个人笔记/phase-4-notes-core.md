# Phase 4: 笔记核心

**Goal:** 写笔记、存草稿、发布、列表、详情形成闭环；详情页落成设计文档的签名元素「一张真纸」。
**Prerequisites:** Phase 3 完成（登录态与 `partials/field.html`）。
**Deliverables:** `notes` 蓝图 4 个写接口与 3 个页面；`/api/preview`；`editor.js`、`notes.js`；`paper.jpg` 接入的纸张容器；空状态与状态徽标。

**Interface Decisions Implemented:** 编辑器左写右预览分栏与 <900px 写作/预览切换；「存草稿」「发布」按钮与 loading 态；脏数据离开提醒；列表页 tab（全部/已发布/草稿）+ 分页 + 卡片密度与「草稿/已发布」徽标；空状态文案「还没有笔记。写下第一行，它会留在这里。」「草稿箱是空的。」；详情页羊皮纸纸张容器与正文 inset；空正文占位「（这篇笔记还没有正文）」；删除二次确认文案「删除后无法恢复，确定删除《标题》吗？」。

---

## Task 1: 笔记接口与所有权校验

**Goal:** 四个写接口按信封返回，任何人只能操作自己的笔记，越权与不存在不可区分。

**Files:**
- Create: `app/blueprints/notes.py`、`tests/helpers.py`、`tests/test_notes.py`
- Modify: `app/__init__.py`（注册蓝图）、`config.py`（`DEFAULT_LANDING_ENDPOINT = 'notes.list'`）、`app/utils/security.py`（追加 `owned_note_or_404(note_id)`）

**Steps:**
- [x] 在 `app/utils/security.py` 追加：

```python
def owned_note_or_404(note_id):
    """返回当前用户的笔记；不属于当前用户或不存在时抛 404（ERR_NOT_FOUND）。"""
    note = db.session.get(Note, note_id)
    if note is None or note.user_id != session.get('user_id'):
        abort(404)
    return note
```

- [x] 写 `notes.py`：
  - `_validate(title, content_md, require_body)`：标题去空白后必须 1–120 字（始终校验）；`require_body=True` 时正文去空白后必须非空（**发布**才要求）；返回 `fields` 字典。存草稿允许只有标题、正文为空。
  - `POST /notes`（`@api_login_required`）：建 `Note(status='draft')` → `ok({'id': note.id, 'url': url_for('notes.detail', note_id=note.id)}, '已保存草稿', status=201)`。
  - `PUT /notes/<int:note_id>`（`@api_login_required` + `owned_note_or_404`）：更新标题/正文，`updated_at` 刷新 → `ok({'id': ..., 'updated_at': ...}, '已保存')`。
  - `POST /notes/<int:note_id>/publish`：`require_body=True` → `status='published'`，首次发布写 `published_at` → `ok({'id': ..., 'url': ...}, '已发布')`。
  - `DELETE /notes/<int:note_id>`：删除（级联由模型负责）→ `ok(message='已删除')`。
  - `GET /notes`（页面视图，`@login_required`，端点 `notes.list`）：本阶段只支持 `?tab=all|published|draft` 与 `?page=`，每页 10，`updated_at` 倒序，渲染 `notes/list.html`。
  - `GET /notes/new`（`@login_required`，端点 `notes.editor_new`）：渲染空编辑器。
  - `GET /notes/<int:note_id>`（`@login_required` + `owned_note_or_404`，端点 `notes.detail`）：渲染详情。
  - `GET /notes/<int:note_id>/edit`（端点 `notes.editor_edit`）：渲染编辑器并回填。
- [x] 写 `tests/helpers.py`，提供**全部后续测试文件复用**的造数辅助函数（各测试文件顶部统一写 `from helpers import register, login`，不再各自重复定义）：

```python
def register(client, username="alice", email="a@e.com", password="Passw0rd!"):
    res = client.post("/auth/register", json={"username": username, "email": email,
                                              "password": password, "password_confirm": password})
    assert res.status_code == 201, res.get_json()
    client.post("/auth/logout")
    return res

def login(client, email="a@e.com", password="Passw0rd!"):
    res = client.post("/auth/login", json={"email": email, "password": password})
    assert res.get_json()["code"] == "OK", res.get_json()
    return res
```

- [x] 写 `tests/test_notes.py`（用例统一采用 `register(client, ...)` / `login(client, ...)` 的调用形式）：

```python
def test_create_draft_then_publish(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    r = client.post("/notes", json={"title": "第一篇", "content_md": "# 你好"})
    assert r.status_code == 201 and r.get_json()["message"] == "已保存草稿"
    nid = r.get_json()["data"]["id"]
    assert client.post(f"/notes/{nid}/publish").get_json()["message"] == "已发布"
    assert client.get(f"/notes/{nid}").status_code == 200

def test_validation_and_publish_requires_body(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    r = client.post("/notes", json={"title": "   ", "content_md": ""})
    assert r.status_code == 400 and r.get_json()["code"] == "ERR_VALIDATION"
    assert "标题" in r.get_json()["data"]["fields"]["title"]
    nid = client.post("/notes", json={"title": "只有标题的草稿", "content_md": ""}).get_json()["data"]["id"]
    pub = client.post(f"/notes/{nid}/publish")
    assert pub.status_code == 400 and "正文" in pub.get_json()["data"]["fields"]["content_md"]

def test_other_user_note_is_404_for_every_operation(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    nid = client.post("/notes", json={"title": "A 的笔记", "content_md": "x"}).get_json()["data"]["id"]
    client.post("/auth/logout")
    register(client, "bob", "b@e.com"); login(client, "b@e.com")
    for call in (lambda: client.get(f"/notes/{nid}"), lambda: client.get(f"/notes/{nid}/edit"),
                 lambda: client.put(f"/notes/{nid}", json={"title": "hack", "content_md": "x"}),
                 lambda: client.post(f"/notes/{nid}/publish"), lambda: client.delete(f"/notes/{nid}")):
        assert call().status_code == 404

def test_anonymous_write_is_401_json(client):
    r = client.post("/notes", json={"title": "x", "content_md": "y"})
    assert r.status_code == 401 and r.get_json()["code"] == "ERR_UNAUTHORIZED"

def test_anonymous_page_redirects_to_login(client):
    res = client.get("/notes")
    assert res.status_code == 302 and "/login" in res.headers["Location"]
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_notes.py -q`
  - Expected: 全部通过。

**Security/Boundary Notes:** 所有写路径都必须先过 `owned_note_or_404`；越权一律 404，禁止在响应中区分「不存在」与「无权限」。页面视图用 `login_required`（302），接口用 `api_login_required`（401 JSON）。

---

## Task 2: 编辑器

**Goal:** 编辑器可新建、可续写草稿、可发布，右侧预览由服务端渲染，未保存内容有离开提醒。

**Files:**
- Create: `app/templates/notes/editor.html`、`app/static/js/editor.js`、`app/static/css/pages/notes.css`
- Modify: `app/blueprints/main.py`（追加 `POST /api/preview`）、`app/templates/base.html`（引入 `pages/notes.css`、`editor.js`）
- Test: `tests/test_notes.py`（追加预览与编辑器页面用例）

**Steps:**
- [x] 在 `main.py` 追加：`@bp.post('/api/preview')`（`@api_login_required`）→ `ok({'html': render_markdown(payload.get('content_md', ''))})`。
- [x] 写 `editor.html`：`<h1>` 为「写笔记」或「编辑笔记」；字段：标题 input、textarea `#content-md`、预览面板 `#preview`、按钮「存草稿」「发布」；携带 `data-note-id`、`data-updated-at`（用于并发提示，本阶段只用于脏检查）。
- [x] 写 `editor.js`：
  - 标题或正文变化 → `dirty = true`；`beforeunload` 时若有脏数据则 `e.preventDefault()`；站内链接点击前用 `confirm('还有未保存的修改，确定离开吗？')`。
  - 输入 → 300ms 防抖 → `POST /api/preview` → 写入 `#preview.innerHTML`；请求期间预览区显示「正在渲染…」。
  - 「存草稿」：新建时 `POST /notes`，已有则 `PUT /notes/<id>`；成功后清脏标记，按钮文案短暂变「已保存」。
  - 「发布」：先确保已创建（必要时 `POST /notes`）→ `POST /notes/<id>/publish` → 成功 `location.href = res.data.url`。
  - 提交期间按钮 `disabled` + 文案「保存中…」/「发布中…」。
- [x] `notes.css` 的编辑器部分：

```css
.editor { display: grid; grid-template-columns: 55% 45%; gap: 0; border: 1px solid var(--brown); border-radius: 10px; overflow: hidden; background: var(--surface); }
.editor__pane + .editor__pane { border-left: 1px solid var(--brown); }
.editor__pane { padding: 20px; min-height: 420px; }
.editor textarea { width: 100%; min-height: 360px; border: 0; resize: vertical; font: inherit; background: transparent; }
@media (max-width: 899px) {
  .editor { grid-template-columns: 1fr; }
  .editor__pane + .editor__pane { border-left: 0; border-top: 1px solid var(--brown); }
  .editor[data-mode="write"] .editor__pane--preview,
  .editor[data-mode="preview"] .editor__pane--write { display: none; }
}
```

- [x] 追加用例：

```python
def test_preview_returns_sanitized_html(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    r = client.post("/api/preview", json={"content_md": "# 标题\n\n<script>alert(1)</script>"})
    assert "<h1>" in r.get_json()["data"]["html"] and "script" not in r.get_json()["data"]["html"].lower()

def test_editor_pages_render(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    assert "写笔记" in client.get("/notes/new").get_data(as_text=True)
    nid = client.post("/notes", json={"title": "草稿标题", "content_md": "正文"}).get_json()["data"]["id"]
    html = client.get(f"/notes/{nid}/edit").get_data(as_text=True)
    assert "草稿标题" in html and "正文" in html
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_notes.py -q`
  - Expected: 通过。

**Visual Verification:** 1440×900 下左右分栏 55/45，预览区实时更新；390×844 下出现「写作 / 预览」切换且各占全宽；textarea 内滚动不影响页面；两按钮触摸目标 ≥ 40px。

---

## Task 3: 笔记列表页

**Goal:** 列表按 tab 过滤、按更新时间倒序、可翻页，空态与「草稿/已发布」徽标清楚。

**Files:**
- Create: `app/templates/notes/list.html`、`app/templates/partials/note_card.html`、`app/templates/partials/empty.html`
- Modify: `app/static/css/pages/notes.css`（卡片与网格）、`app/static/js/notes.js`（删除确认）
- Test: `tests/test_notes.py`（追加列表用例）

**Steps:**
- [x] 写 `partials/note_card.html` 宏 `note_card(note)`：标题、正文首行摘要（纯文本截断 80 字，`note.content_md|striptags|truncate(80)`）、`updated_at`、状态徽标（`草稿`/`已发布`）、标签 chip（Phase 5 起有数据）。
- [x] 写 `partials/empty.html` 宏 `empty(text, action_text=None, action_href=None)`。
- [x] 写 `list.html`：`<h1>我的笔记</h1>` + 三个 tab 链接（`?tab=all|published|draft`，当前项 `aria-current="page"`）+ 卡片网格 + 分页（上一页/下一页 + 页码，`?page=`）+ 空态：
  - `tab=all` 且无笔记：「还没有笔记。写下第一行，它会留在这里。」+ 按钮「写第一篇笔记」。
  - `tab=draft` 且无草稿：「草稿箱是空的。」
  - `tab=published` 且无已发布：「还没有发布的笔记。发布后它会出现在这里。」
- [x] `notes.js`：删除按钮 → 确认弹窗「删除后无法恢复，确定删除《标题》吗？」→ `DELETE /notes/<id>` → 成功后 `location.reload()`；收藏按钮本阶段不实现（Phase 6）。
- [x] 追加用例：

```python
def test_list_filters_and_paginates(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    published, drafts = [], []
    for i in range(12):
        nid = client.post("/notes", json={"title": f"笔记{i}", "content_md": "正文"}).get_json()["data"]["id"]
        if i % 2 == 0:
            client.post(f"/notes/{nid}/publish"); published.append(f"笔记{i}")
        else:
            drafts.append(f"笔记{i}")
    page1 = client.get("/notes?tab=all&page=1").get_data(as_text=True)
    page2 = client.get("/notes?tab=all&page=2").get_data(as_text=True)
    assert page1.count("note-card") == 10 and "note-card" in page2
    assert "笔记11" in page2 and "笔记11" not in page1
    draft_html = client.get("/notes?tab=draft").get_data(as_text=True)
    assert all(t in draft_html for t in drafts) and all(t not in draft_html for t in published)
    pub_html = client.get("/notes?tab=published").get_data(as_text=True)
    assert all(t in pub_html for t in published) and all(t not in pub_html for t in drafts)

def test_empty_state_copy(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    assert "还没有笔记。写下第一行，它会留在这里。" in client.get("/notes").get_data(as_text=True)
    assert "草稿箱是空的。" in client.get("/notes?tab=draft").get_data(as_text=True)
    assert "还没有发布的笔记。发布后它会出现在这里。" in client.get("/notes?tab=published").get_data(as_text=True)
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_notes.py -q`
  - Expected: 通过；第一页 10 张卡片。

**Visual Verification:** ≥768 两列、<768 单列；卡片 hover 阴影加深；摘要不溢出（长英文单词换行）；分页控件在只有一页时不显示。

---

## Task 4: 笔记详情与纸张签名元素

**Goal:** 详情页正文落在一张旧纸上，版式与对比度符合设计契约。

**Files:**
- Create: `app/templates/notes/detail.html`
- Modify: `app/static/css/components.css`（`.paper` 正式实现）、`app/static/img/paper.jpg`（由素材复制）
- Test: `tests/test_notes.py`（追加详情渲染用例）

**Steps:**
- [x] 复制素材：

```powershell
Copy-Item '个人笔记-笔记背景.jpg' 'app\static\img\paper.jpg'
```

- [x] `.paper` 实现（`components.css`）：

```css
.paper {
  max-width: 760px; margin: 32px auto; padding: clamp(28px, 7%, 64px);
  background: url("../img/paper.jpg") center / 100% 100% no-repeat;
  border: 1px solid var(--parchment-edge); border-radius: 4px;
  box-shadow: 0 8px 24px rgba(59, 50, 41, .08); color: var(--ink);
}
.paper .prose { font-family: "Georgia", "Times New Roman", "Songti SC", "SimSun", serif; font-size: 17px; line-height: 1.9; }
.paper .prose img { max-width: 100%; height: auto; }
.paper .prose pre { overflow-x: auto; background: rgba(59, 50, 41, .06); padding: 12px; border-radius: 6px; }
```

  - inset 说明：素材随容器等比拉伸，故内边距用百分比（`7%`，下限 28px、上限 64px），桌面下 ≥ 48px，移动端按纸宽等比缩小，始终避开手撕毛边与角落藤蔓纹。

- [x] 写 `detail.html`：`<article>` 内 `<h1>` 标题 + 元信息（更新时间、状态徽标）+ `.paper` 容器内 `<div class="prose">{{ note.content_md | render_md | safe }}</div>`（正文为空时显示占位「（这篇笔记还没有正文）」）+ 纸张下方：标签、收藏位、分享位、作者操作（「编辑」「删除」）。
- [x] 追加用例：

```python
def test_detail_renders_markdown_inside_paper(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    nid = client.post("/notes", json={"title": "标题", "content_md": "## 小节\n\n**粗体**"}).get_json()["data"]["id"]
    client.post(f"/notes/{nid}/publish")
    html = client.get(f"/notes/{nid}").get_data(as_text=True)
    assert 'class="paper"' in html and "<h2>小节</h2>" in html and "<strong>粗体</strong>" in html

def test_detail_empty_body_placeholder(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    nid = client.post("/notes", json={"title": "只有标题的草稿", "content_md": ""}).get_json()["data"]["id"]
    html = client.get(f"/notes/{nid}").get_data(as_text=True)
    assert "（这篇笔记还没有正文）" in html
```

  - 说明：存草稿允许正文为空（见 Task 1 的校验规则），因此空正文占位在草稿详情页可被真实触发。

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_notes.py -q`
  - Expected: 通过。

**Visual Verification:** 1440×900 下纸张居中、最大 760px、正文四周留白 ≥ 48px 不压角饰与毛边；长正文（≥2000 字）滚动时纸张完整不重复；390×844 下正文内边距按比例缩小、无横向溢出、正文单列可读；正文墨色 `--ink` 在纸面 `--parchment` 上目视对比充足（≥ 9:1）。

---

## Phase Completion Checklist

- [x] 所有任务完成
- [x] `.venv\Scripts\python.exe -m pytest -q` 全绿
- [ ] 新建 → 存草稿 → 列表看到草稿 → 续写 → 发布 → 详情页看到纸张 的闭环手工走通　—　未执行：需真实浏览器交互或人工确认，见 `visual-check.md` 第五节
- [x] 详情页与编辑器截图核对通过（记入 `visual-check.md`）
- [x] 可以进入 Phase 5
