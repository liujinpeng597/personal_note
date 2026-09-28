# Phase 7: 分享与评论

**Goal:** 分享链接可生成、可选密码、可撤销；评论区按权限正确工作；整个分享面是全项目权限最敏感的地方，测试必须覆盖越权与失效。
**Prerequisites:** Phase 4 完成（发布态、详情页）；Phase 3 完成（登录态）。
**Deliverables:** `POST/DELETE /notes/<id>/share`；`/s/<token>` 分享页与密码页；`POST /s/<token>/unlock`；评论增删接口与评论区组件；相关测试。

**Interface Decisions Implemented:** 分享弹窗（密码开关、生成的链接、复制按钮、取消分享）；复制成功文案「已复制」；取消分享二次确认「取消后，这个链接会立刻失效。确定取消分享吗？」；分享页顶部提示条「这是他人分享给你的笔记，你正在以访客身份阅读。」；密码页「这篇笔记需要密码才能查看。」+「进入」；失效页「该分享链接已失效或已被作者取消。」；评论区空状态「还没有评论，来说点什么。」与未登录引导「登录后可以评论」。

---

## Task 1: 分享生成与撤销

**Goal:** 只有作者能给自己的已发布笔记生成或撤销分享链接，token 不可枚举，密码哈希存储。

**Files:**
- Create: `app/blueprints/share.py`（本任务只放接口）、`app/static/js/share.js`、`app/templates/partials/share_dialog.html`
- Modify: `app/blueprints/notes.py`（详情页传入分享状态）、`app/templates/notes/detail.html`（分享按钮与弹窗挂载）、`app/__init__.py`（注册蓝图）
- Test: `tests/test_share.py`

**Steps:**
- [x] 写 `share.py` 的接口：
  - `POST /notes/<int:note_id>/share`（`@api_login_required` + `owned_note_or_404`）：笔记必须是 `published`，否则 `fail('ERR_VALIDATION', '草稿不能分享，请先发布', status=400)`；请求带 `password`（空串或缺省 = 无密码）→ 有密码则校验长度 ≥ 4 且 ≤ 64；`token = secrets.token_urlsafe(16)`；查现有 `Share`：存在则复用那一行（更新 `password_hash`、清空 `revoked_at`、必要时换 token），不存在则新建；返回 `ok({'url': url_for('share.view', token=..., _external=False), 'has_password': bool})`，message 为「已生成分享链接」。
  - `DELETE /notes/<int:note_id>/share`：把 `revoked_at` 置为当前时间 → `ok(message='已取消分享')`；没有分享记录时同样返回该 message（幂等）。
- [x] 写 `share_dialog.html`：对话框含「设置密码（可选）」开关与输入、已生成链接的只读输入框 + 「复制」按钮、状态行（「未分享」/「已分享（无密码）」/「已分享（有密码）」）、底部「取消分享」次要按钮。
- [x] 写 `share.js`：点「分享」打开对话框 → 未分享时显示密码开关与「生成链接」按钮 → `POST` → 展示链接、聚焦复制按钮；「复制」用 `navigator.clipboard.writeText` 并在成功后把按钮文案改为「已复制」（2 秒后还原），剪贴板不可用时选中输入框并提示「请按 Ctrl+C 复制」；「取消分享」→ 确认弹窗 → `DELETE` → 状态回到「未分享」，已打开的分享页会看到失效页。
- [x] 详情页加「分享」按钮（仅 `published` 显示），并内联一个 `data-share-state` JSON 供 `share.js` 初始化。

- [x] 写用例：

```python
def test_share_generate_and_revoke(client, app):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    nid = client.post("/notes", json={"title": "可分享", "content_md": "内容"}).get_json()["data"]["id"]
    client.post(f"/notes/{nid}/publish")
    r = client.post(f"/notes/{nid}/share", json={})
    assert r.get_json()["code"] == "OK" and r.get_json()["data"]["has_password"] is False
    url = r.get_json()["data"]["url"]
    assert client.get(url).status_code == 200
    client.delete(f"/notes/{nid}/share")
    assert client.get(url).status_code == 410

def test_draft_cannot_be_shared(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    nid = client.post("/notes", json={"title": "草稿", "content_md": "x"}).get_json()["data"]["id"]
    r = client.post(f"/notes/{nid}/share", json={})
    assert r.status_code == 400 and "草稿" in r.get_json()["message"]

def test_only_owner_can_share_or_revoke(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    nid = client.post("/notes", json={"title": "A", "content_md": "x"}).get_json()["data"]["id"]
    client.post(f"/notes/{nid}/publish")
    url = client.post(f"/notes/{nid}/share", json={}).get_json()["data"]["url"]
    client.post("/auth/logout"); register(client, "bob", "b@e.com"); login(client, "b@e.com")
    assert client.post(f"/notes/{nid}/share", json={}).status_code == 404
    assert client.delete(f"/notes/{nid}/share").status_code == 404
    assert client.get(url).status_code == 200  # 未被他人撤销

def test_token_is_random_and_not_guessable(client, app):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    nid = client.post("/notes", json={"title": "A", "content_md": "x"}).get_json()["data"]["id"]
    client.post(f"/notes/{nid}/publish")
    t1 = client.post(f"/notes/{nid}/share", json={}).get_json()["data"]["url"].rstrip("/").split("/")[-1]
    client.delete(f"/notes/{nid}/share")
    t2 = client.post(f"/notes/{nid}/share", json={}).get_json()["data"]["url"].rstrip("/").split("/")[-1]
    assert t1 != t2 and len(t1) >= 20
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_share.py -q`
  - Expected: 通过。

**Security/Boundary Notes:** token 必须来自 `secrets`（禁止 `random`/自增 id）；密码上限 64 字符避免哈希开销被滥用；撤销后必须立刻 410，不得缓存；已发布笔记删除时分享随级联消失。

---

## Task 2: 分享访问与密码解锁

**Goal:** 无密码链接直接可读；有密码必须解锁且本次会话内免重复输入；失效链接有明确页面。

**Files:**
- Modify: `app/blueprints/share.py`（`GET /s/<token>`、`POST /s/<token>/unlock`）、`app/templates/share/view.html`、`app/templates/share/password.html`、`app/static/css/pages/share.css`
- Test: `tests/test_share.py`

**Steps:**
- [x] `GET /s/<token>`：查 `Share` → 不存在 404；`revoked_at` 非空 → 410（渲染 `errors/410.html`）；`password_hash` 为空或 `session.get(f'share_ok:{token}')` 为真 → 渲染 `share/view.html`（复用纸张版式，顶部提示条，评论区）；否则渲染 `share/password.html`。
- [x] `POST /s/<token>/unlock`：`check_password_hash` 失败 → `fail('ERR_SHARE_PASSWORD')`；成功 → `session[f'share_ok:{token}'] = True` → `ok({'redirect': url_for('share.view', token=token)})`。（会话 Cookie 非 permanent，符合「本次会话内有效」。）
- [x] `share/view.html` 不显示作者邮箱、不显示编辑/删除按钮、不显示草稿信息；正文同样经 `render_md` 过滤器。
- [x] 密码页用与登录页一致的字段宏，错误就地显示「密码不正确，请重试。」。
- [x] 写用例：

```python
def test_password_share_flow(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    nid = client.post("/notes", json={"title": "加密笔记", "content_md": "机密内容"}).get_json()["data"]["id"]
    client.post(f"/notes/{nid}/publish")
    url = client.post(f"/notes/{nid}/share", json={"password": "s3cret"}).get_json()["data"]["url"]
    client.post("/auth/logout")
    anon = client
    assert "机密内容" not in anon.get(url).get_data(as_text=True)
    assert "这篇笔记需要密码才能查看。" in anon.get(url).get_data(as_text=True)
    assert anon.post(url + "/unlock", json={"password": "bad"}).status_code == 403
    assert anon.post(url + "/unlock", json={"password": "s3cret"}).get_json()["code"] == "OK"
    assert "机密内容" in anon.get(url).get_data(as_text=True)

def test_password_required_per_session(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    nid = client.post("/notes", json={"title": "X", "content_md": "秘密"}).get_json()["data"]["id"]
    client.post(f"/notes/{nid}/publish")
    url = client.post(f"/notes/{nid}/share", json={"password": "pw12"}).get_json()["data"]["url"]
    client.post("/auth/logout")
    assert "这篇笔记需要密码才能查看。" in client.get(url).get_data(as_text=True)
    client.post(url + "/unlock", json={"password": "pw12"})
    with client.session_transaction() as sess:
        sess.clear()  # 模拟新会话
    assert "这篇笔记需要密码才能查看。" in client.get(url).get_data(as_text=True)

def test_unknown_and_revoked_token(client):
    assert client.get("/s/not-a-real-token").status_code == 404
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    nid = client.post("/notes", json={"title": "X", "content_md": "y"}).get_json()["data"]["id"]
    client.post(f"/notes/{nid}/publish")
    url = client.post(f"/notes/{nid}/share", json={}).get_json()["data"]["url"]
    client.delete(f"/notes/{nid}/share")
    res = client.get(url)
    assert res.status_code == 410 and "已失效" in res.get_data(as_text=True)
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_share.py -q`
  - Expected: 通过。

**Security/Boundary Notes:** 解锁标记只写 session；分享页是匿名可达面，禁止渲染任何用户私有字段；410 与 404 都不能回显笔记标题或作者信息。

**Visual Verification:** 分享页在 1440×900 与 390×844 下纸张版式与详情页一致、顶部提示条不遮挡正文；密码页错误态就地显示；失效页有「回到主页」按钮。

---

## Task 3: 评论

**Goal:** 登录用户可评论、可删自己的评论；访客可读不可写；空态与计数正确。

**Files:**
- Create: `app/templates/partials/comments.html`
- Modify: `app/blueprints/share.py`（`POST /notes/<id>/comments`、`DELETE /comments/<id>`）、`app/templates/notes/detail.html` 与 `app/templates/share/view.html`（挂载评论区）、`app/static/js/notes.js`（提交与删除）
- Test: `tests/test_comments.py`

**Steps:**
- [x] `POST /notes/<int:note_id>/comments`（`@api_login_required`）：笔记须存在且为 `published`（否则 404）；内容去空白后 1–500 字，否则 `fail('ERR_VALIDATION', '评论内容不能为空', fields={'content': ...})`；返回 `ok({'comment': {...}}, '已发表评论', status=201)`。
- [x] `DELETE /comments/<int:comment_id>`（`@api_login_required`）：非作者 → 404（**不**返回 403，避免探测评论归属）；成功 `ok(message='已删除评论')`。
- [x] 写 `partials/comments.html`：`<section aria-label="评论">` + 计数 + 列表（每条：用户名、时间、内容，`white-space: pre-wrap` 保留换行；自己的评论显示「删除」）+ 输入框（textarea，`maxlength="500"`）+「发表评论」按钮；未登录时用「登录后可以评论」+ 登录链接替换输入区（链接带 `?next=` 回当前页）；列表为空时显示「还没有评论，来说点什么。」。
- [x] `notes.js` 追加：提交评论 → `POST` → 成功后把新评论插入列表顶部并清空输入框、计数 +1；失败时保留输入内容。删除 → 确认弹窗「删除后无法恢复，确定删除这条评论吗？」→ `DELETE` → 成功后移除该条并计数 -1。
- [x] 写用例：

```python
def test_comment_crud_and_permissions(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    nid = client.post("/notes", json={"title": "可评论", "content_md": "x"}).get_json()["data"]["id"]
    client.post(f"/notes/{nid}/publish")
    cid = client.post(f"/notes/{nid}/comments", json={"content": "第一条\n换行"}).get_json()["data"]["comment"]["id"]
    assert "第一条" in client.get(f"/notes/{nid}").get_data(as_text=True)
    client.post("/auth/logout")
    assert client.post(f"/notes/{nid}/comments", json={"content": "游客"}).status_code == 401
    assert client.delete(f"/comments/{cid}").status_code == 401
    register(client, "bob", "b@e.com"); login(client, "b@e.com")
    assert client.delete(f"/comments/{cid}").status_code == 404
    login(client, "a@e.com")
    assert client.delete(f"/comments/{cid}").get_json()["code"] == "OK"

def test_comment_validation_and_empty_copy(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    nid = client.post("/notes", json={"title": "X", "content_md": "x"}).get_json()["data"]["id"]
    client.post(f"/notes/{nid}/publish")
    assert "还没有评论，来说点什么。" in client.get(f"/notes/{nid}").get_data(as_text=True)
    r = client.post(f"/notes/{nid}/comments", json={"content": "   "})
    assert r.status_code == 400 and r.get_json()["data"]["fields"]["content"]
    r2 = client.post(f"/notes/{nid}/comments", json={"content": "字" * 501})
    assert r2.status_code == 400

def test_draft_cannot_be_commented(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    draft = client.post("/notes", json={"title": "草稿", "content_md": "x"}).get_json()["data"]["id"]
    assert client.post(f"/notes/{draft}/comments", json={"content": "hi"}).status_code == 404
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_comments.py -q`
  - Expected: 通过。

**Security/Boundary Notes:** 评论按纯文本存储与输出（依赖 Jinja 自动转义 + `pre-wrap`），**禁止** `|safe`；删他人评论返回 404；草稿不可评论。

**Visual Verification:** 评论区在详情页与分享页外观一致；多行评论换行保留；未登录看到登录引导；提交后新评论出现在顶部且页面不刷新。

---

## Phase Completion Checklist

- [x] 所有任务完成
- [x] `.venv\Scripts\python.exe -m pytest -q` 全绿
- [ ] 手工走通：作者分享（无密码 / 有密码）→ 访客打开 → 密码错误 → 解锁 → 评论 → 作者撤销 → 访客刷新看到失效页　—　未执行：需真实浏览器交互或人工确认，见 `visual-check.md` 第五节
- [x] 越权矩阵（他人笔记的分享/取消分享/评论/删评论）全部为 404
- [x] 分享页与密码页截图核对通过（记入 `visual-check.md`）
- [x] 可以进入 Phase 8
