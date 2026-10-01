"""Health endpoint behaviour for connected and degraded dependency states."""

from __future__ import annotations

import httpx
import pytest
from app.db.session import Database
from app.main import app
from app.services.runtime.ollama import OllamaAdapter


@pytest.fixture
def client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


async def _fake_ping_ok(self):
    return True, None


async def _fake_ping_down(self):
    return False, "connection refused"


async def _fake_ollama_ok(self):
    return True, None


async def _fake_ollama_down(self):
    return False, "connection refused"


async def test_health_reports_connected(monkeypatch):
    monkeypatch.setattr(Database, "ping", _fake_ping_ok)
    monkeypatch.setattr(OllamaAdapter, "health", _fake_ollama_ok)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["services"]["postgres"]["status"] == "connected"
    assert body["services"]["ollama"]["status"] == "connected"


async def test_health_degrades_when_postgres_down(monkeypatch):
    monkeypatch.setattr(Database, "ping", _fake_ping_down)
    monkeypatch.setattr(OllamaAdapter, "health", _fake_ollama_down)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["services"]["postgres"]["status"] == "offline"
    # The reason is reported, never a fabricated "connected".
    assert "refused" in body["services"]["postgres"]["detail"]


async def test_root_exposes_runtime_endpoint(monkeypatch):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/")
    body = response.json()
    endpoint = body["runtime_endpoint"]
    assert endpoint["port_supplied"] == "240426"
    assert endpoint["validated"] is False
