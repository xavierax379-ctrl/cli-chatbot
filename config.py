"""全部可变配置的唯一来源。

默认值写在这里，运行时用 .env 或环境变量覆盖（前缀 CHATBOT_）。
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """从环境变量 / .env 读取配置。"""

    model_config = SettingsConfigDict(
        env_prefix="CHATBOT_",        # 环境变量前缀
        env_file=".env",              # 同时读项目根目录的 .env
        env_file_encoding="utf-8",
        extra="ignore",               # .env 里有多余变量不报错
    )

    # 密钥：用 SecretStr，打印 / 日志里只会出现 **********
    api_key: SecretStr = SecretStr("")
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"

    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, gt=0)

    system_prompt: str = "你是一个乐于助人的中文助手，回答简洁准确。"
    history_limit: int = Field(default=20, ge=0)
    request_timeout: float = Field(default=60.0, gt=0)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """返回全局唯一的配置对象（进程内缓存，测试里可 cache_clear()）。"""
    return Settings()