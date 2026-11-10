"""前端托管测试：首页能返回 index.html，静态挂载不影响 API，页面不暴露密钥。"""

from __future__ import annotations


def test_homepage_served(api):
    resp = api.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "<html" in resp.text.lower()


def test_page_has_no_secret(api):
    body = api.get("/").text
    assert "sk-" not in body
    assert "api_key" not in body.lower()
    assert "chatbot_api_key" not in body.lower()


def test_static_mount_does_not_swallow_api(api):
    assert api.get("/health").status_code == 200
    assert api.get("/sessions").status_code == 200
    resp = api.post("/chat", json={"session_id": "w1", "message": "hi"})
    assert resp.status_code == 200
    assert api.get("/docs").status_code == 200


def test_index_html_directly_reachable(api):
    assert api.get("/index.html").status_code == 200