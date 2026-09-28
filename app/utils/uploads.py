"""上传校验：白名单扩展名 + 魔术字节 + 体积，uuid 重命名落盘。"""
import uuid
from pathlib import Path

ALLOWED_EXT = {"jpg": "jpg", "jpeg": "jpg", "png": "png", "gif": "gif", "webp": "webp"}
MAX_BYTES = 2 * 1024 * 1024


def sniff_image(header: bytes):
    """按文件头判定真实类型，返回扩展名或 None。"""
    if header.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
        return "gif"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    return None


def save_image(file_storage, folder):
    """保存图片，返回 (相对 URL, 错误码)；成功时错误码为 None。"""
    filename = file_storage.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXT:
        return None, "ERR_FILE_TYPE"

    stream = file_storage.stream
    header = stream.read(12)
    stream.seek(0)
    detected = sniff_image(header)
    if detected is None or detected != ALLOWED_EXT[ext]:
        return None, "ERR_FILE_TYPE"

    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(0)
    if size > MAX_BYTES:
        return None, "ERR_FILE_TOO_LARGE"

    target_dir = Path(folder)
    target_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ALLOWED_EXT[ext]}"
    file_storage.save(target_dir / name)
    return f"/static/uploads/{name}", None
