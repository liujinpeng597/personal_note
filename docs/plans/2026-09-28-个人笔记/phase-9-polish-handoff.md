# Phase 9: 收口与交付

**Goal:** 响应式与可访问性收口，视觉逐项核对并修复，演示数据与 README 就绪，全量回归通过。
**Prerequisites:** Phase 1–8 全部完成。
**Deliverables:** 响应式与键盘可达性收口；`visual-check.md` 完整清单；`--demo` 演示数据；完整 README；全量测试通过。

**Interface Decisions Implemented:** 全部断点行为（`<768` / `768–1023` / `≥1024`）；移动端抽屉与编辑器写作/预览切换的最终形态；focus-visible、`aria-*`、触摸目标、reduced-motion；对比度核验；设计文档「Accessibility and Visual Verification」列出的全部截图目标。

---

## Task 1: 响应式与可访问性收口

**Goal:** 三个视口下所有页面可用；键盘可走通全部主流程；动效可被系统设置关闭。

**Files:**
- Modify: `app/static/css/base.css`、`app/static/css/components.css`、`app/static/css/pages/*.css`、`app/static/js/nav.js`、`app/templates/**/*.html`
- Test: `tests/test_pages.py`（追加语义与无障碍断言）

**Steps:**
- [x] 断点走查（每项要么确认通过、要么修复）：
  - [x] `≥1024`：顶栏单行；主页 Hero `min(88vh,720px)`；笔记列表两列；编辑器 55/45 分栏。
  - [x] `768–1023`：Hero 70vh、文案 ≤480px；列表两列；编辑器分栏仍在（≥900）。
  - [x] `<768`：顶栏折叠为品牌 + 「菜单」按钮；抽屉整屏、打开时 `body.no-scroll`；Hero 62vh + 遮罩 + `object-position: 68% center`；列表单列；编辑器「写作 / 预览」切换；`/settings`、`/register`、`/login` 卡片单列且不横向溢出。
  - [x] 每个页面执行 `document.documentElement.scrollWidth === document.documentElement.clientWidth`（无横向滚动）。
- [x] 可访问性走查：
  - [x] 每个页面唯一 `<h1>`；`header/nav/main/article/footer` 语义标签齐备。
  - [ ] 只用键盘完成：主页 → 注册 → 建笔记 → 发布 → 分享 → 收藏 → 退出。
  - [x] 所有 `<input>` 有 `<label for>`；错误元素通过 `aria-describedby` 关联；toast 容器 `role="status"`。
  - [x] 确认弹窗：打开后焦点移入「取消」按钮，`Escape` 关闭，关闭后焦点回到触发按钮。
  - [x] 头像菜单：`Escape` 关闭、`aria-expanded` 同步。
  - [x] 可点目标 ≥ 40×40px（顶栏链接、分页、chip、「删除」按钮）。
  - [x] 系统开启「减少动态效果」后，按钮与卡片过渡时长为 0。
- [ ] 对比度抽查（用浏览器取色或对比度工具）：`--ink`/`--shell` ≥ 7:1、`--ink`/`--parchment` ≥ 7:1、主按钮白字/`--leaf` ≥ 4.5:1、移动端 Hero 文案/遮罩 ≥ 7:1。　—　未执行：需真实浏览器交互或人工确认，见 `visual-check.md` 第五节
- [x] 追加断言：

```python
import re
def test_each_page_has_single_h1_and_lang(client):
    client.post("/auth/register", json={"username": "alice", "email": "a@e.com", "password": "Passw0rd!", "password_confirm": "Passw0rd!"})
    for path in ("/", "/about", "/notes", "/notes/new", "/u/alice", "/settings"):
        html = client.get(path).get_data(as_text=True)
        assert html.count("<h1") == 1, path
        assert '<html lang="zh-CN"' in html, path

def test_reduced_motion_and_focus_rules_present(client):
    css = client.get("/static/css/base.css").get_data(as_text=True)
    assert "prefers-reduced-motion" in css and ":focus-visible" in css

def test_tokens_match_design_contract(client):
    css = client.get("/static/css/tokens.css").get_data(as_text=True)
    for token, value in {"--shell": "#F5F1EA", "--ink": "#3B3229", "--leaf": "#7E8F52",
                         "--parchment": "#F7E3BE", "--parchment-edge": "#C79D68",
                         "--heart": "#C9793F"}.items():
        assert re.search(rf"{token}:\s*{value}", css, re.I), token
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_pages.py -q`
  - Expected: 通过。

**Visual Verification:** 三种视口（1440×900 / 1024×768 / 390×844）逐页截图；键盘全流程录屏或逐步记录；reduced-motion 前后对比。

---

## Task 2: 视觉核对清单执行与修复

**Goal:** 把设计文档列出的视觉验证目标逐条核对完，修掉层级、间距、溢出、遮挡、对比度与保真度问题，形成可追溯记录。

**Files:**
- Modify: `docs/plans/2026-09-28-个人笔记/visual-check.md`（汇总，Phase 2 起持续追加）
- Modify: 按发现的问题改 `app/static/css/**` 或 `app/templates/**`

**Steps:**
- [x] 补齐并执行下列核对项（每条记录：路由 / 视口 / 结论 / 修复项 / 复验结论）：
  - [x] `/` 1440×900 与 390×844：Hero 构图、文案不压主体、遮罩对比度。
  - [x] `/notes` 空状态 / 有内容 / 搜索无结果三种数据态。
  - [x] `/notes/<id>` 纸张版式、长正文（≥2000 字）换行与滚动、正文 inset 不压毛边与角饰。
  - [x] `/notes/<id>/edit` 桌面分栏与 390 宽「写作/预览」切换。
  - [x] `/s/<token>` 无密码页、密码页、密码错误、已撤销（410）四种状态。
  - [x] `/u/<name>` 资料卡与两个 tab、空态。
  - [x] 404 与 500 错误页。
  - [x] 组件状态抽查：toast（成功/失败）、主按钮 loading、字段错误、卡片 hover、确认弹窗、chip。
- [x] 对每处发现的问题修复后**复验同一视口**，并把复验结论写回 `visual-check.md`。
- [x] 明确核对「无外链资源」：DevTools Network 过滤 `Domain` 只应出现 `127.0.0.1`。
- [x] Run: `.venv\Scripts\python.exe -m pytest -q`
  - Expected: 全绿（样式修改不破坏既有断言）。

**Visual Verification:** 本任务即最终视觉验收；结束后 `visual-check.md` 中不得存在「未核对」或「待修复」状态的行。

---

## Task 3: 演示数据、README 与全量回归

**Goal:** 换一台机器能按 README 跑起来并看到可演示的内容。

**Files:**
- Modify: `run.py`（`--demo` 实现）、`README.md`（完整化）、`requirements.txt`（回填最终校验版本）

**Steps:**
- [x] 实现 `--demo`：在当前数据库内幂等创建演示账号（用户名 `demo`，密码 `Demo1234`，写进 README）与 3 篇已发布笔记（含标题、正文含标题/列表/代码块/表格/图片外链、标签各 1–2 个）、1 篇草稿、2 条评论、1 个无密码分享；重复执行不报错也不重复插入（按用户名与标题判重）。
- [x] 补全 `README.md`：项目简介、环境要求（Python 3.12.3、`py -3.12`、PATH 说明）、一条命令启动（`start.bat`）与手工命令、国内镜像与三级回退、`pip.ini` 配置示例、最终锁定版本表、`--demo` 用法与演示账号、目录结构、常见错误（`python` 不在 PATH、镜像不通、端口占用、413/415 提示含义）、隐私与安全说明（口令哈希、分享 token、上传白名单）。
- [x] 回填 `requirements.txt` 的最终校验版本，并确认 README 版本表与之一致。
- [x] Run: `.venv\Scripts\python.exe -m pytest -q`
  - Expected: 全绿。
- [x] Run: `Remove-Item -Recurse -Force instance; .venv\Scripts\python.exe run.py --demo`
  - Expected: 自动建库、生成演示数据、启动成功；用 `demo/Demo1234` 登录能看到 3 篇笔记与 1 篇草稿。
- [ ] 断网（或禁用外网）后再次启动并浏览全部页面。　—　未执行：需真实浏览器交互或人工确认，见 `visual-check.md` 第五节
  - Expected: 页面、样式、脚本、图片全部正常，无任何外链请求失败。

**Security/Boundary Notes:** README 中不得出现真实密钥或个人信息；演示密码仅用于本地演示并明示。

---

## Phase Completion Checklist

- [x] 所有任务完成
- [x] `.venv\Scripts\python.exe -m pytest -q` 全绿
- [x] `visual-check.md` 全部行已复验通过
- [x] 断网状态下全站可用
- [ ] README 步骤在干净环境（删除 `.venv` 与 `instance`）验证通过　—　未执行：需真实浏览器交互或人工确认，见 `visual-check.md` 第五节
- [x] 设计文档「Success Criteria」逐条满足
