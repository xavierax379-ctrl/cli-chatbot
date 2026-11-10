"""数据库层测试：建表、连续历史、会话隔离、清空、重开连接后数据仍在。

用 tmp_path 下的独立数据库文件，不碰开发机上的 chat.db 和 .env。
"""

from __future__ import annotations

import sqlite3

import pytest

from chatbot.app.store import SessionNotFound, SessionStore


def test_tables_created(tmp_path):
    """建表成功：sessions 与 messages 都在。"""
    db = tmp_path / "fresh.db"
    SessionStore(db).close()

    conn = sqlite3.connect(db)
    names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()

    assert {"sessions", "messages"} <= names


def test_history_is_ordered(tmp_path):
    """同一会话历史连续，且按对话顺序返回。"""
    store = SessionStore(tmp_path / "chat.db")
    store.append("u1", "user", "第一句")
    store.append("u1", "assistant", "第二句")
    store.append("u1", "user", "第三句")

    messages = store.messages("u1")
    store.close()

    assert [m.role for m in messages] == ["user", "assistant", "user"]
    assert [m.content for m in messages] == ["第一句", "第二句", "第三句"]


def test_sessions_are_isolated(tmp_path):
    """不同会话互不干扰。"""
    store = SessionStore(tmp_path / "chat.db")
    store.append("u1", "user", "只属于 u1")
    store.append("u2", "user", "只属于 u2")

    assert [m.content for m in store.messages("u1")] == ["只属于 u1"]
    assert [m.content for m in store.messages("u2")] == ["只属于 u2"]
    assert store.list_sessions() == ["u1", "u2"]
    store.close()


def test_clear_removes_messages_but_keeps_session(tmp_path):
    """清空后记录消失，但会话本身还在（还能继续用同一个 ID）。"""
    store = SessionStore(tmp_path / "chat.db")
    store.append("u1", "user", "hi")

    store.clear("u1")

    assert store.exists("u1") is True
    assert store.messages("u1") == []
    store.close()


def test_unknown_session_raises(tmp_path):
    """不存在的会话抛 SessionNotFound（路由层翻成 404）。"""
    store = SessionStore(tmp_path / "chat.db")
    with pytest.raises(SessionNotFound):
        store.messages("nobody")
    with pytest.raises(SessionNotFound):
        store.clear("nobody")
    store.close()


def test_data_survives_reopen(tmp_path):
    """持久化：关掉连接再打开同一个文件，数据还在。"""
    db = tmp_path / "chat.db"

    first = SessionStore(db)
    first.append("u1", "user", "重启前的消息")
    first.close()

    second = SessionStore(db)  # 模拟服务重启
    messages = second.messages("u1")
    sessions = second.list_sessions()
    second.close()

    assert sessions == ["u1"]
    assert [m.content for m in messages] == ["重启前的消息"]


def test_pop_last_removes_latest_message(tmp_path):
    """失败回滚用：只删最后一条。"""
    store = SessionStore(tmp_path / "chat.db")
    store.append("u1", "user", "问题")
    store.append("u1", "assistant", "回复")

    store.pop_last("u1")

    assert [m.content for m in store.messages("u1")] == ["问题"]
    store.close()