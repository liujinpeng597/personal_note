# Phase 1: 骨架与全局基础设施

**Goal:** 项目能启动、能建库、能启动时自建上传目录；所有接口有统一 `{code, message}` 信封与中文错误；Markdown 渲染默认安全；页面外壳已带上全部设计变量与 toast 通道。
**Prerequisites:** 无（本阶段是起点）。
**Deliverables:** 可运行的 Flask 应用骨架；`instance/notes.db` 建成；`/about` 与 404/410/500 页可访问；`pytest` 有真实用例并通过。

**Interface Decisions Implemented:** 10 个设计变量（tokens.css）；响应式断点骨架；中文错误文案与统一信封；组件状态中的 toast、按钮、字段三件套；零外链资源策略。

---

## Task 1: 环境、依赖锁定与启动脚本

**Goal:** 把本机可用的虚拟环境与锁定依赖固定下来，并让 README 的启动步骤真实可执行。

**Files:**
- Create: `requirements.txt`、`requirements-dev.txt`、`.gitignore`、`start.bat`、`README.md`（骨架，P9 补全）

**Steps:**
- [x] 写 `requirements.txt`（初值，校验后按需回填补丁版）：

```text
Flask==3.0.3
Flask-SQLAlchemy==3.1.1
SQLAlchemy==2.0.36
Markdown==3.7
nh3==0.2.18
```

- [x] 写 `requirements-dev.txt`：`-r requirements.txt` 加 `pytest==8.3.3`。
- [x] 建环境并安装：

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```
  - Expected: 全部 `Successfully installed`。
  - 若镜像无响应（本机实测清华镜像不通）：依次改用 `-i https://mirrors.aliyun.com/pypi/simple/`，最后省略 `-i` 走 pypi.org。
- [x] 若某条 `==` 版本报 `No matching distribution found`，用 `.venv\Scripts\python.exe -m pip index versions <包> -i <可用索引>` 取该包最新可用补丁版，**同时更新 `requirements.txt` 与 README 的版本表**，再重跑安装。
- [x] 写 `.gitignore`：`.venv/`、`instance/`、`app/static/uploads/`、`__pycache__/`、`.pytest_cache/`、`*.pyc`、`.env`。
- [x] 写 `start.bat`：若 `.venv` 不存在则 `py -3.12 -m venv .venv`；若 `import flask` 失败则按上表命令装依赖；执行 `flask --app run init-db`；最后 `python run.py`。
- [ ] 验证：删除 `.venv` 后双击 `start.bat`，能一路建环境、装依赖、建库并启动。　—　未执行：需真实浏览器交互或人工确认，见 `visual-check.md` 第五节
  - Expected: 控制台出现本地地址，浏览器可打开。

**Security/Boundary Notes:** 依赖必须精确锁定，不允许 `>=`；README 里不得写入真实密钥。

---

## Task 2: 应用工厂、数据模型与初始化命令

**Goal:** 应用可按配置装配，7 张表可一次建好，测试有独立临时库。

**Files:**
- Create: `config.py`、`run.py`、`app/__init__.py`、`app/extensions.py`、`app/models.py`、`tests/conftest.py`、`tests/test_models.py`

**Steps:**
- [x] 写 `config.py`：`SECRET_KEY`（环境变量 `NOTES_SECRET_KEY` → 否则读 `instance/secret_key`，不存在则 `secrets.token_urlsafe(32)` 写入）、`SQLALCHEMY_DATABASE_URI = sqlite:///<root>/instance/notes.db`、`MAX_CONTENT_LENGTH = 2 * 1024 * 1024`、`SESSION_COOKIE_HTTPONLY = True`、`SESSION_COOKIE_SAMESITE = 'Lax'`、`CSRF_ENABLED = True`、`UPLOAD_FOLDER = app/static/uploads`。
- [x] 写 `app/extensions.py`：`db = SQLAlchemy()`。
- [x] 写 `app/models.py`，7 个类/表按设计文档「数据模型」逐字段实现，关键约束：
  - `Note.status` 默认 `'draft'`，`CheckConstraint("status IN ('draft','published')")`。
  - `Favorite` 加 `UniqueConstraint('user_id','note_id')`；`Share.note_id` 加 `unique=True`；`Share.token` 加 `unique=True`。
  - `Note` 上 `tags = relationship('Tag', secondary=note_tags, backref='notes', cascade='all, delete')`，`comments`/`favorites`/`shares` 用 `cascade='all, delete-orphan'`。
  - 每个模型提供 `to_dict()`，只输出展示所需字段（`User.to_dict()` **不含** `password_hash` 与 `email`）。
- [x] 写 `app/__init__.py` 的 `create_app(config_overrides=None)`：加载配置、`db.init_app(app)`、建 `static/uploads` 目录、注册模板过滤器 `render_md`（Task 4 提供）、注册全局错误处理器（Task 3 提供）、`app.cli` 命令 `init-db`（`db.create_all()`）。
- [x] 写 `run.py`：`app = create_app()`；`__main__` 下解析 `--demo`（本阶段仅占位调用 `app.cli`，P9 T3 实现）并 `app.run(debug=True, port=5000)`。
- [x] 写 `tests/conftest.py`：

```python
import pytest
from app import create_app
from app.extensions import db as _db

@pytest.fixture()
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
    })
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()

@pytest.fixture()
def client(app):
    return app.test_client()
```

- [x] 写 `tests/test_models.py`：建一个用户 + 笔记 + 标签 + 收藏 + 评论 + 分享；删除笔记后断言 `note_tags`/`favorites`/`comments`/`shares` 均被级联清除；断言 `User.to_dict()` 不含 `password_hash`。
- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_models.py -q`
  - Expected: 通过；级联断言与字段白名单断言均为真。

**Security/Boundary Notes:** `models.py` 不写业务查询；`to_dict()` 是防止邮箱与口令哈希外泄的唯一出口，必须显式白名单字段。

---

## Task 3: 统一响应信封、错误码与安全装饰器

**Goal:** 规范一落地：所有接口经 `ok()/fail()` 返回，所有失败都带中文 `message`；写请求受 CSRF 保护；未登录与越权有统一行为。

**Files:**
- Create: `app/utils/responses.py`、`app/utils/security.py`、`app/blueprints/__init__.py`（空包标记）
- Test: `tests/test_errors.py`

**Steps:**
- [x] 写 `app/utils/responses.py`：

```python
CODES = {
    "OK": (200, "操作成功"),
    "ERR_VALIDATION": (400, "请求参数不合法"),
    "ERR_EMAIL_TAKEN": (409, "该邮箱已被注册"),
    "ERR_USERNAME_TAKEN": (409, "该用户名已被使用"),
    "ERR_BAD_CREDENTIALS": (401, "邮箱或密码不正确"),
    "ERR_UNAUTHORIZED": (401, "请先登录"),
    "ERR_FORBIDDEN": (403, "你没有权限执行该操作"),
    "ERR_CSRF": (403, "页面已过期，请刷新后重试"),
    "ERR_SHARE_PASSWORD": (403, "密码不正确，请重试"),
    "ERR_NOT_FOUND": (404, "内容不存在或已被删除"),
    "ERR_SHARE_REVOKED": (410, "该分享链接已失效或已被作者取消"),
    "ERR_FILE_TYPE": (415, "仅支持 JPG、PNG、GIF、WebP 图片"),
    "ERR_FILE_TOO_LARGE": (413, "图片不能超过 2 MB"),
    "ERR_SERVER": (500, "服务器开小差了，请稍后再试"),
}

def ok(data=None, message="操作成功", status=200): ...   # {"code":"OK","message":message,"data":data or {}}
def fail(code, message=None, fields=None, status=None): ...  # message 缺省取 CODES[code][1]
```

- [x] 写 `app/utils/security.py`：`get_csrf_token()`（session 内随机值，供模板与 `/api` 读取）、`login_required`（页面：302 到 `/login?next=`）、`api_login_required`（接口：401 `ERR_UNAUTHORIZED`）、`register_csrf(app)`（`before_request`：方法属于 `POST/PUT/PATCH/DELETE` 且 `CSRF_ENABLED` 时，比对 `X-CSRF-Token` 头或表单 `csrf_token` 字段，失败 `fail("ERR_CSRF")`）。
- [x] 在 `create_app()` 中注册 `register_csrf(app)` 与全局错误处理器：`404 → ERR_NOT_FOUND`、`410 → ERR_SHARE_REVOKED`、`413 → ERR_FILE_TOO_LARGE`、`500 → ERR_SERVER`（异常堆栈只 `app.logger.exception`）。内容协商：`request.path.startswith('/api')` 或 `request.is_json` 或 `Accept` 含 `application/json` → 返回 JSON 信封；否则渲染 `errors/404.html`、`errors/410.html`、`errors/500.html`。
- [x] 写 `tests/test_errors.py`：

```python
def test_unknown_route_returns_chinese_json(client):
    res = client.get("/api/not-exist")
    assert res.status_code == 404
    assert res.get_json()["code"] == "ERR_NOT_FOUND"
    assert "不存在" in res.get_json()["message"]

def test_csrf_blocks_write_without_token(app):
    app.config["CSRF_ENABLED"] = True
    res = app.test_client().post("/auth/register", json={"username": "a"})
    assert res.status_code == 403 and res.get_json()["code"] == "ERR_CSRF"

def test_generic_500_hides_stack(app, monkeypatch):
    @app.get("/_boom")
    def boom(): raise RuntimeError("secret detail")
    res = app.test_client().get("/_boom", headers={"Accept": "text/html"})
    assert res.status_code == 500 and b"secret detail" not in res.data
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_errors.py -q`
  - Expected: 三个用例通过；500 响应体不含 `secret detail`。

**Security/Boundary Notes:** 越权后续一律映射为 `ERR_NOT_FOUND`（P4 起使用），`ERR_FORBIDDEN` 只用于非资源类权限（如非评论作者删评论除外——按设计文档，删他人评论也返回 404）。CSRF 校验必须对所有写方法生效，包含匿名的分享解锁表单（其 csrf 值来自页面表单字段）。

---

## Task 4: Markdown 渲染与消毒

**Goal:** Markdown 只在服务端渲染一次并消毒，XSS 用例全部被拦住。

**Files:**
- Create: `app/utils/markdown_render.py`
- Test: `tests/test_markdown.py`

**Steps:**
- [x] 实现 `render_markdown(text) -> str`：`markdown.markdown(text, extensions=['extra', 'sane_lists', 'nl2br'])`，随后经 `nh3.clean(html, tags={...}, attributes={...}, url_schemes={'http','https','mailto'})`。
  - 允许标签：`p br h1 h2 h3 h4 strong em del code pre blockquote ul ol li a img table thead tbody tr th td hr`。
  - 允许属性：`a[href,title]`、`img[src,alt,title]`、`code[class]`（语言类）；**不含** `on*`、`style`、`script`、`iframe`、`svg`。
- [x] 在 `create_app()` 注册模板过滤器：`app.jinja_env.filters['render_md'] = render_markdown`。
- [x] 写 `tests/test_markdown.py`：

```python
import pytest
from app.utils.markdown_render import render_markdown

@pytest.mark.parametrize("payload", [
    "<script>alert(1)</script>",
    '<img src=x onerror=alert(1)>',
    "[x](javascript:alert(1))",
    '<a href="#" onclick="alert(1)">x</a>',
    '<iframe src="//evil"></iframe>',
])
def test_xss_is_stripped(payload):
    out = render_markdown(payload)
    assert "script" not in out.lower()
    assert "onerror" not in out.lower() and "onclick" not in out.lower()
    assert "javascript:" not in out.lower()
    assert "iframe" not in out.lower()

def test_normal_markdown_renders():
    out = render_markdown("# 标题\n\n- 一\n- 二\n\n```python\nprint(1)\n```\n\n| a | b |\n|---|---|\n| 1 | 2 |")
    assert "<h1>" in out and "<ul>" in out and "<table>" in out and "print(1)" in out
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_markdown.py -q`
  - Expected: 全部通过；正常语法用例保留标题、列表、代码块与表格。

**Security/Boundary Notes:** 这是唯一的 HTML 产出点。若 `nh3` 装不上，切换 `bleach==6.1.0` 时只改本文件的清洗调用，接口签名不变。

---

## Task 5: 页面外壳、设计变量与提示通道

**Goal:** 所有页面继承同一外壳，设计变量与组件基础样式就位，toast 与 `fetch` 封装可用，`/about` 与三个错误页可访问。

**Files:**
- Create: `app/templates/base.html`、`app/templates/main/about.html`、`app/templates/partials/header.html`、`app/templates/partials/footer.html`、`app/templates/partials/toast.html`、`app/templates/errors/404.html`、`errors/410.html`、`errors/500.html`
- Create: `app/static/css/tokens.css`、`app/static/css/base.css`、`app/static/css/components.css`
- Create: `app/static/js/request.js`、`app/static/js/toast.js`
- Create: `app/blueprints/main.py`（本阶段只注册 `/about`）
- Test: `tests/test_pages.py`

**Steps:**
- [x] 写 `tokens.css`，值必须与设计文档一致：`--shell:#F5F1EA`、`--surface:#FFFDF9`、`--ink:#3B3229`、`--ink-soft:#6F6252`、`--brown:#745F46`、`--leaf:#7E8F52`、`--leaf-soft:#E7EAD8`、`--parchment:#F7E3BE`、`--parchment-edge:#C79D68`、`--heart:#C9793F`；另加字号阶梯（44/32/28/30/22/16/13）、行高（1.3/1.7/1.9）、圆角（10px/6px/999px）、两级阴影、`--dur:150ms`。
- [x] 写 `base.css`：重置、`box-sizing`、字体栈（标题 `"Georgia","Times New Roman","Songti SC","SimSun",serif`；正文 `-apple-system,"Segoe UI","Microsoft YaHei","PingFang SC",sans-serif`）、正文 16px/1.7、`:focus-visible { outline: 2px solid var(--leaf); outline-offset: 2px }`、`@media (prefers-reduced-motion: reduce) { *,*::before,*::after { transition-duration: 0s !important; animation-duration: 0s !important } }`。**不引用任何 webfont。**
- [x] 写 `components.css`：`.btn`/`.btn-primary`/`.btn-ghost`/`.btn-danger`、`.field`/`.field-error`、`.card`/`.note-card`、`.chip`、`.badge-draft`、`.toast`、`.dialog`、`.paper`（本阶段仅定义空壳，`background-image` 在 P4 T4 接入）。所有可点目标 `min-height:40px`。
- [x] 写 `base.html`：`<meta name="csrf-token" content="{{ csrf_token() }}">`、`{% include 'partials/header.html' %}`、`<main>`、`{% include 'partials/footer.html' %}`、`<div id="toast-root" role="status" aria-live="polite"></div>`、按顺序引入 css 与 `request.js`、`toast.js`、`nav.js`（P2 提供）。每页唯一 `<h1>`。
- [x] 写 `request.js`：

```js
async function request(url, { method = 'GET', body = null } = {}) {
  const headers = { 'Accept': 'application/json' };
  if (body !== null) headers['Content-Type'] = 'application/json';
  const token = document.querySelector('meta[name="csrf-token"]')?.content;
  if (token && method !== 'GET') headers['X-CSRF-Token'] = token;
  let res;
  try {
    res = await fetch(url, { method, headers, body: body === null ? null : JSON.stringify(body) });
  } catch {
    toast('error', '网络异常，请检查连接后重试');
    return { code: 'ERR_NETWORK', message: '网络异常，请检查连接后重试' };
  }
  let payload = {};
  try { payload = await res.json(); } catch { /* 非 JSON 响应 */ }
  if (!payload.message) payload = { code: 'ERR_SERVER', message: '服务器开小差了，请稍后再试' };
  if (method !== 'GET' || res.status >= 400) {
    toast(payload.code === 'OK' ? 'success' : 'error', payload.message);
  }
  return payload;
}
```

- [x] 写 `toast.js`：`toast(type, message)` 在 `#toast-root` 内渲染一条，**新的顶掉旧的**，3 秒后移除，带关闭按钮。
- [x] 写 `partials/header.html`：本阶段只渲染品牌「个人笔记」与右侧静态链接（登录/注册的登录态切换在 P3 T3 实现）。
- [x] 写 `main.py`：`bp = Blueprint('main', __name__)`，`@bp.get('/about')` 渲染 `main/about.html`（项目说明、技术栈、两条规范）。在 `create_app()` 注册。
- [x] 写三个错误页：各含一句说明 + 出口按钮（「回到主页」/「回到我的笔记」）。
- [x] 写 `tests/test_pages.py`：

```python
def test_about_page_renders(client):
    res = client.get("/about")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'name="csrf-token"' in html and "--leaf" in client.get("/static/css/tokens.css").get_data(as_text=True)

def test_error_page_has_exit(client):
    html = client.get("/no-such-page").get_data(as_text=True)
    assert "回到主页" in html
```

- [x] Run: `.venv\Scripts\python.exe -m pytest -q`
  - Expected: 全绿（P1 全部用例）。

**Security/Boundary Notes:** `base.html` 是 CSRF token 的唯一注入点；所有页面必须继承它，禁止在页面里手写 `<html>`。
**Visual Verification:** `/about` 在 1440×900 下检查顶栏/页脚/字体栈生效；`/no-such-page` 与 `/_boom` 的错误页有无障碍出口按钮；DevTools Network 确认无第三方请求。

---

## Phase Completion Checklist

- [x] 所有任务完成
- [x] `.venv\Scripts\python.exe -m pytest -q` 全绿
- [x] `flask --app run init-db` 生成 `instance/notes.db`
- [ ] 双击 `start.bat` 能从零跑到启动　—　未执行：需真实浏览器交互或人工确认，见 `visual-check.md` 第五节
- [x] `requirements.txt` 中每个版本号都经过实际安装验证，README 版本表已同步
- [x] 可以进入 Phase 2
