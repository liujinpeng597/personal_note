"""SQLAlchemy 实例，独立模块以避免循环导入。"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
