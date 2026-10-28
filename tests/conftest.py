"""测试公共装置：隔离环境变量与本地 .env，避免测试受开发机配置影响。"""

from __future__ import annotations

from pathlib import Path

import pytest

from config import get_settings

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
    # .env 只可能在项目根目录，切到 tests/ 就读不到开发机上的真实配置
    monkeypatch.chdir(TESTS_DIR)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()