"""Chat stream orchestration: emits real activity events, never fake source data."""

from __future__ import annotations

from app.db.session import Database
from app.services.chat.service import ChatRequest, ChatService
from app.services.runtime.base import ChatMessage, StreamChunk
from app.services.runtime.ollama import OllamaAdapter


async def _fake_chat(self, model, messages, *, options=None):
    yield StreamChunk(type="delta", content="Hello", model=model)
    yield StreamChunk(type="delta", content=" world", model=model)
    yield StreamChunk(type="done", model=model, metrics={"eval_count": 2})


async def _db_down(self):
    return False, "connection refused"


async def test_stream_emits_deltas_and_completion(monkeypatch):
    monkeypatch.setattr(OllamaAdapter, "chat", _fake_chat)
    monkeypatch.setattr(Database, "ping", _db_down)

    async def fake_resolve(self, requested):
        return "test-model"

    monkeypatch.setattr(ChatService, "resolve_model", fake_resolve)

    request = ChatRequest(messages=[ChatMessage(role="user", content="hi")], use_brain=False)
    events = [event async for event in ChatService().stream(request)]
    types = [event["type"] for event in events]

    assert types[0] == "chat.started"
    assert "assistant.delta" in types
    assert "assistant.completed" in types
    assert types[-1] == "chat.completed"

    deltas = "".join(e["data"]["content"] for e in events if e["type"] == "assistant.delta")
    assert deltas == "Hello world"

    completed = next(e for e in events if e["type"] == "chat.completed")
    # No web requested -> no sources may be reported.
    assert completed["data"]["sources"] == []
    assert completed["data"]["memory_used"] == 0


async def test_stream_reports_model_error(monkeypatch):
    async def failing_chat(self, model, messages, *, options=None):
        yield StreamChunk(type="error", error="Ollama unavailable")

    monkeypatch.setattr(OllamaAdapter, "chat", failing_chat)
    monkeypatch.setattr(Database, "ping", _db_down)

    async def fake_resolve(self, requested):
        return "test-model"

    monkeypatch.setattr(ChatService, "resolve_model", fake_resolve)

    request = ChatRequest(messages=[ChatMessage(role="user", content="hi")], use_brain=False)
    events = [event async for event in ChatService().stream(request)]
    assert any(e["type"] == "chat.error" for e in events)
