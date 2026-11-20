"""数据库层测试：ORM 建表、历史顺序、会话隔离、清空、重开连接、事务回滚。

用 tmp_path 下的独立 SQLite 文件，不碰开发机上的 chat.db 与 .env。
"""

from __future__ import annotations

import sqlite3

import pytest

from chatbot.app.store import SessionNotFound, SessionStore


def test_tables_created(tmp_path):
    """建表成功：sessions 与 messages 都在。"""
    db_path = tmp_path / "fresh.db"
    SessionStore(db_path).close()

    conn = sqlite3.connect(db_path)
    names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()

    assert {"sessions", "messages"} <= names


def test_turn_is_written_as_a_pair(tmp_path):
    """一轮对话写两条，按对话顺序返回。"""
    store = SessionStore(tmp_path / "chat.db")
    store.append_turn("u1", "第一句", "回复一")
    store.append_turn("u1", "第二句", "回复二")

    messages = store.messages("u1")
    store.close()

    assert [m.role for m in messages] == ["user", "assistant", "user", "assistant"]
    assert [m.content for m in messages] == ["第一句", "回复一", "第二句", "回复二"]


def test_sessions_are_isolated(tmp_path):
    """不同会话互不干扰。"""
    store = SessionStore(tmp_path / "chat.db")
    store.append_turn("u1", "只属于 u1", "回复 1")
    store.append_turn("u2", "只属于 u2", "回复 2")

    assert [m.content for m in store.messages("u1")] == ["只属于 u1", "回复 1"]
    assert [m.content for m in store.messages("u2")] == ["只属于 u2", "回复 2"]
    assert store.list_sessions() == ["u1", "u2"]
    store.close()


def test_clear_removes_messages_but_keeps_session(tmp_path):
    """清空后记录消失，但会话本身还在。"""
    store = SessionStore(tmp_path / "chat.db")
    store.append_turn("u1", "hi", "hello")

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
    db_path = tmp_path / "chat.db"

    first = SessionStore(db_path)
    first.append_turn("u1", "重启前的消息", "重启前的回复")
    first.close()

    second = SessionStore(db_path)  # 模拟服务重启
    messages = second.messages("u1")
    sessions = second.list_sessions()
    second.close()

    assert sessions == ["u1"]
    assert [m.content for m in messages] == ["重启前的消息", "重启前的回复"]


def test_failed_turn_leaves_no_partial_history(tmp_path):
    """事务：回复写不进去时，用户消息也不能留下。"""
    store = SessionStore(tmp_path / "chat.db")
    store.get_or_create("u1")

    with pytest.raises(Exception):
        store.append_turn("u1", "用户消息", None)  # assistant 内容为 NULL → 写入失败

    assert store.messages("u1") == []
    store.close()