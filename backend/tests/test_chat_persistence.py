"""Chat exchange persistence.

Verifies that ``ChatService`` always persists the user message (and any
assistant reply) through the conversation repository, recovers from an unknown
conversation id, and never lets a persistence failure break the stream.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.services.chat.service import ChatRequest, ChatService
from app.services.runtime.base import ChatMessage


class _Session:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _FakeDB:
    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail

    def session(self):
        if self._fail:
            raise RuntimeError("database unavailable")
        return _Session()


class _FakeRepo:
    last: _FakeRepo | None = None
    exists_result = True

    def __init__(self, session) -> None:
        self.session = session
        self.messages: list[tuple[str, str, str | None]] = []
        self.created: list[tuple[str, str | None]] = []
        _FakeRepo.last = self

    async def exists(self, conversation_id) -> bool:
        return _FakeRepo.exists_result

    async def create(self, title, model_name=None):
        self.created.append((title, model_name))
        return SimpleNamespace(id=uuid.uuid4())

    async def add_message(self, conversation_id, role, content, **kwargs):
        self.messages.append((role, content, kwargs.get("model_name")))
        return SimpleNamespace(id=uuid.uuid4())


def _request(text: str = "hello") -> ChatRequest:
    return ChatRequest(messages=[ChatMessage(role="user", content=text)])


def _install(monkeypatch, *, fail: bool = False, exists: bool = True):
    monkeypatch.setattr(
        "app.services.chat.service.get_database", lambda: _FakeDB(fail=fail)
    )
    monkeypatch.setattr("app.services.chat.service.ConversationRepository", _FakeRepo)
    _FakeRepo.exists_result = exists
    _FakeRepo.last = None


async def test_new_conversation_persists_user_and_assistant(monkeypatch):
    _install(monkeypatch, exists=False)
    conversation_id = await ChatService()._persist_exchange(
        _request(),
        conversation_id=None,
        model="qwen3:8b",
        response_text="hi there",
        activities=[{"id": "a1"}],
        sources=[],
        memories=[],
    )
    assert conversation_id is not None
    repo = _FakeRepo.last
    assert repo is not None
    assert repo.created and repo.created[0] == ("hello", "qwen3:8b")
    assert [(role, content) for role, content, _ in repo.messages] == [
        ("user", "hello"),
        ("assistant", "hi there"),
    ]


async def test_unknown_conversation_id_creates_a_new_one(monkeypatch):
    _install(monkeypatch, exists=False)
    requested_id = uuid.uuid4()
    result = await ChatService()._persist_exchange(
        _request("continue"),
        conversation_id=requested_id,
        model="m",
        response_text="answer",
        activities=[],
        sources=[],
        memories=[],
    )
    assert result is not None
    assert result != requested_id  # a fresh conversation was created
    assert _FakeRepo.last is not None and _FakeRepo.last.created


async def test_empty_reply_still_persists_the_user_message(monkeypatch):
    _install(monkeypatch, exists=False)
    await ChatService()._persist_exchange(
        _request("only me"),
        conversation_id=None,
        model="m",
        response_text="",
        activities=[],
        sources=[],
        memories=[],
    )
    assert _FakeRepo.last is not None
    assert [role for role, _, _ in _FakeRepo.last.messages] == ["user"]


async def test_persistence_failure_never_raises(monkeypatch):
    _install(monkeypatch, fail=True)
    requested_id = uuid.uuid4()
    result = await ChatService()._persist_exchange(
        _request(),
        conversation_id=requested_id,
        model="m",
        response_text="answer",
        activities=[],
        sources=[],
        memories=[],
    )
    # The caller keeps the id it already had; the stream is not interrupted.
    assert result == requested_id
