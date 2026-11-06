"""FastAPI 应用：对话接口与会话管理。"""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from app.deps import get_client, get_store
from app.schemas import ChatRequest, ChatResponse, MessageList, SessionList
from app.store import SessionNotFound, SessionStore
from llm import ChatClient

app = FastAPI(title="Chatbot API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """给调用方（或以后的前端）一个探活接口。"""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    store: SessionStore = Depends(get_store),
    client: ChatClient = Depends(get_client),
) -> ChatResponse:
    """一问一答：带上该会话的历史，返回完整回复。"""
    session_id = payload.session_id
    store.get_or_create(session_id)
    store.append(session_id, "user", payload.message)

    try:
        reply = client.chat(store.messages(session_id))
    except Exception as exc:  # 网络 / 鉴权 / 限流等
        store.pop_last(session_id)  # 撤掉这条没有回复的提问
        raise HTTPException(
            status_code=502,
            detail=f"模型调用失败：{type(exc).__name__}",
        ) from exc

    if not reply.strip():
        store.pop_last(session_id)
        raise HTTPException(status_code=502, detail="模型没有返回内容")

    store.append(session_id, "assistant", reply)
    return ChatResponse(session_id=session_id, reply=reply)


@app.get("/sessions", response_model=SessionList)
def list_sessions(store: SessionStore = Depends(get_store)) -> SessionList:
    """列出所有会话 ID。"""
    return SessionList(sessions=store.list_sessions())


@app.get("/sessions/{session_id}/messages", response_model=MessageList)
def list_messages(
    session_id: str,
    store: SessionStore = Depends(get_store),
) -> MessageList:
    """按对话顺序返回该会话的消息记录。"""
    try:
        messages = store.messages(session_id)
    except SessionNotFound as exc:
        raise HTTPException(status_code=404, detail="会话不存在") from exc
    return MessageList(session_id=session_id, messages=messages)


@app.delete("/sessions/{session_id}", status_code=204)
def clear_session(
    session_id: str,
    store: SessionStore = Depends(get_store),
) -> None:
    """清空会话里的消息（会话本身保留，之后还能继续用这个 ID）。"""
    try:
        store.clear(session_id)
    except SessionNotFound as exc:
        raise HTTPException(status_code=404, detail="会话不存在") from exc