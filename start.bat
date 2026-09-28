@echo off
setlocal
cd /d %~dp0

if not exist .venv (
  echo [1/4] creating virtualenv with Python 3.12 ...
  py -3.12 -m venv .venv
)

.venv\Scripts\python.exe -c "import flask" 2>nul
if errorlevel 1 (
  echo [2/4] installing dependencies ...
  .venv\Scripts\python.exe -m pip install -r requirements-dev.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  if errorlevel 1 (
    echo [2/4] mirror failed, retry with aliyun ...
    .venv\Scripts\python.exe -m pip install -r requirements-dev.txt -i https://mirrors.aliyun.com/pypi/simple/
  )
  if errorlevel 1 (
    echo [2/4] mirror failed, retry with pypi.org ...
    .venv\Scripts\python.exe -m pip install -r requirements-dev.txt
  )
)

echo [3/4] initializing database ...
.venv\Scripts\python.exe -m flask --app run init-db

echo [4/4] starting http://127.0.0.1:5000
.venv\Scripts\python.exe run.py
