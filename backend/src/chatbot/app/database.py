"""SQLAlchemy 引擎与会话工厂。

create_all 只创建**缺失**的表（checkfirst 默认 True），
绝不 DROP、不 TRUNCATE，所以已有数据不会丢。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from chatbot.app.models import Base


def build_engine(db_path: str | Path) -> Engine:
    """按路径创建引擎并确保表存在；也支持 ":memory:"。"""
    if str(db_path) == ":memory:":
        # 内存库：所有会话必须共用一个连接，否则每个连接都是一个空库
        engine = create_engine(
            "sqlite://",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
    else:
        engine = create_engine(
            f"sqlite:///{Path(db_path)}",
            connect_args={"check_same_thread": False},
        )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection: sqlite3.Connection, _record: object) -> None:
        # PRAGMA 是连接级设置，每次新建连接都要重新执行
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    # 只建缺失的表；已有表和数据原样保留
    Base.metadata.create_all(engine)
    return engine
