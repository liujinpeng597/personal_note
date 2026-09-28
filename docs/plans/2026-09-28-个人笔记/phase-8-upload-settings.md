# Phase 8: 图片上传与设置

**Goal:** 编辑器可上传图片并插入正文；设置页可改资料与密码。
**Prerequisites:** Phase 4 完成（编辑器）；Phase 1 完成（`utils/uploads.py` 待实现）。
**Deliverables:** `POST /api/upload`；编辑器插入图片；`/settings` 资料与密码两张表单。

**Interface Decisions Implemented:** 编辑器工具栏「插入图片」按钮与上传中状态；`ERR_FILE_TYPE`、`ERR_FILE_TOO_LARGE`、`ERR_VALIDATION` 三条中文提示；设置页表单布局与字段错误态；头像「图片 URL 或首字母圆底」两种形态。

---

## Task 1: 图片上传

**Goal:** 只接受真实图片、限 2 MB、uuid 命名、拒绝 SVG，返回可用 URL。

**Files:**
- Create: `app/utils/uploads.py`
- Modify: `app/blueprints/notes.py`（追加 `POST /api/upload`）、`app/templates/notes/editor.html`（上传按钮与 input[type=file]）、`app/static/js/editor.js`（上传与插入 Markdown）
- Test: `tests/test_upload.py`

**Steps:**
- [x] 写 `app/utils/uploads.py`：

```python
ALLOWED_EXT = {"jpg", "jpeg", "png", "gif", "webp"}
MAGIC = {b"\xff\xd8\xff": "jpg", b"\x89PNG\r\n\x1a\n": "png", b"GIF87a": "gif", b"GIF89a": "gif"}
# WebP: b"RIFF" + 4 字节长度 + b"WEBP"

def sniff_image(stream) -> str | None:
    """读取前 12 字节判定真实类型，返回扩展名或 None（无法识别）。"""

def save_image(file_storage, folder) -> tuple[str, str]:
    """校验扩展名、魔术字节、体积（由 MAX_CONTENT_LENGTH 兜底）；
    通过则 uuid4 命名落盘，返回 (相对 URL, 文件名)；失败返回 (None, 错误码)。"""
```

  - 明确拒绝 `svg`（不在 `ALLOWED_EXT`，且魔术字节不匹配任何图片类型）。

- [x] 在 `notes.py` 追加 `POST /api/upload`（`@api_login_required`）：取 `request.files.get('file')`；无文件 → `fail('ERR_VALIDATION', '请选择要上传的图片')`；类型不符 → `fail('ERR_FILE_TYPE')`；超限（模型校验兜底）→ `fail('ERR_FILE_TOO_LARGE')`；成功 → `ok({'url': '/static/uploads/<uuid>.<ext>'}, '图片已上传', status=201)`。
- [x] 编辑器工具栏加 `<input type="file" accept="image/png,image/jpeg,image/gif,image/webp" hidden>` + 「插入图片」按钮；`editor.js` 监听选择 → 上传期间按钮文案「上传中…」并禁用 → 成功后依据 `selectionStart` 在正文插入 `![图片](/static/uploads/xxx.png)` 并刷新预览 → 失败时保留原内容。
- [x] 写用例：

```python
import io

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
def test_upload_valid_png(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    r = client.post("/api/upload", data={"file": (io.BytesIO(PNG), "a.png")},
                    content_type="multipart/form-data")
    assert r.status_code == 201 and r.get_json()["data"]["url"].startswith("/static/uploads/")

def test_upload_rejects_fake_and_svg(client):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    fake = client.post("/api/upload", data={"file": (io.BytesIO(b"not an image"), "a.png")},
                       content_type="multipart/form-data")
    assert fake.status_code == 415 and fake.get_json()["code"] == "ERR_FILE_TYPE"
    svg = client.post("/api/upload", data={"file": (io.BytesIO(b"<svg onload=alert(1)/>"), "a.svg")},
                      content_type="multipart/form-data")
    assert svg.status_code == 415

def test_upload_requires_login(client):
    r = client.post("/api/upload", data={"file": (io.BytesIO(PNG), "a.png")},
                    content_type="multipart/form-data")
    assert r.status_code == 401

def test_upload_rejects_oversize(client, app):
    register(client, "alice", "a@e.com"); login(client, "a@e.com")
    big = PNG + b"\x00" * (3 * 1024 * 1024)
    r = client.post("/api/upload", data={"file": (io.BytesIO(big), "big.png")},
                    content_type="multipart/form-data")
    assert r.status_code == 413 and r.get_json()["code"] == "ERR_FILE_TOO_LARGE"
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_upload.py -q`
  - Expected: 通过；`app/static/uploads/` 下生成 uuid 命名文件，文件名不含原始名。
- [x] 确认 `.gitignore` 已忽略 `app/static/uploads/`，且 `create_app()` 会创建该目录。

**Security/Boundary Notes:** 绝不信任 `filename` 与 `Content-Type`（用扩展名 + 魔术字节双重判定）；uuid 重命名切断路径穿越与覆盖；不生成缩略图（YAGNI）；上传目录不参与模板渲染。

**Visual Verification:** 上传中按钮状态、成功后正文插入图片且预览立即显示；390×844 下工具栏不换行溢出。

---

## Task 2: 设置页

**Goal:** 可改用户名/简介/头像与密码，错误就地中文提示。

**Files:**
- Create: `app/templates/user/settings.html`
- Modify: `app/blueprints/user.py`（`GET /settings`、`POST /settings/profile`、`POST /settings/password`）、`app/static/js/notes.js` 或新增 `app/static/js/settings.js`、`app/templates/base.html`（引入）
- Test: `tests/test_settings.py`

**Steps:**
- [x] `GET /settings`（`@login_required`）：渲染两张表单（资料 / 修改密码），资料表单回填当前用户。
- [x] `POST /settings/profile`：`username` 3–20 字且唯一（与他人冲突 → `ERR_USERNAME_TAKEN`）；`bio` ≤ 200 字；`avatar_url` 为空或必须以 `http://` / `https://` 开头（否则 `ERR_VALIDATION`，message「头像地址必须以 http:// 或 https:// 开头」）；成功 `ok({'user': ...}, '资料已更新')`。
- [x] `POST /settings/password`：`old_password` 必须匹配（否则 `fail('ERR_BAD_CREDENTIALS', '原密码不正确')`）；`new_password` ≥ 8 位且含字母与数字；`new_password_confirm` 一致；成功后更新哈希并 `session.clear()` 保留 `user_id`（避免用户被登出）→ `ok(message='密码已修改')`。
- [x] `settings.js`：两张表单分别走 `request()`，错误字段标红，成功后 toast 并刷新用户信息区域。
- [x] 写用例：

```python
def test_update_profile_validations(client):
    client.post("/auth/register", json={"username": "alice", "email": "a@e.com",
                                        "password": "Passw0rd!", "password_confirm": "Passw0rd!"})
    assert client.post("/settings/profile", json={"bio": "你好", "avatar_url": ""}).get_json()["code"] == "OK"
    bad = client.post("/settings/profile", json={"avatar_url": "javascript:alert(1)"})
    assert bad.status_code == 400 and "http" in bad.get_json()["message"]
    too_long = client.post("/settings/profile", json={"bio": "字" * 201})
    assert too_long.status_code == 400 and "bio" in too_long.get_json()["data"]["fields"]

def test_username_conflict_on_profile(client, app):
    client.post("/auth/register", json={"username": "alice", "email": "a@e.com",
                                        "password": "Passw0rd!", "password_confirm": "Passw0rd!"})
    other = app.test_client()
    other.post("/auth/register", json={"username": "bob", "email": "b@e.com",
                                       "password": "Passw0rd!", "password_confirm": "Passw0rd!"})
    taken = client.post("/settings/profile", json={"username": "bob"})
    assert taken.get_json()["code"] == "ERR_USERNAME_TAKEN"

def test_change_password(client):
    client.post("/auth/register", json={"username": "alice", "email": "a@e.com",
                                        "password": "Passw0rd!", "password_confirm": "Passw0rd!"})
    wrong = client.post("/settings/password", json={"old_password": "wrong", "new_password": "Newpass1", "new_password_confirm": "Newpass1"})
    assert wrong.get_json()["code"] == "ERR_BAD_CREDENTIALS" and wrong.get_json()["message"] == "原密码不正确"
    weak = client.post("/settings/password", json={"old_password": "Passw0rd!", "new_password": "short", "new_password_confirm": "short"})
    assert weak.status_code == 400
    ok_res = client.post("/settings/password", json={"old_password": "Passw0rd!", "new_password": "Newpass1", "new_password_confirm": "Newpass1"})
    assert ok_res.get_json()["code"] == "OK"
    client.post("/auth/logout")
    assert client.post("/auth/login", json={"email": "a@e.com", "password": "Newpass1"}).get_json()["code"] == "OK"
    assert client.post("/auth/login", json={"email": "a@e.com", "password": "Passw0rd!"}).status_code == 401
```

  - 断言细节：`bio` 超长与 `avatar_url` 协议不符都必须通过 `data.fields` 定位到字段；改密码后旧密码登录必须 401。

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_settings.py -q`
  - Expected: 通过；改密码后旧密码失效、新密码可登录、当前会话仍有效。

**Security/Boundary Notes:** 头像 URL 必须限制协议（防 `javascript:` 与 `data:`）；改名后旧会话不受影响（session 存 id 而非用户名）；改密码不强制登出但也不明文回显。

**Visual Verification:** `/settings` 在 1440×900 与 390×844 下两张表单分区清晰、错误就地显示、Tab 顺序正确。

---

## Phase Completion Checklist

- [x] 所有任务完成
- [x] `.venv\Scripts\python.exe -m pytest -q` 全绿
- [x] 上传目录被 `.gitignore` 忽略且不进入版本库
- [x] 设置页截图核对通过（记入 `visual-check.md`）
- [x] 可以进入 Phase 9
