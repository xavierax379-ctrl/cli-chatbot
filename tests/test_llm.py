"""模型调用测试：用假 client 断言传给 SDK 的参数，全程不联网、不需要真实 Key。"""

from __future__ import annotations

from types import SimpleNamespace

from config import get_settings
from llm import ChatClient, build_messages, trim_history


class FakeCompletions:
    """记录每次 create 的入参，并按片段返回假 chunk。"""

    def __init__(self, pieces: tuple[str, ...]) -> None:
        self.pieces = pieces
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return iter([self._chunk(piece) for piece in self.pieces])

    @staticmethod
    def _chunk(text: str):
        return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=text))])


class FakeClient:
    def __init__(self, pieces: tuple[str, ...] = ("你", "好")) -> None:
        self.completions = FakeCompletions(pieces)
        self.chat = SimpleNamespace(completions=self.completions)


def make_settings(monkeypatch, **env: object):
    monkeypatch.setenv("CHATBOT_API_KEY", "sk-test-123")
    for key, value in env.items():
        monkeypatch.setenv(key, str(value))
    return get_settings()


def test_request_params_follow_config(monkeypatch):
    """model / temperature / max_tokens / stream 必须来自配置，且必须开启流式。"""
    settings = make_settings(monkeypatch, CHATBOT_TEMPERATURE="0.2", CHATBOT_MAX_TOKENS="256")
    fake = FakeClient()

    list(ChatClient(settings, client=fake).stream_reply([{"role": "user", "content": "你好"}]))

    assert len(fake.completions.calls) == 1
    call = fake.completions.calls[0]
    assert call["model"] == settings.model == "gpt-4o-mini"
    assert call["temperature"] == settings.temperature == 0.2
    assert call["max_tokens"] == settings.max_tokens == 256
    assert call["stream"] is True


def test_messages_structure(monkeypatch):
    """messages 是 [system, user, assistant, user] 的顺序，内容原样透传。"""
    settings = make_settings(monkeypatch)
    fake = FakeClient()
    history = [
        {"role": "user", "content": "第一轮"},
        {"role": "assistant", "content": "第一轮回复"},
        {"role": "user", "content": "第二轮"},
    ]

    list(ChatClient(settings, client=fake).stream_reply(history))

    messages = fake.completions.calls[0]["messages"]
    assert messages[0] == {"role": "system", "content": settings.system_prompt}
    assert messages[1:] == history
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "user"]


def test_history_trimmed_but_system_prompt_kept(monkeypatch):
    """历史超长时只保留最近 N 条，system prompt 不能被裁掉。"""
    settings = make_settings(monkeypatch, CHATBOT_HISTORY_LIMIT="4")
    history = [{"role": "user", "content": f"第{i}条"} for i in range(10)]

    messages = build_messages(settings, history)

    assert messages[0]["role"] == "system"
    assert len(messages) == 5  # system + 4 条历史
    assert messages[-1]["content"] == "第9条"


def test_trim_history_edge_cases():
    history = [{"role": "user", "content": "a"}]
    assert trim_history(history, 0) == []
    assert trim_history(history, -1) == []
    assert trim_history(history, 5) == history


def test_stream_yields_pieces(monkeypatch):
    """流式：逐段产出，拼接后得到完整回复。"""
    settings = make_settings(monkeypatch)
    client = ChatClient(settings, client=FakeClient(("Hel", "lo", "")))

    pieces = list(client.stream_reply([{"role": "user", "content": "hi"}]))

    assert pieces == ["Hel", "lo"]


def test_client_skips_empty_choices(monkeypatch):
    """usage-only 之类的空 chunk 不能崩，也不能把 None 拼进结果。"""
    settings = make_settings(monkeypatch)

    class EmptyChunkCompletions(FakeCompletions):
        def create(self, **kwargs):
            self.calls.append(kwargs)
            return iter(
                [
                    SimpleNamespace(choices=[]),
                    SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=None))]),
                    FakeCompletions._chunk("ok"),
                ]
            )

    fake = FakeClient()
    fake.completions = EmptyChunkCompletions(())
    fake.chat = SimpleNamespace(completions=fake.completions)

    assert "".join(ChatClient(settings, client=fake).stream_reply([])) == "ok"