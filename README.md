# 个人笔记

一个安静的个人写作角落：注册登录、Markdown 写作、草稿与发布、分享（可加密码、可撤销）、评论与收藏。
主页使用 `个人笔记主页.jpg` 作 Hero 主视觉，笔记正文使用 `个人笔记-笔记背景.jpg` 作纸张底色；全站不依赖任何外链图片、字体或 CDN。

技术栈：**Python 3.12 + Flask 3 + SQLite + 原生 HTML / CSS / JavaScript**（Jinja2 服务端渲染页面，写操作就近提供 JSON 接口）。

## 快速开始（一条命令）

```
双击 start.bat
```

它会依次：用 `py -3.12` 建虚拟环境 → 按国内镜像安装依赖（失败自动回退阿里云镜像、再回退 pypi.org）→ 建库 → 启动服务。
启动后浏览器打开 <http://127.0.0.1:5000>。

## 手工启动（等价步骤）

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
.venv\Scripts\python.exe -m flask --app run init-db
.venv\Scripts\python.exe run.py
```

> 本机注意：`python` 与 `pip` 没有加入 PATH，请始终用 `py -3.12` 或 `.venv\Scripts\python.exe` 调用。

### 镜像说明

`requirements.txt` 里的版本已锁定。安装前可用下面命令确认某个版本在目标镜像上是否可用：

```powershell
.venv\Scripts\python.exe -m pip index versions Flask -i https://pypi.tuna.tsinghua.edu.cn/simple
```

若某个 `==` 版本在镜像上不存在，取该包**最新可用补丁版**，并同步更新 `requirements.txt` 与本文件的版本表。

想永久使用镜像，可写 `%APPDATA%\pip\pip.ini`：

```ini
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
```

实测记录：本机访问 `pypi.org` 正常，清华镜像曾出现无响应；遇到安装卡住可直接省略 `-i` 走 pypi.org。

## 依赖版本

| 包 | 版本 |
|----|------|
| Flask | 3.0.3 |
| Flask-SQLAlchemy | 3.1.1 |
| SQLAlchemy | 2.0.36 |
| Markdown | 3.7 |
| nh3 | 0.2.18 |
| pytest（开发） | 8.3.3 |

以上版本均已在本机实际安装验证通过。

## 演示数据

```powershell
.venv\Scripts\python.exe run.py --demo
```

会幂等地创建演示账号（用户名 `demo`，密码 `Demo1234`）、3 篇已发布笔记、1 篇草稿、2 条评论、1 个收藏和 1 个分享链接。
不执行 `--demo` 时数据库是空的，注册自己的账号即可。

## 测试

```powershell
.venv\Scripts\python.exe -m pytest -q
```

覆盖：注册登录、越权（一律 404）、草稿/发布、分享与密码解锁与撤销、评论权限、收藏幂等、标签与搜索、上传白名单与体积、CSRF、Markdown XSS 消毒、统一中文错误信封、页面结构与无障碍规则。

## 容器化部署（Docker / WSL2）

前置：Docker Desktop（本机已装：引擎 29.8.0，WSL2 后端，Compose v5.5.1）。

```powershell
docker compose up -d --build      # 构建并后台启动
docker compose logs -f web        # 查看日志
docker compose down               # 停止（数据卷保留）
```

访问 <http://127.0.0.1:8000>。容器内 gunicorn 监听 8000，想换宿主机端口用 `APP_PORT=5000 docker compose up -d`。

### 关于镜像源（本机实测结论）

Docker Hub 直连在本机**不可用**（`registry-1.docker.io:443` 连接超时），所以：

- `Dockerfile` 的基础镜像写作 `docker.m.daocloud.io/library/python:3.12-slim`，已实测可拉取、可运行；
- 若你的网络能直连 Docker Hub，把那一行换成 `FROM python:3.12-slim` 即可；
- 想让**默认写法**（如 `docker pull python:3.12-slim`）也能通，在 Docker Desktop → Settings → Docker Engine 里加：

```json
{
  "registry-mirrors": ["https://docker.m.daocloud.io"]
}
```

保存后引擎会自动重启。第三方镜像源存在供应链风险，请自行评估；阿里云 ACR 专属加速器（形如 `xxx.mirror.aliyuncs.com`）更可信，但需要你的账号在控制台获取地址。

构建时的 pip 源默认走清华镜像，可覆盖：
`docker compose build --build-arg PIP_INDEX_URL=https://pypi.org/simple`

### 数据持久化

两个命名卷，容器重建不丢数据：

| 卷 | 容器内挂载点 | 内容 |
|---|---|---|
| `notes_instance` | `/app/instance` | SQLite 数据库 `notes.db` + 自动生成的会话密钥 `secret_key` |
| `notes_uploads` | `/app/app/static/uploads` | 用户上传的图片 |

备份与恢复（卷名前缀为 compose 项目名，即目录名 `personal_node`，可用 `docker volume ls` 核对）：

```powershell
docker run --rm -v personal_node_notes_instance:/data -v "${PWD}:/backup" alpine tar czf /backup/notes-backup.tar.gz -C /data .
docker run --rm -v personal_node_notes_instance:/data -v "${PWD}:/backup" alpine sh -c "rm -rf /data/* && tar xzf /backup/notes-backup.tar.gz -C /data"
```

### 在容器里写演示数据

```powershell
docker compose exec web flask --app wsgi seed-demo
```

### 生产注意事项

- 容器内跑的是 gunicorn（不是 Flask 开发服务器），没有开 debug；
- **刻意用单进程多线程**（`-w 1 --threads 8`）：SQLite 是多进程并发写会 `database is locked`，要横向扩容请先迁移到 PostgreSQL；
- `NOTES_SECRET_KEY` 留空时由应用在数据卷内生成并持久化；多副本部署必须显式设置同一个值，否则各副本之间会话不互通；
- HTTPS、反向代理、定时备份不在本期范围。

## 目录结构

```
run.py                  本地开发入口（--demo 写演示数据）
wsgi.py                 容器入口（gunicorn wsgi:app）
config.py               配置：密钥、SQLite、上传限制、CSRF 开关
start.bat               一键启动（Windows 本地）
Dockerfile              容器镜像：python:3.12-slim + gunicorn + 非 root
docker-compose.yml      单机编排：端口、环境变量、两个数据卷
.dockerignore           构建上下文排除（.venv / instance / uploads / 源素材 / tests）
requirements.txt        运行依赖（锁定）
requirements-prod.txt   上者 + gunicorn（容器用）
app/
  __init__.py           应用工厂（含 init-db / seed-demo 两个 CLI 命令）
  models.py             7 张表
  demo.py               演示数据
  blueprints/           main / auth / notes / share / user
  utils/                responses（统一信封）/ security（登录与 CSRF）/ markdown_render / uploads / tags
  templates/            base.html + 各页面 + partials
  static/               css（tokens / base / components / pages）、js、img（两张素材）、uploads（运行时）
tests/                  pytest 用例
docs/plans/             实施计划与视觉核对记录
```

## 两条硬性规范

1. 后端统一返回 `{"code": "...", "message": "中文提示"}`，前端展示 message 中的中文提示；失败时字段级错误在 `data.fields`。
2. 依赖使用国内镜像安装并在 `requirements.txt` 中锁定版本。

## 隐私与安全

- 密码只存 scrypt 哈希；登录失败不区分账号是否存在。
- 笔记默认私有，只有分享链接能让别人看到；草稿不可分享。
- 分享 token 由 `secrets.token_urlsafe(16)` 生成，取消分享后立即失效（410）。
- 所有写请求校验 CSRF token；越权访问他人资源一律返回 404。
- Markdown 经服务端渲染后由 nh3 白名单消毒；评论按纯文本存储与输出。
- 上传只接受 JPG / PNG / GIF / WebP，校验文件头且限制 2 MB，uuid 重命名落盘。

## 常见问题

| 现象 | 原因与处理 |
|------|------------|
| `python : 无法将“python”项识别为...` | `python` 不在 PATH，改用 `py -3.12` 或 `.venv\Scripts\python.exe` |
| 安装依赖很慢或卡住 | 镜像不可达，去掉 `-i` 走 pypi.org，或改用阿里云镜像 |
| 端口 5000 被占用 | 修改 `run.py` 里的 `port`，或用 `netstat -ano \| findstr 5000` 找到进程 |
| 页面提示「图片不能超过 2 MB」 | 上传限制 2 MB，改 `config.py` 的 `MAX_CONTENT_LENGTH` 可放宽 |
| 忘记 `demo` 密码 | 删除 `instance/notes.db` 后重新执行 `--demo` |

## 清空数据

```powershell
Remove-Item -Recurse -Force instance
```

会同时清掉数据库与自动生成的会话密钥；上传的图片在 `app\static\uploads\`。
