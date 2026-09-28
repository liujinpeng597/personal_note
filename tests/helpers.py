"""测试辅助：注册与登录。各测试文件顶部 `from helpers import register, login`。"""


def register(client, username="alice", email="a@e.com", password="Passw0rd!"):
    res = client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
        "password_confirm": password,
    })
    assert res.status_code == 201, res.get_json()
    client.post("/auth/logout")
    return res


def login(client, email="a@e.com", password="Passw0rd!"):
    res = client.post("/auth/login", json={"email": email, "password": password})
    assert res.get_json()["code"] == "OK", res.get_json()
    return res
