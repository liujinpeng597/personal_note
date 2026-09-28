# Phase 2: 主页 Hero 主视觉

**Goal:** 把 `个人笔记主页.jpg` 落成主页 Hero，按设计稿把标题与按钮放在照片左侧留白，并完成本项目的第一次视觉评审。
**Prerequisites:** Phase 1 完成（`base.html`、tokens、components、`main` 蓝图、`/about` 可用）。
**Deliverables:** 可访问的主页：Hero 摄影图 + 四功能简介 + 页脚；`static/img/hero-desk.jpg`；`pages/home.css`；移动端与桌面端两张核对截图。

**Interface Decisions Implemented:** 主页 Hero 布局（照片整幅铺满、`object-position: right center`、文案左侧 `max-width: 520px`）；Hero 文案「把想法，留在纸上」与其副标题、主/次按钮；四功能简介 2×2 网格；页脚；响应式断点 `<768` / `768–1023` / `≥1024` 中的 Hero 规则；移动端遮罩对比度规则；Hero 图片 alt 文案；主页断言的零外链资源。

---

## Task 1: 素材落地与主页实现

**Goal:** 主页在桌面与移动端都呈现设计稿的构图，文案不遮挡照片主体。

**Files:**
- Create: `app/static/img/hero-desk.jpg`（由素材复制）
- Create: `app/templates/main/home.html`、`app/static/css/pages/home.css`
- Modify: `app/blueprints/main.py`（注册 `/`）、`app/templates/partials/header.html`（品牌链接指向 `/`）
- Test: `tests/test_pages.py`（追加主页用例）

**Steps:**
- [x] 复制素材，不改内容：

```powershell
Copy-Item '个人笔记主页.jpg' 'app\static\img\hero-desk.jpg'
```

  - Expected: `app/static/img/hero-desk.jpg` 存在，尺寸 2560×1440。

- [x] 写 `main.py` 的 `home` 视图：`@bp.get('/')`，渲染 `main/home.html`，传入 `features`（四项：写笔记 / Markdown 排版 / 一键分享 / 评论与收藏，各含内联 SVG 名称与一句中文说明）。
- [x] 写 `home.html`：

```html
<section class="hero">
  <img class="hero__photo" src="{{ url_for('static', filename='img/hero-desk.jpg') }}"
       alt="清晨书桌上的咖啡杯、花瓶与摊开的笔记本">
  <div class="hero__copy">
    <h1>把想法，留在纸上</h1>
    <p class="hero__sub">一个属于你自己的安静角落，写下来，藏起来，或者只分享给一个人。</p>
    <div class="hero__actions">
      <a class="btn btn-primary" href="{{ url_for('auth.register_page') }}">开始记录</a>
      <a class="btn btn-ghost" href="#features">了解更多</a>
    </div>
  </div>
</section>
<section id="features" class="features">…四张功能说明…</section>
```

  - `auth.register_page` 由 Phase 3 提供：本阶段临时写 `href="/register"`，Phase 3 T2 换成 `url_for`。

- [x] 写 `pages/home.css`：

```css
.hero { position: relative; height: min(88vh, 720px); overflow: hidden; }
.hero__photo { width: 100%; height: 100%; object-fit: cover; object-position: right center; display: block; }
.hero__copy { position: absolute; inset-block: 0; left: 0; display: flex; flex-direction: column;
  justify-content: center; gap: 16px; max-width: 520px; padding-inline: 64px; }
.hero h1 { font-size: 44px; line-height: 1.3; color: var(--ink); }
@media (max-width: 1023px) { .hero { height: 70vh; } .hero__copy { max-width: 480px; padding-inline: 40px; } .hero h1 { font-size: 32px; } }
@media (max-width: 767px) {
  .hero { height: 62vh; }
  .hero__photo { object-position: 68% center; }
  .hero::after { content: ""; position: absolute; inset: 0;
    background: linear-gradient(rgba(245,241,234,.92), rgba(245,241,234,.72)); }
  .hero__copy { padding-inline: 24px; }
  .hero h1 { font-size: 28px; }
}
.features { display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; padding: 64px; }
@media (max-width: 767px) { .features { grid-template-columns: 1fr; padding: 32px 24px; } }
```

- [x] 在 `base.html` 的样式引入里加入 `pages/home.css`，并给 `<body>` 增加 `page-home` 类以便页面级样式隔离。
- [x] 追加主页用例到 `tests/test_pages.py`：

```python
def test_home_hero_and_features(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "img/hero-desk.jpg" in html
    assert "把想法，留在纸上" in html
    assert html.count('alt="清晨书桌上的咖啡杯、花瓶与摊开的笔记本"') == 1
    for label in ("写笔记", "Markdown", "分享", "评论"):
        assert label in html
    assert "© 2026" in html
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_pages.py -q`
  - Expected: 通过。
- [x] Run: `.venv\Scripts\python.exe run.py`，浏览器打开 `http://127.0.0.1:5000/`
  - Expected: Hero 铺满首屏，标题在左、照片主体（杯子/花瓶/笔记本/绿叶）完整可见。

**Security/Boundary Notes:** 照片用 `<img>` 而非 CSS 背景，以保留 alt 文本；`static/img/` 只放项目素材，上传文件一律走 `static/uploads/`。

**Visual Verification:**
- 1440×900：文案块左对齐、不越过照片中线，杯子与笔记本不被文字覆盖。
- 390×844：遮罩生效、标题 28px、文案与照片有足够对比；「开始记录」「了解更多」触摸目标 ≥ 40px。
- DevTools Network：只有本机 `127.0.0.1` 请求，无字体/CDN/图床请求。

---

## Task 2: 主页视觉核对与迭代

**Goal:** 用设计文档的文案与构图逐条核对，修掉层级、间距、溢出、遮挡问题。

**Files:**
- Modify: `app/static/css/pages/home.css`、`app/templates/main/home.html`（按发现的问题）

**Steps:**
- [x] 按设计文档「关键文案」逐条核对主页：标题「把想法，留在纸上」、副标题「一个属于你自己的安静角落，写下来，藏起来，或者只分享给一个人。」、按钮「开始记录」「了解更多」、页脚「关于 · 技术栈 · © 2026」。
- [x] 逐项检查并修复（每项都要么确认通过、要么改样式）：
  - [x] 文案最长一行不超出 `max-width`，不出横向滚动条（`document.documentElement.scrollWidth === clientWidth`）。
  - [x] 1024×768、1280×800、1440×900、1920×1080 四个宽度下 Hero 高度不超过 `720px`。
  - [x] 390×844 下标题不被截断（`hero__copy` 有上下留白，且不压到汉堡按钮）。
  - [x] 页码对比度：Hero 文案 `--ink` 在移动端遮罩上目视清晰；`--ink-soft` 的功能说明文字在 `--shell` 上可读。
  - [x] 「从主页点到关于页再返回」路径通畅（页脚链接与顶栏品牌都可点）。
- [x] 记录核对结果到 `docs/plans/2026-09-28-个人笔记/visual-check.md`（一张表：路由 / 视口 / 结论 / 修复项）。
- [x] Run: `.venv\Scripts\python.exe -m pytest -q`
  - Expected: 全绿（本阶段不引入回归）。

**Visual Verification:** 本任务本身就是视觉验证任务，产出 `visual-check.md` 的第一批记录；`visual-check.md` 在 P9 T2 汇总为完整清单。

---

## Phase Completion Checklist

- [x] 所有任务完成
- [x] 主页桌面与移动端截图核对通过，无横向溢出、无遮挡主体
- [x] `visual-check.md` 已建立并记录主页结论
- [x] 无任何外链资源请求
- [x] 可以进入 Phase 3
