"""大模型调用的封装：负责拼 messages、裁剪历史、发起请求。"""

from __future__ import annotations

from typing import Any

from openai import OpenAI

from config import Settings

Message = dict[str, str]


def trim_history(history: list[Message], limit: int) -> list[Message]:
    """只保留最近 limit 条历史消息；limit <= 0 表示不携带历史。"""
    if limit <= 0:
        return []
    return history[-limit:]


def build_messages(settings: Settings, history: list[Message]) -> list[Message]:
    """system prompt 永远在最前，历史只保留最近若干条。"""
    kept = trim_history(history, settings.history_limit)
    return [{"role": "system", "content": settings.system_prompt}, *kept]


class ChatClient:
    """对 OpenAI 兼容接口的薄封装，方便测试时注入假 client。"""

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self._settings = settings
        self._client = client or OpenAI(
            api_key=settings.api_key.get_secret_value(),
            base_url=settings.base_url,
            timeout=settings.request_timeout,
        )

    def reply(self, history: list[Message]) -> str:
        """根据历史消息返回一条完整回复。"""
        response = self._client.chat.completions.create(
            model=self._settings.model,
            messages=build_messages(self._settings, history),
            temperature=self._settings.temperature,
            max_tokens=self._settings.max_tokens,
        )
        return response.choices[0].message.content or ""