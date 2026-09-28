# Phase 3: 认证与会话

**Goal:** 注册、登录、退出全链路可用；顶栏按登录态切换；表单错误以中文就地提示且不丢输入。
**Prerequisites:** Phase 1 完成（信封、CSRF、安全装饰器、`base.html`）；Phase 2 完成（主页可作为登录后的默认落地页）。
**Deliverables:** `/auth/register`、`/auth/login`、`/auth/logout` 三个接口与两个页面；`partials/field.html` 字段宏；`auth.js`；顶栏登录态与移动端抽屉。

**Interface Decisions Implemented:** 注册/登录页面版式与字段级错误态；主按钮 loading 态（「注册中…」「登录中…」）；顶栏已登录/未登录两种形态与「写笔记」主按钮；头像菜单（个人主页/设置/退出）；移动端抽屉与 `aria-expanded`；`ERR_EMAIL_TAKEN`、`ERR_USERNAME_TAKEN`、`ERR_BAD_CREDENTIALS`、`ERR_UNAUTHORIZED` 四条中文提示。

---

## Task 1: 认证接口与口令处理

**Goal:** 三个接口按信封返回，校验完备，口令只以哈希形式落库。

**Files:**
- Create: `app/blueprints/auth.py`
- Modify: `app/utils/security.py`（追加 `current_user()` 与模板上下文注册）、`config.py`（追加 `DEFAULT_LANDING_ENDPOINT = 'main.home'`）、`app/__init__.py`（注册蓝图）
- Test: `tests/test_auth.py`

**Steps:**
- [x] 在 `app/utils/security.py` 追加：

```python
def current_user():
    from app.models import User
    uid = session.get('user_id')
    return db.session.get(User, uid) if uid else None

def register_template_context(app):
    @app.context_processor
    def inject_user():
        return {'current_user': current_user()}
```

- [x] 在 `config.py` 追加 `DEFAULT_LANDING_ENDPOINT = 'main.home'`（Phase 4 T3 改为 `'notes.list'`）。
- [x] 写 `app/blueprints/auth.py`：
  - `_validate_username(u)`：`re.fullmatch(r'[\w\u4e00-\u9fa5]{3,20}', u)`。
  - `_validate_email(e)`：`re.fullmatch(r'[^@\s]+@[^@\s]+\.[A-Za-z]{2,}', e)`，存储与查重前 `e.strip().lower()`。
  - `_validate_password(p)`：长度 ≥ 8 且同时含字母与数字。
  - `POST /auth/register`：逐字段校验 → `fail('ERR_VALIDATION', fields={...})`；邮箱查重 → `ERR_EMAIL_TAKEN`；用户名查重 → `ERR_USERNAME_TAKEN`；写入 `generate_password_hash(password)`（默认 scrypt）；`session['user_id'] = user.id`；返回 `ok({'user': user.to_dict()}, '注册成功', status=201)`。
  - `POST /auth/login`：按小写邮箱查用户 → `check_password_hash` 失败或用户不存在 → 一律 `fail('ERR_BAD_CREDENTIALS')`；成功写 session 并返回 `ok({'user': ..., 'redirect': url_for(app.config['DEFAULT_LANDING_ENDPOINT'])})`。
  - `POST /auth/logout`：`session.clear()` → `ok(message='已退出登录')`。
  - `GET /login`、`GET /register`：已登录时 302 到 `url_for(app.config['DEFAULT_LANDING_ENDPOINT'])`；否则渲染页面并保留 `?next=`。
- [x] 写 `tests/test_auth.py`：

```python
def test_register_then_login(client, app):
    r = client.post("/auth/register", json={"username": "alice", "email": "A@Example.com",
                                            "password": "Passw0rd!", "password_confirm": "Passw0rd!"})
    assert r.status_code == 201 and r.get_json()["code"] == "OK"
    from app.models import User
    with app.app_context():
        u = User.query.filter_by(email="a@example.com").one()
        assert u.password_hash != "Passw0rd!" and u.password_hash.startswith("scrypt:")
    assert client.post("/auth/logout").get_json()["code"] == "OK"
    assert client.post("/auth/login", json={"email": "a@example.com", "password": "Passw0rd!"}).get_json()["code"] == "OK"

def test_duplicate_email_returns_409_with_field(client):
    client.post("/auth/register", json={"username": "alice", "email": "a@e.com", "password": "Passw0rd!", "password_confirm": "Passw0rd!"})
    r = client.post("/auth/register", json={"username": "bob", "email": "A@E.com", "password": "Passw0rd!", "password_confirm": "Passw0rd!"})
    assert r.status_code == 409
    assert r.get_json()["code"] == "ERR_EMAIL_TAKEN" and "已被注册" in r.get_json()["message"]

def test_duplicate_username_and_mismatch_and_weak_password(client):
    client.post("/auth/register", json={"username": "alice", "email": "a@e.com", "password": "Passw0rd!", "password_confirm": "Passw0rd!"})
    assert client.post("/auth/register", json={"username": "alice", "email": "b@e.com", "password": "Passw0rd!", "password_confirm": "Passw0rd!"}).get_json()["code"] == "ERR_USERNAME_TAKEN"
    r = client.post("/auth/register", json={"username": "carol", "email": "c@e.com", "password": "Passw0rd!", "password_confirm": "other"})
    assert r.get_json()["code"] == "ERR_VALIDATION" and "password_confirm" in r.get_json()["data"]["fields"]
    assert client.post("/auth/register", json={"username": "dave", "email": "d@e.com", "password": "abcdefgh", "password_confirm": "abcdefgh"}).get_json()["code"] == "ERR_VALIDATION"
    bad_email = client.post("/auth/register", json={"username": "erin", "email": "not-an-email", "password": "Passw0rd!", "password_confirm": "Passw0rd!"})
    assert bad_email.status_code == 400 and "email" in bad_email.get_json()["data"]["fields"]
    bad_name = client.post("/auth/register", json={"username": "x", "email": "f@e.com", "password": "Passw0rd!", "password_confirm": "Passw0rd!"})
    assert bad_name.status_code == 400 and "username" in bad_name.get_json()["data"]["fields"]

def test_login_failure_message_is_generic(client):
    client.post("/auth/register", json={"username": "alice", "email": "a@e.com", "password": "Passw0rd!", "password_confirm": "Passw0rd!"})
    client.post("/auth/logout")
    r = client.post("/auth/login", json={"email": "a@e.com", "password": "wrong"})
    assert r.status_code == 401 and r.get_json()["message"] == "邮箱或密码不正确"
    assert r.get_json().get("data", {}).get("fields") is None
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_auth.py -q`
  - Expected: 全部通过；哈希前缀为 `scrypt:`；登录失败文案固定且不暴露字段。

**Security/Boundary Notes:** 口令永不打日志、不进 `to_dict()`；查重前统一小写邮箱；登录失败不区分账号是否存在。

---

## Task 2: 注册与登录页面

**Goal:** 两个页面在站点外壳内可用，字段错误就地标红，提交时按钮进入 loading 态。

**Files:**
- Create: `app/templates/auth/register.html`、`app/templates/auth/login.html`、`app/templates/partials/field.html`、`app/static/js/auth.js`、`app/static/css/pages/auth.css`
- Modify: `app/blueprints/auth.py`（`register_page`、`login_page` 视图）、`app/templates/base.html`（引入 `pages/auth.css`、`auth.js`）
- Test: `tests/test_pages.py`（追加页面结构断言）

**Steps:**
- [x] 写 `partials/field.html` 宏 `field(name, label, type='text', autocomplete='', hint='')`：输出 `<label for>`、`<input id name type autocomplete aria-describedby>`、`<p class="field-error" id="{{ name }}-error" hidden></p>`。
- [x] 写 `auth/register.html`：四个字段（邮箱、用户名、密码、确认密码）+ 「注册」主按钮 + 「已有账号？去登录」。`<h1>注册</h1>`。
- [x] 写 `auth/login.html`：邮箱、密码 + 「登录」主按钮 + 「还没有账号？去注册」。`<h1>登录</h1>`。
- [x] 写 `auth.js`：

```js
async function submitAuth(form) {
  const btn = form.querySelector('button[type=submit]');
  const original = btn.textContent;
  form.querySelectorAll('.field-error').forEach(el => { el.hidden = true; el.textContent = ''; });
  btn.disabled = true; btn.textContent = form.dataset.loadingText;
  const data = Object.fromEntries(new FormData(form).entries());
  const res = await request(form.action, { method: 'POST', body: data });
  btn.disabled = false; btn.textContent = original;
  if (res.code === 'OK') { location.href = res.data.redirect || form.dataset.successUrl; return; }
  const fields = res.data?.fields || {};
  for (const [name, msg] of Object.entries(fields)) {
    const el = form.querySelector(`#${name}-error`);
    if (el) { el.textContent = msg; el.hidden = false; }
  }
  if (Object.keys(fields).length === 0) {
    const first = form.querySelector('input'); if (first) first.focus();
  }
}
document.querySelectorAll('form[data-auth-form]').forEach(f => f.addEventListener('submit', e => { e.preventDefault(); submitAuth(f); }));
```

- [x] `auth.css`：表单卡片居中、`max-width: 420px`、`--surface` 底、10px 圆角；错误态输入框 1px `--heart` 描边 + 错误文案 `--heart` 色。
- [x] 追加页面断言：

```python
def test_register_page_structure(client):
    html = client.get("/register").get_data(as_text=True)
    for field in ("email", "username", "password", "password_confirm"):
        assert f'id="{field}"' in html and f'for="{field}"' in html
    assert 'id="email-error"' in html and "注册" in html

def test_logged_in_redirects_away_from_login(client):
    client.post("/auth/register", json={"username": "alice", "email": "a@e.com", "password": "Passw0rd!", "password_confirm": "Passw0rd!"})
    res = client.get("/login")
    assert res.status_code == 302
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_pages.py -q`
  - Expected: 通过。
- [ ] 手工验证：邮箱重复时 `/register` 上「邮箱」下方出现「该邮箱已被注册」，输入内容保留。　—　未执行：需真实浏览器交互或人工确认，见 `visual-check.md` 第五节

**Visual Verification:** `/register` 与 `/login` 在 1440×900 与 390×844 下：卡片居中不溢出、标签与输入框对齐、错误文案出现时布局不跳动、Tab 顺序为邮箱→用户名→密码→确认密码→按钮、focus 有 2px `--leaf` 描边。

---

## Task 3: 顶栏登录态与移动端导航

**Goal:** 顶栏清楚区分登录态，移动端可展开导航，键盘可操作。

**Files:**
- Create: `app/static/js/nav.js`、`app/templates/partials/header.html`（重写为登录态分支）
- Modify: `app/static/css/components.css`（顶栏与抽屉样式）
- Test: `tests/test_pages.py`（追加顶栏断言）

**Steps:**
- [x] 重写 `header.html`：
  - 品牌 `<a href="{{ url_for('main.home') }}">个人笔记</a>`。
  - 未登录：右侧「登录」「注册」两个链接。
  - 已登录：`<a class="btn btn-primary" href="/notes/new">写笔记</a>`（Phase 4 起换成 `url_for('notes.editor_new')`）、头像菜单按钮（`aria-haspopup="menu"`、`aria-expanded="false"`）、菜单项「个人主页」「设置」「退出」（退出为 POST 表单，带 csrf 隐藏字段）。
  - 头像：`current_user.avatar_url` 存在则 `<img>`，否则首字母圆底（`--leaf` 底、`--surface` 字）。
  - `<button class="nav-toggle" aria-expanded="false" aria-controls="site-nav">菜单</button>`（<768 显示）。
- [x] 写 `nav.js`：切换 `#site-nav` 的 `.is-open` 与 `aria-expanded`；`<768` 打开抽屉时 `document.body.classList.add('no-scroll')`；头像菜单点击开合、`Escape` 关闭并把焦点还给触发按钮、点击外部关闭。
- [x] 追加断言：

```python
def test_header_anonymous_vs_logged_in(client):
    html = client.get("/").get_data(as_text=True)
    assert 'href="/login"' in html and 'href="/register"' in html and "写笔记" not in html
    client.post("/auth/register", json={"username": "alice", "email": "a@e.com", "password": "Passw0rd!", "password_confirm": "Passw0rd!"})
    html = client.get("/").get_data(as_text=True)
    assert "写笔记" in html and "alice" in html and 'aria-expanded="false"' in html
```

- [x] Run: `.venv\Scripts\python.exe -m pytest -q`
  - Expected: 全绿。
- [ ] 手工验证：登录后顶栏出现「写笔记」；菜单里「退出」能真正退出并回到未登录形态。　—　未执行：需真实浏览器交互或人工确认，见 `visual-check.md` 第五节

**Security/Boundary Notes:** 退出必须是 POST + CSRF（防被 `<img src>` 之类的 GET 请求踢下线）；头像 URL 只接受 `http/https`（Phase 8 T2 落地校验）。

**Visual Verification:** 390×844 下点「菜单」展开抽屉、`Escape` 关闭；顶栏在 1440×900 不换行；头像菜单打开时 `aria-expanded="true"`。

---

## Phase Completion Checklist

- [x] 所有任务完成
- [x] `.venv\Scripts\python.exe -m pytest -q` 全绿
- [ ] 注册→退出→登录→退出全链路手工走通　—　未执行：需真实浏览器交互或人工确认，见 `visual-check.md` 第五节
- [x] 注册/登录页面在桌面与移动端截图核对通过（记入 `visual-check.md`）
- [x] 可以进入 Phase 4
