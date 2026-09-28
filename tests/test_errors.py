def test_unknown_route_returns_chinese_json(client):
    res = client.get("/api/not-exist")
    assert res.status_code == 404
    body = res.get_json()
    assert body["code"] == "ERR_NOT_FOUND"
    assert "不存在" in body["message"]


def test_unknown_page_returns_html_with_exit(client):
    res = client.get("/no-such-page")
    assert res.status_code == 404
    html = res.get_data(as_text=True)
    assert "回到主页" in html


def test_csrf_blocks_write_without_token(app):
    app.config["CSRF_ENABLED"] = True
    res = app.test_client().post("/auth/register", json={"username": "a"})
    assert res.status_code == 403
    assert res.get_json()["code"] == "ERR_CSRF"


def test_csrf_allows_write_with_token(app):
    app.config["CSRF_ENABLED"] = True
    client = app.test_client()
    page = client.get("/about")
    assert page.status_code == 200
    token = None
    for line in page.get_data(as_text=True).splitlines():
        if 'name="csrf-token"' in line:
            token = line.split('content="')[1].split('"')[0]
    assert token
    res = client.post("/auth/register", json={"username": "a"}, headers={"X-CSRF-Token": token})
    assert res.get_json()["code"] != "ERR_CSRF"


def test_generic_500_hides_stack(app):
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.get("/_boom")
    def boom():
        raise RuntimeError("secret detail")

    res = app.test_client().get("/_boom")
    assert res.status_code == 500
    assert b"secret detail" not in res.data
    assert "服务器开小差了" in res.get_data(as_text=True)
