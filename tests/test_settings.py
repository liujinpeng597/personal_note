from helpers import login, register


def test_update_profile_validations(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")

    ok_res = client.post("/settings/profile", json={"bio": "你好", "avatar_url": ""})
    assert ok_res.get_json()["code"] == "OK"
    assert ok_res.get_json()["data"]["user"]["bio"] == "你好"

    bad_scheme = client.post("/settings/profile", json={"avatar_url": "javascript:alert(1)"})
    assert bad_scheme.status_code == 400
    assert "http" in bad_scheme.get_json()["message"]

    too_long = client.post("/settings/profile", json={"bio": "字" * 201})
    assert too_long.status_code == 400
    assert "bio" in too_long.get_json()["data"]["fields"]


def test_username_conflict_on_profile(client, app):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")

    other = app.test_client()
    other.post("/auth/register", json={"username": "bob", "email": "b@e.com",
                                       "password": "Passw0rd!", "password_confirm": "Passw0rd!"})

    taken = client.post("/settings/profile", json={"username": "bob"})
    assert taken.get_json()["code"] == "ERR_USERNAME_TAKEN"

    renamed = client.post("/settings/profile", json={"username": "alice2"})
    assert renamed.get_json()["code"] == "OK"
    assert renamed.get_json()["data"]["user"]["username"] == "alice2"


def test_change_password(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")

    wrong = client.post("/settings/password", json={
        "old_password": "wrong", "new_password": "Newpass1", "new_password_confirm": "Newpass1"})
    assert wrong.get_json()["code"] == "ERR_BAD_CREDENTIALS"
    assert wrong.get_json()["message"] == "原密码不正确"

    weak = client.post("/settings/password", json={
        "old_password": "Passw0rd!", "new_password": "short", "new_password_confirm": "short"})
    assert weak.status_code == 400

    mismatch = client.post("/settings/password", json={
        "old_password": "Passw0rd!", "new_password": "Newpass1", "new_password_confirm": "Newpass2"})
    assert mismatch.status_code == 400

    ok_res = client.post("/settings/password", json={
        "old_password": "Passw0rd!", "new_password": "Newpass1", "new_password_confirm": "Newpass1"})
    assert ok_res.get_json()["code"] == "OK"

    client.post("/auth/logout")
    assert client.post("/auth/login", json={"email": "a@e.com", "password": "Newpass1"}).get_json()["code"] == "OK"
    client.post("/auth/logout")
    assert client.post("/auth/login", json={"email": "a@e.com", "password": "Passw0rd!"}).status_code == 401


def test_settings_requires_login_for_writes(client):
    assert client.post("/settings/profile", json={"bio": "x"}).status_code == 401
    assert client.post("/settings/password", json={"old_password": "x"}).status_code == 401
