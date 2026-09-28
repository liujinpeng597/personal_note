from helpers import login, register


def test_about_page_renders(client):
    res = client.get("/about")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'name="csrf-token"' in html
    assert "<h1>" in html


def test_home_hero_and_features(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "img/hero-desk.jpg" in html
    assert "把想法，留在纸上" in html
    assert html.count('alt="清晨书桌上的咖啡杯、花瓶与摊开的笔记本"') == 1
    for label in ("写笔记", "Markdown", "排版", "分享", "评论", "收藏"):
        assert label in html, label
    assert "© 2026" in html


def test_header_anonymous_vs_logged_in(client):
    html = client.get("/").get_data(as_text=True)
    header = html.split("</header>")[0]
    assert 'href="/login"' in header
    assert 'href="/register"' in header
    assert 'href="/notes/new"' not in header, "未登录不应出现写笔记入口"

    register(client, "alice", "a@e.com")
    login(client)
    header = client.get("/").get_data(as_text=True).split("</header>")[0]
    assert 'href="/notes/new"' in header
    assert "alice" in header
    assert 'aria-expanded="false"' in header
    assert 'action="/logout"' in header


def test_register_page_structure(client):
    html = client.get("/register").get_data(as_text=True)
    for name in ("email", "username", "password", "password_confirm"):
        assert f'id="{name}"' in html
        assert f'for="{name}"' in html
        assert f'id="{name}-error"' in html
    assert "注册" in html


def test_login_page_structure(client):
    html = client.get("/login").get_data(as_text=True)
    for name in ("email", "password"):
        assert f'id="{name}"' in html
        assert f'for="{name}"' in html
    assert "登录" in html


def test_tokens_css_matches_design_contract(client):
    res = client.get("/static/css/tokens.css")
    assert res.status_code == 200
    css = res.get_data(as_text=True)
    for token, value in {
        "--shell": "#F5F1EA",
        "--surface": "#FFFDF9",
        "--ink": "#3B3229",
        "--ink-soft": "#6F6252",
        "--brown": "#745F46",
        "--leaf": "#7E8F52",
        "--leaf-soft": "#E7EAD8",
        "--parchment": "#F7E3BE",
        "--parchment-edge": "#C79D68",
        "--heart": "#C9793F",
    }.items():
        assert token in css and value in css, token


def test_paper_uses_design_asset_and_responsive_breakpoints(client):
    components = client.get("/static/css/components.css").get_data(as_text=True)
    assert 'url("../img/paper.jpg")' in components
    assert "767px" in components, "移动端断点"
    assert "899px" in client.get("/static/css/pages/notes.css").get_data(as_text=True), "编辑器断点"
    home = client.get("/static/css/pages/home.css").get_data(as_text=True)
    assert "object-position: right center" in home
    assert "linear-gradient" in home, "移动端 Hero 遮罩"


def test_error_page_has_exit(client):
    html = client.get("/no-such-page").get_data(as_text=True)
    assert "回到主页" in html


def test_reduced_motion_and_focus_rules_present(client):
    css = client.get("/static/css/base.css").get_data(as_text=True)
    assert "prefers-reduced-motion" in css
    assert ":focus-visible" in css
    assert ".sr-only" in css


def test_each_page_has_single_h1_and_lang(client):
    register(client, "alice", "a@e.com")
    login(client)
    note_id = client.post("/notes", json={"title": "标题", "content_md": "正文"}).get_json()["data"]["id"]
    client.post(f"/notes/{note_id}/publish")
    token = client.post(f"/notes/{note_id}/share", json={}).get_json()["data"]["url"]

    for path in ("/", "/about", "/notes", "/notes/new", f"/notes/{note_id}",
                 f"/notes/{note_id}/edit", "/u/alice", "/settings"):
        html = client.get(path).get_data(as_text=True)
        assert html.count("<h1") == 1, path
        assert '<html lang="zh-CN"' in html, path

    client.post("/auth/logout")
    for path in ("/login", "/register", token):
        html = client.get(path).get_data(as_text=True)
        assert html.count("<h1") == 1, path
        assert '<html lang="zh-CN"' in html, path


def test_pages_load_no_external_resources(client):
    register(client, "alice", "a@e.com")
    login(client)
    for path in ("/", "/about", "/notes", "/notes/new", "/settings", "/u/alice"):
        html = client.get(path).get_data(as_text=True)
        for marker in ("//cdn", "googleapis", "unpkg.com", "jsdelivr", "fonts.gstatic"):
            assert marker not in html, f"{path} 引用了外部资源 {marker}"
