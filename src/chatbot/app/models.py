"""SQLAlchemy 2.x ORM 模型：会话与消息。

表名、列名、类型与第四次作业的建表语句（db.py 里的 SCHEMA）完全一致，
所以可以直接读取已有的 chat.db，不需要迁移数据。
"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """声明式基类，所有模型都继承它。"""


class Session(Base):
    """会话表。"""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    created_at: Mapped[str] = mapped_column(Text, server_default=text("(datetime('now'))"))
    updated_at: Mapped[str] = mapped_column(Text, server_default=text("(datetime('now'))"))

    # 一个会话对应多条消息；删会话时 ORM 也会删掉它的消息
    messages: Mapped[list[Message]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.id",
    )


class Message(Base):
    """消息表。"""

    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_messages_role"),
        Index("idx_messages_session", "session_id", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        Text, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, server_default=text("(datetime('now'))"))

    session: Mapped[Session] = relationship(back_populates="messages")
