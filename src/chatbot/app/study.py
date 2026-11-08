"""学习功能：英语单词讲解。

独立于对话会话：不读写 SessionStore，也不影响 /chat 的上下文。
"""

from __future__ import annotations

from chatbot.llm import ChatClient


def explain_word(client: ChatClient, system_prompt: str, word: str) -> str:
    """让模型以英语老师口吻讲解一个单词，返回纯文本。"""
    history = [{"role": "user", "content": f"请讲解这个英语单词：{word}"}]
    return client.chat(history, system_prompt=system_prompt)