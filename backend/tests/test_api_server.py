"""Local OpenAI-compatible API: server status, networking and key management.

External boundaries (PostgreSQL, Ollama, the OS network stack) are mocked so the
real route/middleware/service logic is exercised. No test fabricates runtime
data.
"""

from __future__ import annotations

import socket
import uuid
from dataclasses import field
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import ClassVar

import httpx
import pytest

from app.api.dependencies import require_api_key
from app.api.routes import openai as openai_route
from app.config.settings import Settings
from app.db.repositories.keys import ApiKeyRepository
from app.main import app
from app.services.api_server.service import (
    ACCESS_MODE_LAN,
    ACCESS_MODE_LOCAL,
    ApiServerService,
    detect_lan_addresses,
    is_loopback_host,
)

LAN_CLIENT = ("192.168.1.50", 55000)
LOCAL_CLIENT = ("127.0.0.1", 55000)


# --- loopback / LAN detection ---------------------------------------------


def test_is_loopback_host():
    assert is_loopback_host("127.0.0.1") is True
    assert is_loopback_host("::1") is True
    assert is_loopback_host("localhost") is True
    assert is_loopback_host("testclient") is True
    assert is_loopback_host("192.168.1.50") is False
    assert is_loopback_host("0.0.0.0") is False
    assert is_loopback_host(None) is False


class _Addr:
    def __init__(self, family, address):
        self.family = family
        self.address = address


def test_detect_lan_addresses_filters_and_orders(monkeypatch):
    import psutil

    monkeypatch.setattr(
        psutil,
        "net_if_addrs",
        lambda: {
            "lo": [_Addr(socket.AF_INET, "127.0.0.1")],
            "eth0": [_Addr(socket.AF_INET, "10.0.0.5"), _Addr(socket.AF_INET6, "::1")],
            "wifi": [
                _Addr(socket.AF_INET, "192.168.0.20"),
                _Addr(socket.AF_INET, "169.254.10.10"),  # link-local excluded
            ],
        },
    )
    assert detect_lan_addresses() == ["192.168.0.20", "10.0.0.5"]


# --- configuration ---------------------------------------------------------


def test_access_mode_validator_and_bind_host():
    local = Settings(INTLLM_DATABASE_URL="postgresql+asyncpg://x/y")
    assert local.intllm_api_access_mode == ACCESS_MODE_LOCAL
    assert local.api_bind_host == local.intllm_host
    assert local.lan_enabled is False

    lan = Settings(
        INTLLM_API_ACCESS_MODE="LAN",
        INTLLM_DATABASE_URL="postgresql+asyncpg://x/y",
    )
    assert lan.intllm_api_access_mode == ACCESS_MODE_LAN
    assert lan.api_bind_host == "0.0.0.0"
    assert lan.lan_enabled is True


def test_invalid_access_mode_rejected():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(INTLLM_API_ACCESS_MODE="public", INTLLM_DATABASE_URL="postgresql+asyncpg://x/y")


# --- service status --------------------------------------------------------


async def test_status_reports_running_when_probe_succeeds(monkeypatch):
    service = ApiServerService()

    async def _ok(self, port):
        return True, None

    monkeypatch.setattr(ApiServerService, "_self_probe", _ok)
    snapshot = await service.status(None)
    assert snapshot["state"] == "running"
    assert snapshot["reachable"] is True
    assert snapshot["localBaseUrl"].startswith("http://127.0.0.1:")
    assert snapshot["localBaseUrl"].endswith("/v1")


async def test_status_reports_error_when_probe_fails(monkeypatch):
    service = ApiServerService()

    async def _fail(self, port):
        return False, "ConnectError: refused"

    monkeypatch.setattr(ApiServerService, "_self_probe", _fail)
    snapshot = await service.status(None)
    assert snapshot["state"] == "error"
    assert snapshot["reachable"] is False
    assert snapshot["detail"] == "ConnectError: refused"


async def test_status_lan_url_populated_when_enabled(monkeypatch):
    service = ApiServerService()

    async def _ok(self, port):
        return True, None

    monkeypatch.setattr(ApiServerService, "_self_probe", _ok)
    monkeypatch.setattr(
        "app.services.api_server.service.get_settings",
        lambda: SimpleNamespace(
            intllm_api_access_mode=ACCESS_MODE_LAN,
            stored_access_mode=None,
            active_api_port=8000,
            api_bind_host="0.0.0.0",
            lan_enabled=True,
            intllm_port=8000,
            intllm_host="127.0.0.1",
        ),
    )
    monkeypatch.setattr(
        "app.services.api_server.service.detect_lan_addresses",
        lambda: ["192.168.1.10"],
    )
    snapshot = await service.status(None)
    assert snapshot["lanEnabled"] is True
    assert snapshot["lanBaseUrl"] == "http://192.168.1.10:8000/v1"


# --- access-control middleware ---------------------------------------------


async def test_lan_client_blocked_from_internal_api(monkeypatch):
    transport = httpx.ASGITransport(app=app, client=LAN_CLIENT)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        response = await c.get("/api/health")
    assert response.status_code == 403
    assert response.json()["error"]["type"] == "permission_error"


async def test_lan_client_blocked_from_v1_when_lan_disabled(monkeypatch):
    monkeypatch.setattr(
        "app.main.get_settings", lambda: SimpleNamespace(lan_enabled=False)
    )
    transport = httpx.ASGITransport(app=app, client=LAN_CLIENT)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        response = await c.get("/v1/models")
    assert response.status_code == 403


async def test_loopback_client_is_allowed(monkeypatch):
    transport = httpx.ASGITransport(app=app, client=LOCAL_CLIENT)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        response = await c.get("/api/health")
    # Reachable (may be degraded), never blocked by the access gate.
    assert response.status_code in (200, 503)


async def test_lan_v1_requires_authentication(monkeypatch):
    """With LAN enabled, /v1 is reachable but a key is still mandatory."""
    monkeypatch.setattr(
        "app.main.get_settings", lambda: SimpleNamespace(lan_enabled=True)
    )
    transport = httpx.ASGITransport(app=app, client=LAN_CLIENT)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        response = await c.get("/v1/models")
    # No credential from a non-loopback address → 401 (never 403/200).
    assert response.status_code == 401


async def test_lan_v1_allows_authenticated_client(monkeypatch):
    monkeypatch.setattr(
        "app.main.get_settings", lambda: SimpleNamespace(lan_enabled=True)
    )
    app.dependency_overrides[require_api_key] = lambda: None

    async def _names(session):
        return ["qwen2.5-coder:7b"]

    monkeypatch.setattr(openai_route, "_list_installed", _names)
    transport = httpx.ASGITransport(app=app, client=LAN_CLIENT)
    try:
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as c:
            response = await c.get("/v1/models")
        assert response.status_code == 200
        assert response.json()["data"][0]["id"] == "qwen2.5-coder:7b"
    finally:
        app.dependency_overrides.clear()


# --- status endpoint -------------------------------------------------------


async def test_status_endpoint_reports_real_state(monkeypatch):
    async def _ok(self, port):
        return True, None

    monkeypatch.setattr(ApiServerService, "_self_probe", _ok)
    transport = httpx.ASGITransport(app=app, client=LOCAL_CLIENT)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        response = await c.get("/api/api-server/status")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "running"
    assert body["reachable"] is True
    assert body["accessMode"] in ("local", "lan")
    assert body["localBaseUrl"].endswith("/v1")
    # Key store is reported unavailable rather than pretending keys exist.
    assert body["keyStoreAvailable"] is False
    assert body["keyCount"] == 0


# --- key management --------------------------------------------------------


class _FakeKeyRepo(ApiKeyRepository):
    existing = None
    fingerprints: ClassVar[list[str]] = field(default_factory=list)

    def __init__(self, session):
        self.session = session

    async def fingerprint_exists(self, fingerprint):
        return fingerprint in _FakeKeyRepo.fingerprints

    async def create(self, *, name, key_prefix, fingerprint, salt, key_hash, scopes):
        record = SimpleNamespace(
            id=uuid.uuid4(),
            name=name,
            key_prefix=key_prefix,
            fingerprint=fingerprint,
            salt=salt,
            key_hash=key_hash,
            scopes=scopes,
            status="active",
            created_at=datetime.now(UTC),
            last_used_at=None,
            last_used_at_utc=None,
            label=None,
            scope_names=set(),
        )
        _FakeKeyRepo.existing = record
        return record

    async def get(self, key_id):
        record = _FakeKeyRepo.existing
        if record is not None and record.id == key_id:
            return record
        return None

    async def revoke(self, key_id):
        if _FakeKeyRepo.existing is not None:
            _FakeKeyRepo.existing.status = "revoked"
            return True
        return False


class _FakeAudit:
    def __init__(self, session):
        self.session = session

    async def record(self, *args, **kwargs):
        return None


def _install_key_fakes(monkeypatch):
    _FakeKeyRepo.existing = None
    _FakeKeyRepo.fingerprints = []
    monkeypatch.setattr(
        "app.services.security.service.ApiKeyRepository", _FakeKeyRepo
    )
    monkeypatch.setattr("app.services.security.service.AuditRepository", _FakeAudit)


async def test_create_key_is_prefixed_and_unique(monkeypatch):
    _install_key_fakes(monkeypatch)
    from app.services.security.service import ApiKeyService

    record, secret = await ApiKeyService().create(object(), name="claude-code")
    assert secret.startswith("intllm_")
    assert record.fingerprint and record.fingerprint not in secret


async def test_create_key_retries_on_fingerprint_collision(monkeypatch):
    _install_key_fakes(monkeypatch)
    from app.core.security import key_fingerprint
    from app.services.security import service as sec

    # The first candidate collides with an existing fingerprint, so the service
    # must discard it and mint another key.
    candidates = iter(["intllm_first_candidate", "intllm_second_candidate"])
    monkeypatch.setattr(sec, "generate_api_key", lambda: next(candidates))
    _FakeKeyRepo.fingerprints = [key_fingerprint("intllm_first_candidate")]
    _record, secret = await sec.ApiKeyService().create(object(), name="collision")
    assert secret == "intllm_second_candidate"


async def test_regenerate_revokes_old_and_issues_new(monkeypatch):
    _install_key_fakes(monkeypatch)
    from app.services.security.service import ApiKeyService

    service = ApiKeyService()
    old, _ = await service.create(object(), name="cli")
    result = await service.regenerate(object(), old.id)
    assert result is not None
    new_record, new_secret = result
    assert new_record.id != old.id
    assert new_record.name == "cli"
    assert new_secret.startswith("intllm_")
    assert old.status == "revoked"


async def test_regenerate_unknown_key_returns_none(monkeypatch):
    _install_key_fakes(monkeypatch)
    from app.services.security.service import ApiKeyService

    assert await ApiKeyService().regenerate(object(), uuid.uuid4()) is None
