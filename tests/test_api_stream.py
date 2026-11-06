"""流式接口测试：模型收到 stream=True、内容逐块返回、完整回复写入历史。"""

from __future__ import annotations


def test_stream_returns_chunks_and_saves_history(api, fake_openai, store):
    resp = api.post("/chat/stream", json={"session_id": "s1", "message": "你好"})

    assert resp.status_code == 200
    assert resp.text == "ok"  # 假模型默认返回一段 "ok"

    # 模型确实收到了 stream=True
    assert fake_openai.calls[0]["stream"] is True

    # 完整回复被写入历史，user / assistant 成对
    messages = store.messages("s1")
    assert [m.role for m in messages] == ["user", "assistant"]
    assert messages[0].content == "你好"
    assert messages[1].content == "ok"


def test_stream_accumulates_multiple_chunks(api, fake_openai, store):
    fake_openai.completions.pieces = ("你", "好", "！")

    resp = api.post("/chat/stream", json={"session_id": "s2", "message": "hi"})

    assert resp.text == "你好！"
    assert store.messages("s2")[-1].content == "你好！"


def test_stream_rejects_blank_message(api):
    resp = api.post("/chat/stream", json={"session_id": "s1", "message": "   "})
    assert resp.status_code == 422