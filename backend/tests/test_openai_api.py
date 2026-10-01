"""OpenAI-compatible local API contract tests.

The external boundaries (PostgreSQL, Ollama, the chat orchestrator) are mocked
at the module boundary so the tests exercise the real route logic, request
parsing, authentication dependency and response shaping. Nothing in here
asserts fabricated runtime data.
"""

from __future__ import annotations

import json

import httpx
import pytest
from app.api.dependencies import require_api_key
from app.api.routes import openai as openai_route
from app.main import app
from app.services.runtime.base import ModelInfo, RuntimeUnavailable

MODEL = "qwen3:8b"


# --- fakes -----------------------------------------------------------------


class _FakeAdapter:
    def __init__(self, names: list[str]) -> None:
        self._names = names

    async def list_models(self) -> list[ModelInfo]:
        return [ModelInfo(name=name) for name in self._names]


class _Record:
    def __init__(self, name: str) -> None:
        self.name = name
        self.installed = True


class _FakeModels:
    def __init__(self, names: list[str]) -> None:
        self._names = names
        self._adapter = _FakeAdapter(names)

    async def sync_registry(self, session) -> list[_Record]:
        return [_Record(name) for name in self._names]


class _FakeChat:
    def __init__(self, *, unavailable: bool = False) -> None:
        self._unavailable = unavailable

    async def resolve_model(self, requested: str | None) -> str:
        if self._unavailable:
            raise RuntimeUnavailable("Ollama is unavailable")
        return requested or MODEL

    async def complete(self, request):
        if self._unavailable:
            raise RuntimeUnavailable("Ollama is unavailable")
        return MODEL, {
            "content": "Hello from INTLLM",
            "metrics": {"eval_count": 4, "prompt_eval_count": 6, "done_reason": "stop"},
        }, []

    async def stream(self, request):
        if self._unavailable:
            yield {"type": "chat.error", "data": {"message": "Ollama is unavailable"}}
            return
        yield {"type": "assistant.delta", "data": {"content": "Hel"}}
        yield {"type": "assistant.delta", "data": {"content": "lo"}}
        yield {"type": "assistant.completed", "data": {"model": MODEL, "metrics": {}}}


# --- fixtures --------------------------------------------------------------


@pytest.fixture
def overrides_cleanup():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


def _authenticated_client(monkeypatch, names: list[str] | None = None):
    """Client with auth satisfied and Ollama/chat faked out.

    Marks the request loopback + bootstrapped so ``require_api_key`` allows it.
    """
    app.dependency_overrides[require_api_key] = lambda: None
    monkeypatch.setattr(openai_route, "_model_service", _FakeModels(names or [MODEL]))
    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 12345))
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


# --- models ----------------------------------------------------------------


async def test_list_models_returns_openai_shape(monkeypatch, overrides_cleanup):
    client = _authenticated_client(monkeypatch, [MODEL, "llama3.1"])
    async with client as c:
        response = await c.get("/v1/models")
    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "list"
    ids = [m["id"] for m in body["data"]]
    assert ids == [MODEL, "llama3.1"]
    assert all(m["object"] == "model" and m["owned_by"] == "intllm" for m in body["data"])


async def test_get_model_known_and_unknown(monkeypatch, overrides_cleanup):
    client = _authenticated_client(monkeypatch, [MODEL])
    async with client as c:
        ok = await c.get(f"/v1/models/{MODEL}")
        missing = await c.get("/v1/models/does-not-exist")
    assert ok.status_code == 200
    assert ok.json()["id"] == MODEL
    assert missing.status_code == 404
    assert missing.json()["error"]["type"] == "not_found"


# --- chat completions ------------------------------------------------------


async def test_chat_completion_non_streaming_shape(monkeypatch, overrides_cleanup):
    monkeypatch.setattr(openai_route, "get_chat_service", lambda: _FakeChat())
    client = _authenticated_client(monkeypatch)
    async with client as c:
        response = await c.post(
            "/v1/chat/completions",
            json={"model": MODEL, "messages": [{"role": "user", "content": "Hi"}]},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "chat.completion"
    assert body["model"] == MODEL
    assert body["choices"][0]["message"] == {
        "role": "assistant",
        "content": "Hello from INTLLM",
    }
    assert body["choices"][0]["finish_reason"] == "stop"
    assert body["usage"] == {
        "prompt_tokens": 6,
        "completion_tokens": 4,
        "total_tokens": 10,
    }
    assert body["id"].startswith("chatcmpl-")


async def test_chat_completion_streaming_frames(monkeypatch, overrides_cleanup):
    monkeypatch.setattr(openai_route, "get_chat_service", lambda: _FakeChat())
    client = _authenticated_client(monkeypatch)
    async with client as c:
        response = await c.post(
            "/v1/chat/completions",
            json={
                "model": MODEL,
                "stream": True,
                "messages": [{"role": "user", "content": "Hi"}],
            },
        )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    frames = [f for f in response.text.split("\n\n") if f.strip()]
    payloads = [json.loads(f[len("data: ") :]) for f in frames if f.startswith("data: ") and "[DONE]" not in f]
    assert payloads[0]["choices"][0]["delta"] == {"role": "assistant"}
    contents = "".join(
        p["choices"][0]["delta"].get("content", "") for p in payloads
    )
    assert contents == "Hello"
    assert payloads[-1]["choices"][0]["finish_reason"] == "stop"
    assert response.text.rstrip().endswith("data: [DONE]")


async def test_chat_completion_ollama_unavailable(monkeypatch, overrides_cleanup):
    monkeypatch.setattr(
        openai_route, "get_chat_service", lambda: _FakeChat(unavailable=True)
    )
    client = _authenticated_client(monkeypatch)
    async with client as c:
        response = await c.post(
            "/v1/chat/completions",
            json={"model": MODEL, "messages": [{"role": "user", "content": "Hi"}]},
        )
    assert response.status_code == 503
    assert response.json()["error"]["type"] == "service_unavailable"


async def test_chat_completion_streaming_reports_error_frame(
    monkeypatch, overrides_cleanup
):
    monkeypatch.setattr(
        openai_route, "get_chat_service", lambda: _FakeChat(unavailable=True)
    )
    client = _authenticated_client(monkeypatch)
    async with client as c:
        response = await c.post(
            "/v1/chat/completions",
            json={
                "model": MODEL,
                "stream": True,
                "messages": [{"role": "user", "content": "Hi"}],
            },
        )
    assert response.status_code == 200
    assert "service_unavailable" in response.text
    assert response.text.rstrip().endswith("data: [DONE]")


async def test_chat_completion_missing_messages_is_rejected(monkeypatch, overrides_cleanup):
    client = _authenticated_client(monkeypatch)
    async with client as c:
        response = await c.post("/v1/chat/completions", json={"model": MODEL})
    assert response.status_code == 422
    assert response.json()["error"]["type"] == "validation_error"


async def test_chat_completion_rejects_malformed_json(monkeypatch, overrides_cleanup):
    client = _authenticated_client(monkeypatch)
    async with client as c:
        response = await c.post(
            "/v1/chat/completions",
            content=b"{not json",
            headers={"Content-Type": "application/json"},
        )
    assert response.status_code == 422
    assert response.json()["error"]["type"] == "validation_error"


# --- authentication --------------------------------------------------------


def _fake_database(*, available: bool, keys: list | None = None):
    class _SessionCtx:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *args):
            return False

    class _DB:
        async def ping(self):
            return (True, None) if available else (False, "connection refused")

        def session(self):
            return _SessionCtx()

    return _DB()


async def test_missing_key_returns_401(monkeypatch, overrides_cleanup):
    import app.api.dependencies as deps

    monkeypatch.setattr(deps, "get_database", lambda: _fake_database(available=False))
    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 12345))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        response = await c.get("/v1/models")
    assert response.status_code == 401
    assert response.json()["error"]["type"] == "authentication_error"


async def test_invalid_key_returns_401(monkeypatch, overrides_cleanup):
    import app.api.dependencies as deps

    class _Keys:
        async def verify(self, session, token):
            return None

    monkeypatch.setattr(deps, "get_database", lambda: _fake_database(available=True))
    monkeypatch.setattr(deps, "get_api_key_service", lambda: _Keys())
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 12345)),
        base_url="http://testserver",
    )
    async with client as c:
        response = await c.get(
            "/v1/models", headers={"Authorization": "Bearer intllm_bogus"}
        )
    assert response.status_code == 401
    assert response.json()["error"]["type"] == "authentication_error"


async def test_revoked_key_returns_401(monkeypatch, overrides_cleanup):
    import app.api.dependencies as deps

    # A revoked key is not returned by the active-key lookup, so verification
    # fails exactly like an unknown key.
    class _Keys:
        async def verify(self, session, token):
            return None

    monkeypatch.setattr(deps, "get_database", lambda: _fake_database(available=True))
    monkeypatch.setattr(deps, "get_api_key_service", lambda: _Keys())
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 12345)),
        base_url="http://testserver",
    )
    async with client as c:
        response = await c.get(
            "/v1/models", headers={"x-api-key": "intllm_revoked"}
        )
    assert response.status_code == 401


async def test_valid_key_is_accepted(monkeypatch, overrides_cleanup):
    import app.api.dependencies as deps

    class _Keys:
        async def verify(self, session, token):
            return object()  # a non-None key record

    monkeypatch.setattr(deps, "get_database", lambda: _fake_database(available=True))
    monkeypatch.setattr(deps, "get_api_key_service", lambda: _Keys())
    monkeypatch.setattr(openai_route, "_model_service", _FakeModels([MODEL]))
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 12345)),
        base_url="http://testserver",
    )
    async with client as c:
        response = await c.get(
            "/v1/models", headers={"Authorization": "Bearer intllm_valid"}
        )
    assert response.status_code == 200
    assert response.json()["data"][0]["id"] == MODEL


async def test_database_unavailable_returns_503(monkeypatch, overrides_cleanup):
    import app.api.dependencies as deps

    monkeypatch.setattr(deps, "get_database", lambda: _fake_database(available=False))
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 12345)),
        base_url="http://testserver",
    )
    async with client as c:
        response = await c.get(
            "/v1/models", headers={"Authorization": "Bearer intllm_anything"}
        )
    assert response.status_code == 503
    assert response.json()["error"]["type"] == "service_unavailable"
