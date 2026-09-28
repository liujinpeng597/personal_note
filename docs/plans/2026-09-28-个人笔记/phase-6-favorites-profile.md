# Phase 6: 收藏与个人主页

**Goal:** 收藏是杯上那颗小爱心的形状与颜色，可切换且幂等；个人主页展示资料与「笔记 / 收藏」两个 tab。
**Prerequisites:** Phase 4 完成（详情页、`note_card`）；Phase 5 完成（标签 chip 用于卡片）。
**Deliverables:** `POST /notes/<id>/favorite`；爱心按钮组件；`/u/<username>` 资料卡与两个 tab；相关测试。

**Interface Decisions Implemented:** 收藏图标（未收藏 1.5px 描边 / 已收藏实心 `--heart #C9793F`）——设计文档指定该色取自素材中杯身小爱心；收藏计数；未登录点击提示「请先登录再收藏。」；个人主页资料卡与 tab 布局；空收藏文案「你还没有收藏任何笔记。看到喜欢的，点一下那颗心。」；个人主页只展示已发布笔记。

---

## Task 1: 收藏接口与爱心按钮

**Goal:** 点击爱心完成切换、计数正确、重复请求幂等；未登录有明确提示。

**Files:**
- Modify: `app/blueprints/notes.py`（追加路由与详情页传入 `favorited`/`favorite_count`）、`app/templates/notes/detail.html`、`app/templates/partials/note_card.html`、`app/static/js/notes.js`、`app/static/css/components.css`
- Test: `tests/test_favorites.py`

**Steps:**
- [x] 在 `notes.py` 追加 `POST /notes/<int:note_id>/favorite`（`@api_login_required`）：

```python
existing = Favorite.query.filter_by(user_id=session['user_id'], note_id=note_id).first()
if existing:
    db.session.delete(existing); favorited = False
else:
    db.session.add(Favorite(user_id=session['user_id'], note_id=note_id)); favorited = True
db.session.commit()
count = Favorite.query.filter_by(note_id=note_id).count()
return ok({'favorited': favorited, 'count': count}, '已收藏' if favorited else '已取消收藏')
```

  - 该接口**不**要求收藏者拥有笔记，但要求目标笔记存在且状态为 `published`，否则 404（避免探测草稿）。

- [x] 详情页与卡片加入爱心按钮：

```html
<button class="favorite-btn" data-note-id="{{ note.id }}"
        data-favorited="{{ 'true' if favorited else 'false' }}"
        aria-pressed="{{ 'true' if favorited else 'false' }}"
        aria-label="{{ '取消收藏' if favorited else '收藏这篇笔记' }}">
  <svg class="favorite-btn__icon" viewBox="0 0 24 24" aria-hidden="true">…爱心路径…</svg>
  <span class="favorite-btn__count">{{ favorite_count }}</span>
</button>
```

- [x] `components.css`：

```css
.favorite-btn__icon { width: 22px; height: 22px; fill: none; stroke: var(--heart); stroke-width: 1.5; }
.favorite-btn[aria-pressed="true"] .favorite-btn__icon { fill: var(--heart); }
.favorite-btn { min-height: 40px; }
```

- [x] `notes.js`：绑定 `.favorite-btn` 点击 → 若按钮带 `data-requires-login="true"`（未登录渲染时加）→ `toast('error', '请先登录再收藏。')` 并返回；否则 `request('/notes/'+id+'/favorite', {method:'POST'})` → 用返回值更新 `aria-pressed`、`aria-label` 与计数。
- [x] 写用例：

```python
def test_favorite_toggle_is_idempotent(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    nid = client.post("/notes", json={"title": "可收藏", "content_md": "x"}).get_json()["data"]["id"]
    client.post(f"/notes/{nid}/publish")
    r1 = client.post(f"/notes/{nid}/favorite").get_json()["data"]
    assert r1 == {"favorited": True, "count": 1}
    r2 = client.post(f"/notes/{nid}/favorite").get_json()["data"]
    assert r2 == {"favorited": False, "count": 0}

def test_favorite_requires_login_and_published(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    draft = client.post("/notes", json={"title": "草稿", "content_md": "x"}).get_json()["data"]["id"]
    client.post("/auth/logout")
    assert client.post(f"/notes/{draft}/favorite").status_code == 401
    register(client, "bob", "b@e.com"); login(client, "b@e.com")
    assert client.post(f"/notes/{draft}/favorite").status_code == 404
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_favorites.py -q`
  - Expected: 通过。

**Security/Boundary Notes:** 唯一约束 `UNIQUE(user_id, note_id)` 是幂等的最后防线；接口不回传谁收藏了，只回传计数与自己的状态。

**Visual Verification:** 未收藏（描边爱心）与已收藏（实心 `--heart`）两态截图；点击后计数即时更新且页面不刷新；键盘 Tab 可聚焦并用 Enter 切换，`aria-pressed` 随之变化。

---

## Task 2: 个人主页

**Goal:** `/u/<username>` 展示公开资料与「笔记 / 收藏」两个 tab，且永不泄露草稿。

**Files:**
- Create: `app/templates/user/profile.html`、`app/static/css/pages/user.css`
- Modify: `app/blueprints/user.py`（实现 `/u/<username>`）、`app/__init__.py`（注册 `user` 蓝图）
- Test: `tests/test_profile.py`

**Steps:**
- [x] 写 `user.py`：`@bp.get('/u/<username>')` → 按 `username` 查用户，不存在 404 → `tab = request.args.get('tab', 'notes')`；`notes` 查该用户 `status=='published'` 笔记（`published_at desc`，每页 10）；`favorites` 查该用户收藏且笔记仍为 `published` 的笔记（按收藏时间倒序，每页 10）；渲染资料卡 + tab。
- [x] 写 `profile.html`：资料卡（头像或首字母圆底、用户名、简介、注册时间、笔记数/收藏数）；两个 tab 链接 `?tab=notes` / `?tab=favorites`，当前项 `aria-current="page"`；两个空状态：
  - 笔记 tab 空：「{{ user.username }} 还没有发布任何笔记。」
  - 收藏 tab 空：「你还没有收藏任何笔记。看到喜欢的，点一下那颗心。」（访问他人主页时改为：「{{ user.username }} 还没有收藏任何笔记。」）
- [x] 写用例：

```python
def test_profile_hides_drafts_and_shows_published(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    pub = client.post("/notes", json={"title": "已发布标题", "content_md": "x"}).get_json()["data"]["id"]
    client.post(f"/notes/{pub}/publish")
    client.post("/notes", json={"title": "草稿标题", "content_md": "x"})
    client.post("/auth/logout"); register(client, "bob", "b@e.com"); login(client, "b@e.com")
    html = client.get("/u/alice").get_data(as_text=True)
    assert "已发布标题" in html and "草稿标题" not in html and "a@e.com" not in html

def test_profile_favorites_tab_and_empty_copy(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    assert "你还没有收藏任何笔记。看到喜欢的，点一下那颗心。" in client.get("/u/alice?tab=favorites").get_data(as_text=True)
    assert "还没有发布任何笔记" in client.get("/u/alice").get_data(as_text=True)

def test_unknown_user_is_404(client):
    assert client.get("/u/nobody").status_code == 404
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_profile.py -q`
  - Expected: 通过；页面不含邮箱。

**Security/Boundary Notes:** `User.to_dict()` 白名单字段是防止邮箱外泄的关键；收藏 tab 需过滤掉已删除或转为非发布态的笔记。

**Visual Verification:** 1440×900 与 390×844 下资料卡与 tab 不溢出；两个空状态文案正确；他人主页不出现草稿标题或邮箱。

---

## Phase Completion Checklist

- [x] 所有任务完成
- [x] `.venv\Scripts\python.exe -m pytest -q` 全绿
- [x] 收藏在详情页、卡片、个人主页三处状态一致
- [x] 个人主页截图核对通过（记入 `visual-check.md`）
- [x] 可以进入 Phase 7
