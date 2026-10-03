"""Health endpoint behaviour for connected and degraded dependency states."""

from __future__ import annotations

import httpx
import pytest

from app.db.session import Database
from app.main import app
from app.services.runtime.ollama import OllamaAdapter
from app.services.system.db_init import DatabaseReport


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


async def _fake_db_running():
    return DatabaseReport(status="running", postgres=True, pgvector=True, schema=True)


async def _fake_db_misconfigured():
    return DatabaseReport(
        status="misconfigured",
        postgres=True,
        pgvector=False,
        schema=False,
        detail="PostgreSQL is reachable but the pgvector extension is not available.",
    )


async def test_health_reports_connected(monkeypatch):
    monkeypatch.setattr(Database, "ping", _fake_ping_ok)
    monkeypatch.setattr(OllamaAdapter, "health", _fake_ollama_ok)
    monkeypatch.setattr("app.api.routes.health.inspect_database", _fake_db_running)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["services"]["postgres"]["status"] == "connected"
    assert body["services"]["ollama"]["status"] == "connected"


async def test_health_degrades_when_pgvector_missing(monkeypatch):
    monkeypatch.setattr(Database, "ping", _fake_ping_ok)
    monkeypatch.setattr(OllamaAdapter, "health", _fake_ollama_ok)
    monkeypatch.setattr("app.api.routes.health.inspect_database", _fake_db_misconfigured)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["services"]["postgres"]["status"] == "degraded"


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


async def test_health_reports_memory_available(monkeypatch):
    monkeypatch.setattr(Database, "ping", _fake_ping_ok)
    monkeypatch.setattr(OllamaAdapter, "health", _fake_ollama_ok)
    monkeypatch.setattr("app.api.routes.health.inspect_database", _fake_db_running)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/health")
    body = response.json()
    assert body["services"]["memory"]["status"] == "connected"


async def test_database_health_endpoint_reports_rich_state(monkeypatch):
    from app.db.health import get_database_health

    get_database_health().mark_connected(
        pgvector=True, schema=True, migration="0001_initial"
    )
    monkeypatch.setattr(Database, "ping", _fake_ping_ok)
    monkeypatch.setattr("app.api.routes.health.inspect_database", _fake_db_running)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/health/database")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "connected"
    assert body["memory"] == "available"
    assert body["ready"] is True
    assert body["pgvector"] is True


async def test_database_health_endpoint_when_down(monkeypatch):
    monkeypatch.setattr(Database, "ping", _fake_ping_down)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/health/database")
    assert response.status_code == 200
    body = response.json()
    # A down database is reported as a real state, never as connected.
    assert body["state"] in ("disconnected", "error")
    assert body["ready"] is False
    assert body["memory"] in ("unavailable", "error")


async def test_api_meta_reports_valid_runtime_endpoint(monkeypatch):
    """The runtime meta endpoint (never the UI) exposes endpoint diagnostics."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "INTLLM"
    endpoint = body["runtime_endpoint"]
    assert endpoint["host"] == "127.0.0.1"
    assert endpoint["port"] == 8000
    assert endpoint["base_url"] == "http://127.0.0.1:8000"
    assert endpoint["validated"] is True
    # The broken historical fields are gone.
    assert "port_supplied" not in endpoint
