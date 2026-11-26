"""假的 OpenAI 客户端：记录每次调用的参数，返回预设内容，完全离线。"""

from __future__ import annotations

from types import SimpleNamespace


def _chunk(text: str):
    """造一个流式 chunk，形状和 SDK 返回的一致。"""
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=text))])


class FakeCompletions:
    def __init__(self, replies: list[str] | None = None, pieces: tuple[str, ...] = ("ok",)) -> None:
        self.calls: list[dict] = []
        self._replies = list(replies) if replies else ["这是模型返回的假回复"]
        self.pieces = pieces

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("stream"):
            return iter([_chunk(piece) for piece in self.pieces])
        text = self._replies[0] if len(self._replies) == 1 else self._replies.pop(0)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=text))]
        )


class FakeOpenAI:
    """冒充 OpenAI 客户端：调用路径是 client.chat.completions.create(...)。"""

    def __init__(self, replies: list[str] | None = None, pieces: tuple[str, ...] = ("ok",)) -> None:
        self.completions = FakeCompletions(replies, pieces)
        self.chat = SimpleNamespace(completions=self.completions)

    @property
    def calls(self) -> list[dict]:
        return self.completions.calls