"""统一响应信封：{code, message, data}。所有接口都必须经这里返回。"""
from flask import jsonify

CODES = {
    "OK": (200, "操作成功"),
    "ERR_VALIDATION": (400, "请求参数不合法"),
    "ERR_EMAIL_TAKEN": (409, "该邮箱已被注册"),
    "ERR_USERNAME_TAKEN": (409, "该用户名已被使用"),
    "ERR_BAD_CREDENTIALS": (401, "邮箱或密码不正确"),
    "ERR_UNAUTHORIZED": (401, "请先登录"),
    "ERR_FORBIDDEN": (403, "你没有权限执行该操作"),
    "ERR_CSRF": (403, "页面已过期，请刷新后重试"),
    "ERR_SHARE_PASSWORD": (403, "密码不正确，请重试"),
    "ERR_NOT_FOUND": (404, "内容不存在或已被删除"),
    "ERR_SHARE_REVOKED": (410, "该分享链接已失效或已被作者取消"),
    "ERR_FILE_TYPE": (415, "仅支持 JPG、PNG、GIF、WebP 图片"),
    "ERR_FILE_TOO_LARGE": (413, "图片不能超过 2 MB"),
    "ERR_SERVER": (500, "服务器开小差了，请稍后再试"),
}


def ok(data=None, message=None, status=200):
    body = {"code": "OK", "message": message or CODES["OK"][1], "data": data if data is not None else {}}
    return jsonify(body), status


def fail(code, message=None, fields=None, status=None):
    default_status, default_message = CODES.get(code, (400, "请求失败"))
    body = {
        "code": code,
        "message": message or default_message,
        "data": {"fields": fields} if fields else {},
    }
    return jsonify(body), status or default_status
