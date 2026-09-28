# 视觉核对记录（visual-check）

**执行日期：** 2026-09-28
**工具：** Microsoft Edge `--headless=new` 截图 + 页面内 JavaScript 布局测量（www.example 无外部依赖，全部本机 `127.0.0.1`）
**结论：** 6 处视觉/交互缺陷已发现并修复并复验；以下逐项记录证据。

## 一、测量方法

1. 用 Flask test client 以演示账号登录，抓取各页面 HTML，落到临时快照文件（`/static/` 绝对路径不变）。
2. 快照经本机开发服务器以 HTTP 提供（`file://` 在本机被浏览器拒绝），供无头浏览器渲染。
3. 页面内脚本测量 `scrollWidth/clientWidth`、关键元素包围盒、`getComputedStyle`、文本行宽（Range API），用 `--dump-dom` 取回。
4. 截图后用 `--force-device-scale-factor=1` 复核。

**本机工具坑（记录以免误判）：** 本机 Windows 显示缩放约 125%，`--window-size=390,844` 时页面的真实 CSS 视口是 **492×702**（由 `probe.html` 实测：`innerWidth=492 dpr=1`），直接截图会被裁切，看起来像"溢出"。移动端验收改用 390×844 的 iframe 包裹页抓图，测量页也用 iframe 固定宽度，避免该假象。

## 二、测量结果（修复后）

| 页面 | 视口 | 关键测量 | 结论 |
|------|------|----------|------|
| 主页 | 390×844 | `scrollWidth=clientWidth=390`；`.hero__copy` 390×523；h1 342 宽 @x24；副标题两行 336px / 160px | 无横向溢出，文案不压照片主体 |
| 主页 | 1000×800 | `.hero__copy` 480 宽；h1 @x40 | 平板断点生效 |
| 主页 | 1440×900 | `.hero` 1425×720；`.hero__copy` 520 宽；h1 @x64 | Hero 高度封顶 720px |
| 笔记详情 | 390×844 | `.paper` = 12,81 351×457；`.prose` 305 宽；`.comments` 343 宽 | 纸张留边、正文不贴毛边 |
| 笔记详情 | 1440×900 | `.paper` 760 宽居中（left=333）；`.prose` 630 宽 | 与设计契约一致（≤760、居中） |
| 笔记列表 | 390×844 | `.note-grid` 单列 342 宽；`.note-card` 342×154 | 移动端单列 |
| 编辑器 | 390×844 | `.editor` 327×658；写作/预览切换可见 | 窄屏切换生效 |
| 全部登录页 | 390×844 | `.nav-toggle` display:flex 位于 x=308；`.site-nav` 抽屉 `visibility:hidden` | 移动端抽屉收敛 |
| 全部登录页 | ≥768 | `.nav-toggle` display:none；`.site-nav` 内联可见 | 桌面端不出现汉堡按钮 |

## 三、发现的问题与修复

| # | 现象 | 根因 | 修复 | 复验 |
|---|------|------|------|------|
| 1 | 头像下拉菜单在页面加载时就展开（挡住内容） | `.user-menu__panel { display: flex }` 盖过 UA 的 `[hidden] { display: none }` | `base.css` 增加全局 `[hidden] { display: none !important; }` | `.user-menu__panel` display:none（三种视口） |
| 2 | 移动端 Hero 标题/按钮被压成极低对比度（几乎看不清） | `.hero::after` 的浅色遮罩绘制在 `.hero__copy` **之上**（同为定位元素且伪元素在后） | `.hero__copy { z-index: 1 }` | 390 宽截图中标题、副标题、按钮均清晰可读 |
| 3 | 移动端 Hero 文案框宽 520px 溢出视口，文字被切 | `.hero__copy` 用 `max-width: 520px`，绝对定位下不会收缩到视口内 | 改为 `max-width: min(520px, 100%)`（1023 断点同理 `min(480px,100%)`） | `.hero__copy` 390 宽；h1 342 宽；`scrollWidth=clientWidth=390` |
| 4 | 390 宽下纸张顶到屏幕两边、正文贴着手撕毛边 | `.paper` 移动端仍用 `margin: 32px auto` 与 `7%` 内边距 | 移动端 `.paper { margin: 16px 12px; padding: 26px 22px }`、`.comments { margin: 24px 16px }` | `.paper` = 12,81 351×457，两侧各有 12px 留白 |
| 5 | 列表卡片摘要露出 Markdown 记号（`##`、`|`、`---`、`**`） | 摘要直接截断 `content_md` 原文 | `Note.excerpt` 改用 `_plain_text()`：去代码块/图片/链接语法、块级标记、表格分隔与强调符 | 摘要为纯文本（`test_card_excerpt_strips_markdown_noise`） |
| 6 | 详情页正文重复标题 | 演示数据正文里又写了一遍 `# 标题` | `app/demo.py` 去掉正文首行的标题 | 复截图后纸张内只有一个标题 |
| 7 | **登录用户在详情页/分享页看到"登录后可以评论"而不是评论框；自己的评论没有"删除"按钮** | `{% from ... import comments_section %}` 默认不传递模板上下文，宏内 `current_user` 为 undefined | 两处导入改为 `with context` | 新增 3 条测试先 RED（3 failed）后 GREEN（84 passed 全绿） |

## 四、截图清单（本次实际抓取）

| 路由 | 视口 | 文件（临时目录，已清理） |
|------|------|--------------------------|
| `/` | 1440×900 / 390×844(iframe) | home-desktop / mobile-frame-home |
| `/about` | 1440×900 | about-desktop |
| `/register` | 1440×900 | register-desktop |
| `/notes` 有内容 | 1440×900 / 390×844(iframe) | notes-list-desktop / mobile-frame-list |
| `/notes` 空状态 | 1440×900 | notes-empty-desktop |
| `/notes/<id>` | 1440×900 / 390×844(iframe) | detail-desktop / mobile-frame-detail |
| `/notes/<id>/edit` | 1440×900 / 390×844 | editor-desktop / editor-mobile |
| `/u/demo` | 1440×900 | profile-desktop |
| `/settings` | 1440×900 / 390×844 | settings-desktop / settings-mobile |
| `/s/<token>`（含密码页） | 1440×900 / 390×844 | share-desktop / share-mobile |

## 五、未执行的可视化/交互核对（需人工在真实浏览器完成）

- 键盘走查全流程（Tab 顺序、焦点环、弹窗 Esc 与焦点归还）、对比度取色器实测、系统"减少动态效果"开关前后的目视对比。
- JS 交互链路：toast 显示与消失、确认弹窗、分享弹窗复制到剪贴板、上传中按钮态、编辑器实时预览与脏数据离开提醒。这些的**服务端行为**已有测试覆盖，但浏览器内的实际交互未逐一点验。
- 1024×768 视口截图与 Firefox / Safari 跨浏览器核对。
- 真实屏幕阅读器与触摸设备验证。

以上均不影响功能正确性，作为后续人工验收项保留。
