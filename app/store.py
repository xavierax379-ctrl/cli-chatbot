"""会话存储：内存实现。

所有会话读写在都集中在这里，路由器只调用这些方法。
以后换成数据库时，只需要把这个类的实现换掉，路由代码不用动。
"""

from __future__ import annotations

import threading

from app.schemas import Message


class SessionNotFound(KeyError):
    """会话不存在。路由层会把它翻成 HTTP 404。"""


class SessionStore:
    """内存会话表：session_id -> 消息列表。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, list[Message]] = {}

    def get_or_create(self, session_id: str) -> None:
        """会话不存在就创建一个空会话。"""
        with self._lock:
            self._sessions.setdefault(session_id, [])

    def exists(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._sessions

    def append(self, session_id: str, role: str, content: str) -> Message:
        """追加一条消息；会话不存在时自动创建。"""
        message = Message(role=role, content=content)
        with self._lock:
            self._sessions.setdefault(session_id, []).append(message)
        return message

    def messages(self, session_id: str) -> list[Message]:
        """按对话顺序返回该会话的全部消息（返回副本）。"""
        with self._lock:
            if session_id not in self._sessions:
                raise SessionNotFound(session_id)
            return list(self._sessions[session_id])

    def list_sessions(self) -> list[str]:
        """返回所有会话 ID。"""
        with self._lock:
            return sorted(self._sessions)

    def clear(self, session_id: str) -> None:
        """清空会话里的消息，但会话本身保留（之后还能继续用同一个 ID）。"""
        with self._lock:
            if session_id not in self._sessions:
                raise SessionNotFound(session_id)
            self._sessions[session_id] = []

    def pop_last(self, session_id: str) -> None:
        """撤销最后一条消息（模型调用失败时，避免历史里留下没有回复的提问）。"""
        with self._lock:
            messages = self._sessions.get(session_id)
            if messages:
                messages.pop()