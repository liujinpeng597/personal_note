import io

from helpers import login, register

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def _upload(client, content, filename):
    return client.post("/api/upload", data={"file": (io.BytesIO(content), filename)},
                       content_type="multipart/form-data")


def test_upload_valid_png(client, app):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    res = _upload(client, PNG, "a.png")
    assert res.status_code == 201
    url = res.get_json()["data"]["url"]
    assert url.startswith("/static/uploads/")
    assert url.endswith(".png")


def test_upload_rejects_fake_and_svg(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")

    fake = _upload(client, b"not an image", "a.png")
    assert fake.status_code == 415
    assert fake.get_json()["code"] == "ERR_FILE_TYPE"

    svg = _upload(client, b"<svg onload=alert(1)/>", "a.svg")
    assert svg.status_code == 415

    mismatch = _upload(client, b"GIF89a" + b"\x00" * 20, "a.png")
    assert mismatch.status_code == 415, "扩展名与真实类型不一致也必须拒绝"


def test_upload_requires_login(client):
    res = _upload(client, PNG, "a.png")
    assert res.status_code == 401


def test_upload_without_file(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    res = client.post("/api/upload", data={}, content_type="multipart/form-data")
    assert res.status_code == 400
    assert res.get_json()["code"] == "ERR_VALIDATION"


def test_upload_rejects_oversize(client):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    big = PNG + b"\x00" * (3 * 1024 * 1024)
    res = _upload(client, big, "big.png")
    assert res.status_code == 413
    assert res.get_json()["code"] == "ERR_FILE_TOO_LARGE"


def test_uploaded_file_is_renamed(client, app):
    register(client, "alice", "a@e.com")
    login(client, "a@e.com")
    url = _upload(client, PNG, "original-name.png").get_json()["data"]["url"]
    assert "original-name" not in url
    assert len(url.rsplit("/", 1)[-1].split(".")[0]) == 32
