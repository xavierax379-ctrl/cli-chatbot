"""会话存储：SQLAlchemy ORM 实现。

所有会话读写都集中在这里，路由只调用这些方法。
一轮对话（用户消息 + 机器人回复）由 append_turn() 在同一个事务里写入，
要么都成功，要么都不写，不会留下半轮对话。
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import sessionmaker

from chatbot.app.database import build_engine
from chatbot.app.models import Message as MessageRow
from chatbot.app.models import Session as SessionRow
from chatbot.app.schemas import Message


class SessionNotFound(KeyError):
    """会话不存在。路由层会把它翻成 HTTP 404。"""


class SessionStore:
    """基于 SQLAlchemy ORM 的会话存储。"""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self._engine = build_engine(db_path)
        # expire_on_commit=False：commit 之后对象还能读属性，不用再查一次库
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)

    # ---------- 写入 ----------

    def get_or_create(self, session_id: str) -> None:
        """会话不存在就创建一个空会话。"""
        with self._session_factory() as db, db.begin():
            if db.get(SessionRow, session_id) is None:
                db.add(SessionRow(id=session_id))

    def append_turn(
        self,
        session_id: str,
        user_content: str,
        assistant_content: str,
    ) -> None:
        """把一轮对话写进同一个事务：要么两条都在，要么一条都没有。"""
        with self._session_factory() as db, db.begin():
            if db.get(SessionRow, session_id) is None:
                db.add(SessionRow(id=session_id))
            db.add(MessageRow(session_id=session_id, role="user", content=user_content))
            db.add(
                MessageRow(
                    session_id=session_id,
                    role="assistant",
                    content=assistant_content,
                )
            )
            db.execute(
                update(SessionRow)
                .where(SessionRow.id == session_id)
                .values(updated_at=func.datetime("now"))
            )

    def clear(self, session_id: str) -> None:
        """清空会话里的消息，但会话本身保留。"""
        with self._session_factory() as db, db.begin():
            if db.get(SessionRow, session_id) is None:
                raise SessionNotFound(session_id)
            db.execute(delete(MessageRow).where(MessageRow.session_id == session_id))

    # ---------- 读取 ----------

    def exists(self, session_id: str) -> bool:
        with self._session_factory() as db:
            return db.get(SessionRow, session_id) is not None

    def messages(self, session_id: str) -> list[Message]:
        """按对话顺序返回该会话的全部消息。"""
        with self._session_factory() as db:
            if db.get(SessionRow, session_id) is None:
                raise SessionNotFound(session_id)
            rows = (
                db.execute(
                    select(MessageRow)
                    .where(MessageRow.session_id == session_id)
                    .order_by(MessageRow.id)
                )
                .scalars()
                .all()
            )
            return [Message(role=row.role, content=row.content) for row in rows]

    def list_sessions(self) -> list[str]:
        with self._session_factory() as db:
            rows = db.execute(select(SessionRow.id)).scalars().all()
            return sorted(rows)

    def close(self) -> None:
        self._engine.dispose()