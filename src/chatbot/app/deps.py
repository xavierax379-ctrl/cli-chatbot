"""依赖注入：路由用到的会话存储和模型客户端都从这里拿。

测试时用 app.dependency_overrides 整包替换成假的，一个网络请求都不会发。
"""

from __future__ import annotations

from functools import lru_cache

from chatbot.app.store import SessionStore
from chatbot.config import get_settings
from chatbot.llm import ChatClient


@lru_cache(maxsize=1)
def get_store() -> SessionStore:
    """返回会话存储。

    - 用 lru_cache 保证进程内只有一个连接
    - 数据库路径来自配置（CHATBOT_DB_PATH），所以数据会持久化到磁盘
    - 不放在模块级，避免 import 时就创建数据库文件（测试好隔离）
    """
    return SessionStore(get_settings().db_path)


@lru_cache(maxsize=1)
def get_client() -> ChatClient:
    """返回模型客户端；用 lru_cache 保证只创建一次（OpenAI 客户端是长连接）。"""
    return ChatClient(get_settings())