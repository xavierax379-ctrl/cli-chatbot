"""测试公共装置：隔离环境变量与本地 .env，并提供注入假模型的 API 客户端。

全程不联网、不需要真实 API Key。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from chatbot.app.deps import get_client, get_store
from chatbot.app.main import app
from chatbot.app.store import SessionStore
from chatbot.config import Settings, get_settings
from fake_model import FakeOpenAI
from chatbot.llm import ChatClient

CONFIG_ENV_VARS = (
    "CHATBOT_API_KEY",
    "CHATBOT_BASE_URL",
    "CHATBOT_MODEL",
    "CHATBOT_TEMPERATURE",
    "CHATBOT_MAX_TOKENS",
    "CHATBOT_SYSTEM_PROMPT",
    "CHATBOT_HISTORY_LIMIT",
    "CHATBOT_REQUEST_TIMEOUT",
)

TESTS_DIR = Path(__file__).resolve().parent


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    """每个用例都从零开始：清环境变量、切到 tests/（没有 .env）、清缓存。"""
    for name in CONFIG_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(TESTS_DIR)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def store() -> SessionStore:
    """每个用例一个全新的内存存储。"""
    return SessionStore()


@pytest.fixture
def fake_openai() -> FakeOpenAI:
    return FakeOpenAI()


@pytest.fixture
def api(store: SessionStore, fake_openai: FakeOpenAI) -> TestClient:
    """注入了假模型 + 干净存储的 TestClient。"""
    settings = Settings(api_key="sk-test-123")
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_client] = lambda: ChatClient(settings, client=fake_openai)
    yield TestClient(app)
    app.dependency_overrides.clear()