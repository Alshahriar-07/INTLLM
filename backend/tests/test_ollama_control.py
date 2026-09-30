"""Ollama control endpoint behaviour (mocked process layer, real service logic)."""

from __future__ import annotations

import httpx
import pytest

from app.main import app
from app.services.ollama import process as ollama_process
from app.services.ollama.service import get_ollama_control_service


@pytest.fixture(autouse=True)
def _fresh_control_state():
    # Reset the singleton state machine between tests.
    import app.services.ollama.service as svc

    svc._control = None
    yield
    svc._control = None


async def _probe_ok(timeout: float = 2.0):
    return True, None


async def _probe_down(timeout: float = 2.0):
    return False, "connection refused"


@pytest.fixture
def client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


async def test_status_unavailable_when_daemon_down(monkeypatch, client):
    monkeypatch.setattr(ollama_process, "is_running", _probe_down)
    async with client as c:
        response = await c.get("/api/ollama/status")
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "unavailable"
    assert "refused" in body["reason"]
    assert body["version"] is None
    assert body["modelCount"] is None


async def test_status_running_reports_details(monkeypatch, client):
    monkeypatch.setattr(ollama_process, "is_running", _probe_ok)

    class _Response:
        status_code = 200

        def json(self):
            return {"version": "0.12.0"}

    class _Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, path):
            return _Response()

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _Client())

    import app.services.ollama.service as svc

    class _Adapter:
        async def list_models(self):
            from app.services.runtime.base import ModelInfo

            return [ModelInfo(name="llama3.1", size_bytes=4_700_000_000)]

    monkeypatch.setattr(svc, "get_ollama_adapter", lambda: _Adapter())

    async with client as c:
        response = await c.get("/api/ollama/status")
    body = response.json()
    assert body["status"] == "running"
    assert body["version"] == "0.12.0"
    assert body["modelCount"] == 1
    assert body["endpoint"]


async def test_start_when_already_running_is_noop(monkeypatch, client):
    # The already-running guard lives inside process.start(); with a healthy
    # probe it must return early without spawning anything.
    monkeypatch.setattr(ollama_process, "is_running", _probe_ok)

    def fail_spawn(*args, **kwargs):
        raise AssertionError("spawn must not run when Ollama is already up")

    monkeypatch.setattr(ollama_process, "_spawn_daemon", fail_spawn)
    async with client as c:
        response = await c.post("/api/ollama/start")
    body = response.json()
    assert body["ok"] is True
    assert body["changed"] is False
    assert body["status"] == "running"


async def test_start_failure_returns_real_error(monkeypatch, client):
    async def down(timeout: float = 2.0):
        return False, "connection refused"

    monkeypatch.setattr(ollama_process, "is_running", down)

    async def fail_start():
        return {"changed": True, "running": False, "error": "Ollama executable not found."}

    monkeypatch.setattr(ollama_process, "start", fail_start)
    async with client as c:
        response = await c.post("/api/ollama/start")
    body = response.json()
    assert body["ok"] is False
    assert "executable not found" in body["error"]
    assert body["status"] == "error"


async def test_stop_when_not_running_is_noop(monkeypatch, client):
    async def down(timeout: float = 2.0):
        return False, "connection refused"

    monkeypatch.setattr(ollama_process, "is_running", down)
    async with client as c:
        response = await c.post("/api/ollama/stop")
    body = response.json()
    assert body["ok"] is True
    assert body["changed"] is False
    assert body["status"] == "stopped"


async def test_restart_verifies_running(monkeypatch, client):
    async def ok(timeout: float = 2.0):
        return True, None

    monkeypatch.setattr(ollama_process, "is_running", ok)
    async def fake_restart():
        return {"changed": True, "running": True}

    monkeypatch.setattr(ollama_process, "restart", fake_restart)
    async with client as c:
        response = await c.post("/api/ollama/restart")
    body = response.json()
    assert body["ok"] is True
    assert body["status"] == "running"
