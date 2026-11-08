"""大模型调用的封装：拼 messages、裁剪历史、发起请求（流式 / 非流式）。"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

from openai import OpenAI

from chatbot.config import Settings

Message = dict[str, str]


def trim_history(history: Iterable[Message], limit: int) -> list[Message]:
    """只保留最近 limit 条历史消息；limit <= 0 表示不携带历史。"""
    items = list(history)
    if limit <= 0:
        return []
    return items[-limit:]


def _as_api_message(message: Any) -> Message:
    """把一条会话记录统一成 SDK 要的 dict：兼容 dict 和 pydantic 模型两种形态。"""
    if isinstance(message, dict):
        return {"role": message["role"], "content": message["content"]}
    return {"role": message.role, "content": message.content}


def build_messages(
    settings: Settings,
    history: Iterable[Any],
    system_prompt: str | None = None,
) -> list[Message]:
    """system prompt 永远在最前，历史只保留最近若干条。"""
    kept = [_as_api_message(item) for item in trim_history(history, settings.history_limit)]
    prompt = (system_prompt or settings.system_prompt).strip()
    return [{"role": "system", "content": prompt}, *kept]


class ChatClient:
    """对 OpenAI 兼容接口的薄封装，方便测试时注入假 client。"""

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self._settings = settings
        self._client = client if client is not None else OpenAI(
            api_key=settings.api_key.get_secret_value(),
            base_url=settings.base_url,
            timeout=settings.request_timeout,
        )

    def chat(self, history: Iterable[Any], system_prompt: str | None = None) -> str:
        """一次性拿到完整回复（非流式），用于 /chat 这类 JSON 接口。"""
        response = self._client.chat.completions.create(
            model=self._settings.model,
            messages=build_messages(self._settings, history, system_prompt),
            temperature=self._settings.temperature,
            max_tokens=self._settings.max_tokens,
            stream=False,
        )
        return response.choices[0].message.content or ""

    def stream_reply(
        self,
        history: Iterable[Any],
        system_prompt: str | None = None,
    ) -> Iterator[str]:
        """按片段产出回复文本：收到一段就能立刻打印 / 返回。"""
        stream = self._client.chat.completions.create(
            model=self._settings.model,
            messages=build_messages(self._settings, history, system_prompt),
            temperature=self._settings.temperature,
            max_tokens=self._settings.max_tokens,
            stream=True,  # 需求要求边收边打，所以不做成可配置开关
        )
        for chunk in stream:
            if not chunk.choices:  # 有的实现会在末尾发一个只有 usage 的空 chunk
                continue
            content = getattr(chunk.choices[0].delta, "content", None)
            if content:
                yield content