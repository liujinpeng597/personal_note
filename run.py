"""开发服务器入口。

    python run.py            正常启动
    python run.py --demo     先写入演示数据再启动
    flask --app run init-db  只建表
"""
import sys

from app import create_app
from app.extensions import db

app = create_app()


def _run_demo():
    from app.demo import seed_demo_data

    with app.app_context():
        db.create_all()
        created = seed_demo_data()
        print(f"演示数据已就绪（新增 {created} 条笔记）")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _run_demo()
    app.run(debug=True, port=5000)
