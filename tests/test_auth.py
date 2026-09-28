from helpers import login, register


def test_register_then_login(client, app):
    res = register(client, "alice", "A@Example.com")
    assert res.get_json()["code"] == "OK"

    from app.models import User
    with app.app_context():
        user = User.query.filter_by(email="a@example.com").one()
        assert user.password_hash != "Passw0rd!"
        assert user.password_hash.startswith("scrypt:")

    assert client.post("/auth/logout").get_json()["code"] == "OK"
    assert login(client, "a@example.com").get_json()["code"] == "OK"


def test_duplicate_email_returns_409_with_field(client):
    register(client, "alice", "a@e.com")
    res = client.post("/auth/register", json={
        "username": "bob", "email": "A@E.com",
        "password": "Passw0rd!", "password_confirm": "Passw0rd!",
    })
    assert res.status_code == 409
    assert res.get_json()["code"] == "ERR_EMAIL_TAKEN"
    assert "已被注册" in res.get_json()["message"]
    assert "email" in res.get_json()["data"]["fields"]


def test_duplicate_username_and_mismatch_and_weak_password(client):
    register(client, "alice", "a@e.com")

    dup = client.post("/auth/register", json={
        "username": "alice", "email": "b@e.com",
        "password": "Passw0rd!", "password_confirm": "Passw0rd!",
    })
    assert dup.get_json()["code"] == "ERR_USERNAME_TAKEN"

    mismatch = client.post("/auth/register", json={
        "username": "carol", "email": "c@e.com",
        "password": "Passw0rd!", "password_confirm": "other",
    })
    assert mismatch.get_json()["code"] == "ERR_VALIDATION"
    assert "password_confirm" in mismatch.get_json()["data"]["fields"]

    weak = client.post("/auth/register", json={
        "username": "dave", "email": "d@e.com",
        "password": "abcdefgh", "password_confirm": "abcdefgh",
    })
    assert weak.get_json()["code"] == "ERR_VALIDATION"
    assert "password" in weak.get_json()["data"]["fields"]

    bad_email = client.post("/auth/register", json={
        "username": "erin", "email": "not-an-email",
        "password": "Passw0rd!", "password_confirm": "Passw0rd!",
    })
    assert bad_email.status_code == 400
    assert "email" in bad_email.get_json()["data"]["fields"]

    bad_name = client.post("/auth/register", json={
        "username": "x", "email": "f@e.com",
        "password": "Passw0rd!", "password_confirm": "Passw0rd!",
    })
    assert bad_name.status_code == 400
    assert "username" in bad_name.get_json()["data"]["fields"]


def test_login_failure_message_is_generic(client):
    register(client, "alice", "a@e.com")
    res = client.post("/auth/login", json={"email": "a@e.com", "password": "wrong"})
    assert res.status_code == 401
    assert res.get_json()["message"] == "邮箱或密码不正确"
    assert res.get_json()["data"].get("fields") is None

    unknown = client.post("/auth/login", json={"email": "nobody@e.com", "password": "wrong"})
    assert unknown.get_json()["message"] == "邮箱或密码不正确"


def test_login_accepts_uppercase_email(client):
    register(client, "alice", "a@e.com")
    res = client.post("/auth/login", json={"email": "A@E.COM", "password": "Passw0rd!"})
    assert res.get_json()["code"] == "OK"


def test_logged_in_redirects_away_from_auth_pages(client):
    register(client, "alice", "a@e.com")
    login(client)
    assert client.get("/login").status_code == 302
    assert client.get("/register").status_code == 302
