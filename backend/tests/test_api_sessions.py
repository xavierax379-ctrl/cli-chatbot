"""会话管理接口测试：列表、消息顺序、清空、不存在的会话返回 404。"""

from __future__ import annotations


def post_chat(api, session_id: str, message: str):
    return api.post("/chat", json={"session_id": session_id, "message": message})


def test_list_sessions(api):
    post_chat(api, "u2", "hi")
    post_chat(api, "u1", "hi")

    resp = api.get("/sessions")
    assert resp.status_code == 200
    assert resp.json() == {"sessions": ["u1", "u2"]}  # 排序后的结果


def test_messages_in_order(api):
    post_chat(api, "u1", "第一句")
    post_chat(api, "u1", "第二句")

    body = api.get("/sessions/u1/messages").json()
    roles = [m["role"] for m in body["messages"]]
    assert roles == ["user", "assistant", "user", "assistant"]
    assert body["messages"][0]["content"] == "第一句"
    assert body["messages"][2]["content"] == "第二句"


def test_delete_clears_messages(api):
    post_chat(api, "u1", "hi")

    resp = api.delete("/sessions/u1")
    assert resp.status_code == 204
    assert api.get("/sessions/u1/messages").json()["messages"] == []


def test_unknown_session_returns_404(api):
    assert api.get("/sessions/nobody/messages").status_code == 404
    assert api.delete("/sessions/nobody").status_code == 404


def test_keyword_returns_only_matching_messages(api):
    post_chat(api, "k1", "我喜欢吃苹果")
    post_chat(api, "k1", "今天天气不错")

    body = api.get("/sessions/k1/messages", params={"keyword": "苹果"}).json()

    assert [m["content"] for m in body["messages"]] == ["我喜欢吃苹果"]


def test_without_keyword_returns_full_history(api):
    post_chat(api, "k1", "第一句")
    post_chat(api, "k1", "第二句")

    body = api.get("/sessions/k1/messages").json()

    assert len(body["messages"]) == 4


def test_keyword_without_match_returns_empty(api):
    post_chat(api, "k1", "你好")

    body = api.get("/sessions/k1/messages", params={"keyword": "不存在的词"}).json()

    assert body["messages"] == []


def test_keyword_does_not_leak_across_sessions(api):
    post_chat(api, "a", "苹果在 A")
    post_chat(api, "b", "苹果在 B")

    body = api.get("/sessions/a/messages", params={"keyword": "苹果"}).json()

    assert [m["content"] for m in body["messages"]] == ["苹果在 A"]