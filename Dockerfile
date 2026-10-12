# 个人笔记 —— 容器镜像
#
# 基础镜像走 DaoCloud 镜像源：本机实测 Docker Hub（registry-1.docker.io）直连超时，
# 而 docker.m.daocloud.io 可正常拉取。若你的网络能直连 Docker Hub，可把下面一行换成
#   FROM python:3.12-slim
FROM docker.m.daocloud.io/library/python:3.12-slim

# pip 源：国内镜像优先，构建时可用
#   docker build --build-arg PIP_INDEX_URL=https://pypi.org/simple .
# 覆盖
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Shanghai

WORKDIR /app

# 依赖单独成层：只要 requirements 不变，改代码不会重装依赖
COPY requirements.txt requirements-prod.txt ./
RUN pip install --no-cache-dir -i "$PIP_INDEX_URL" -r requirements-prod.txt

COPY . .

# 以非 root 运行；instance/ 与 uploads/ 预先建好并授权，
# 这样 Docker 命名卷首次挂载时会继承正确的属主
RUN useradd --create-home --shell /usr/sbin/nologin --uid 10001 appuser \
    && mkdir -p /app/instance /app/app/static/uploads \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# 健康检查不依赖 curl（slim 镜像里没有），直接用 Python 请求 /about
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/about', timeout=3).status == 200 else 1)"

# 启动前先建表（幂等），再交给 gunicorn。
# -w 1 --threads 8：SQLite 是单文件库，多进程并发写容易 database is locked，
# 因此用单进程多线程；要横向扩容请先换成 PostgreSQL。
CMD ["sh", "-c", "flask --app wsgi init-db && exec gunicorn --bind 0.0.0.0:8000 --workers 1 --threads 8 --timeout 60 --access-logfile - --error-logfile - wsgi:app"]
