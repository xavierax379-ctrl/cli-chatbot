"""会话存储：SQLite 实现。

所有会话读写都集中在这里，路由只调用这些方法。
以后换成 MySQL/PostgreSQL 时，只需要重写这个类，路由代码不用动。
"""

from __future__ import annotations

import threading
from pathlib import Path

from chatbot.app.db import connect
from chatbot.app.schemas import Message


class SessionNotFound(KeyError):
    """会话不存在。路由层会把它翻成 HTTP 404。"""


class SessionStore:
    """SQLite 会话表：sessions + messages。"""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        # RLock：messages() 里可能要复用 exists()，普通 Lock 会被自己锁死
        self._lock = threading.RLock()
        self._conn = connect(db_path)

    # ---------- 写入 ----------

    def get_or_create(self, session_id: str) -> None:
        """会话不存在就创建一个空会话。"""
        with self._lock:
            self._conn.execute("INSERT OR IGNORE INTO sessions (id) VALUES (?)", (session_id,))
            self._conn.commit()

    def append(self, session_id: str, role: str, content: str) -> Message:
        """追加一条消息；会话不存在时自动创建。"""
        message = Message(role=role, content=content)
        with self._lock:
            self._conn.execute("INSERT OR IGNORE INTO sessions (id) VALUES (?)", (session_id,))
            self._conn.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content),
            )
            self._conn.execute(
                "UPDATE sessions SET updated_at = datetime('now') WHERE id = ?",
                (session_id,),
            )
            self._conn.commit()
        return message

    def pop_last(self, session_id: str) -> None:
        """撤销最后一条消息（模型调用失败时，避免留下没有回复的提问）。"""
        with self._lock:
            row = self._conn.execute(
                "SELECT MAX(id) AS last_id FROM messages WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row["last_id"] is not None:
                self._conn.execute("DELETE FROM messages WHERE id = ?", (row["last_id"],))
                self._conn.commit()

    def clear(self, session_id: str) -> None:
        """清空会话里的消息，但会话本身保留。"""
        with self._lock:
            if not self.exists(session_id):
                raise SessionNotFound(session_id)
            self._conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            self._conn.commit()

    # ---------- 读取 ----------

    def exists(self, session_id: str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            return row is not None

    def messages(self, session_id: str) -> list[Message]:
        """按对话顺序返回该会话的全部消息。"""
        with self._lock:
            if not self.exists(session_id):
                raise SessionNotFound(session_id)
            rows = self._conn.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()
        return [Message(role=row["role"], content=row["content"]) for row in rows]

    def list_sessions(self) -> list[str]:
        with self._lock:
            rows = self._conn.execute("SELECT id FROM sessions").fetchall()
        return sorted(row["id"] for row in rows)

    def close(self) -> None:
        with self._lock:
            self._conn.close()