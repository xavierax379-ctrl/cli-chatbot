"""依赖注入：路由用到的会话存储和模型客户端都从这里拿。

测试时用 app.dependency_overrides 整包替换成假的，一个网络请求都不会发。
"""

from __future__ import annotations

from functools import lru_cache

from chatbot.app.store import SessionStore
from chatbot.config import get_settings
from chatbot.llm import ChatClient

# 进程内唯一的会话存储（内存实现，重启即清空）
_store = SessionStore()


def get_store() -> SessionStore:
    """返回会话存储。测试里会 override 成新实例，保证用例隔离。"""
    return _store


@lru_cache(maxsize=1)
def get_client() -> ChatClient:
    """返回模型客户端；用 lru_cache 保证只创建一次（OpenAI 客户端是长连接）。"""
    return ChatClient(get_settings())