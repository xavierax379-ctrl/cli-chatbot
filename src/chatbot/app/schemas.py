"""HTTP 请求 / 响应模型。

校验放在这里：空消息、空 session_id 会在进入路由之前就被 422 拦下。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """/chat 和 /chat/stream 共用的请求体。"""

    session_id: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1)

    @field_validator("session_id", "message")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """去掉首尾空白后不能为空 —— "   " 这种也要拒绝。"""
        value = value.strip()
        if not value:
            raise ValueError("不能为空或只包含空白字符")
        return value

class WordRequest(BaseModel):
    """单词讲解请求。"""

    word: str = Field(min_length=1, max_length=64)

    @field_validator("word")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("不能为空或只包含空白字符")
        return value


class WordResponse(BaseModel):
    word: str
    explanation: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str


class Message(BaseModel):
    """一条对话记录。"""

    role: Literal["user", "assistant"]
    content: str


class SessionList(BaseModel):
    sessions: list[str]


class MessageList(BaseModel):
    session_id: str
    messages: list[Message]