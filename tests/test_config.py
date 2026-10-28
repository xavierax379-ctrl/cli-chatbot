"""配置模块测试：默认值、越界校验、SecretStr 不泄露明文。全离线，不需要真实 Key。"""

from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError

from config import Settings, get_settings


def test_default_values(monkeypatch):
    """只给 API Key 时，其余配置项应取 config.py 里的默认值。"""
    monkeypatch.setenv("CHATBOT_API_KEY", "sk-test-123")

    settings = get_settings()

    assert settings.base_url == "https://api.openai.com/v1"
    assert settings.model == "gpt-4o-mini"
    assert settings.temperature == 0.7
    assert settings.max_tokens == 1024
    assert settings.history_limit == 20


def test_env_overrides_defaults(monkeypatch):
    """环境变量能覆盖默认值 —— 说明配置不是硬编码的。"""
    monkeypatch.setenv("CHATBOT_API_KEY", "sk-test-123")
    monkeypatch.setenv("CHATBOT_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("CHATBOT_MODEL", "deepseek-chat")
    monkeypatch.setenv("CHATBOT_TEMPERATURE", "0.2")

    settings = get_settings()

    assert settings.base_url == "https://example.com/v1"
    assert settings.model == "deepseek-chat"
    assert settings.temperature == 0.2


def test_temperature_out_of_range_raises(monkeypatch):
    """温度必须落在 0~2，写 5 要抛 ValidationError，而不是悄悄生效。"""
    monkeypatch.setenv("CHATBOT_API_KEY", "sk-test-123")
    monkeypatch.setenv("CHATBOT_TEMPERATURE", "5")

    with pytest.raises(ValidationError):
        get_settings()


def test_secret_str_never_prints_plaintext(monkeypatch):
    """api_key 是 SecretStr：str / repr / 序列化结果都不能出现明文。"""
    plaintext = "sk-super-secret-123"
    monkeypatch.setenv("CHATBOT_API_KEY", plaintext)

    settings = get_settings()

    assert isinstance(settings.api_key, SecretStr)
    assert settings.api_key.get_secret_value() == plaintext
    assert plaintext not in str(settings)
    assert plaintext not in repr(settings)
    assert plaintext not in settings.model_dump_json()
    assert "**********" in str(settings)


def test_get_settings_is_cached(monkeypatch):
    """get_settings 带 lru_cache：同一进程内复用同一个实例。"""
    monkeypatch.setenv("CHATBOT_API_KEY", "sk-test-123")

    assert get_settings() is get_settings()


def test_settings_constructible_without_key(monkeypatch):
    """配置层允许空 key，缺 key 的拦截放在 main.py —— 保证测试能构造对象。"""
    monkeypatch.delenv("CHATBOT_API_KEY", raising=False)

    assert Settings().api_key.get_secret_value() == ""