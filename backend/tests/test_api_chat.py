"""对话接口测试：连续对话、会话隔离、空消息拒绝、模型异常回滚。"""

from __future__ import annotations


def post_chat(api, session_id: str, message: str):
    return api.post("/chat", json={"session_id": session_id, "message": message})


def test_chat_returns_reply(api):
    resp = post_chat(api, "u1", "你好")
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == "u1"
    assert body["reply"]


def test_same_session_keeps_history(api, fake_openai):
    post_chat(api, "u1", "我叫小明")
    post_chat(api, "u1", "我叫什么名字？")

    assert len(fake_openai.calls) == 2
    messages = fake_openai.calls[1]["messages"]
    # system + 上一轮 user/assistant + 本轮 user
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "user"]
    assert messages[1]["content"] == "我叫小明"
    assert messages[3]["content"] == "我叫什么名字？"


def test_sessions_are_isolated(api, fake_openai):
    post_chat(api, "u1", "我叫小明")
    post_chat(api, "u2", "我叫什么名字？")

    messages = fake_openai.calls[1]["messages"]
    assert [m["role"] for m in messages] == ["system", "user"]  # 看不到 u1 的历史
    assert messages[1]["content"] == "我叫什么名字？"


def test_empty_message_rejected(api):
    resp = post_chat(api, "u1", "   ")
    assert resp.status_code == 422


def test_blank_session_id_rejected(api):
    resp = api.post("/chat", json={"session_id": "", "message": "hi"})
    assert resp.status_code == 422


def test_model_failure_returns_502_and_rolls_back(api, fake_openai, store):
    def boom(**kwargs):
        raise RuntimeError("upstream down")

    fake_openai.completions.create = boom
    resp = post_chat(api, "u1", "hi")

    assert resp.status_code == 502
    assert store.messages("u1") == []  # 没有回复的提问被撤销

def test_study_word_returns_explanation(api, fake_openai):
    resp = api.post("/study/word", json={"word": "apple"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["word"] == "apple"
    assert body["explanation"]

    # 用的是学习功能的 system prompt（英语老师），不是对话人设
    system_content = fake_openai.calls[0]["messages"][0]["content"]
    assert "英语" in system_content

    # 学习功能不创建会话
    assert api.get("/sessions").json() == {"sessions": []}


def test_study_word_rejects_blank(api):
    assert api.post("/study/word", json={"word": "   "}).status_code == 422