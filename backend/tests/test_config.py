"""Configuration and INTLLM runtime endpoint validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config.settings import Settings


def test_default_port_is_plan_value():
    settings = Settings(INTLLM_DATABASE_URL="postgresql+asyncpg://x/y")
    assert settings.intllm_port == 8000


def test_invalid_port_rejected():
    with pytest.raises(ValidationError):
        Settings(INTLLM_PORT=240426, INTLLM_DATABASE_URL="postgresql+asyncpg://x/y")


def test_runtime_endpoint_defaults_are_loopback_and_valid(settings):
    """The runtime endpoint is a real, dialable loopback endpoint.

    The historical broken build advertised host 172.22.0.1 with the invalid
    port 240426 (``port_supplied``). Those fields no longer exist and the
    defaults must always describe a valid TCP endpoint.
    """
    endpoint = settings.runtime_endpoint
    assert endpoint["host"] == "127.0.0.1"
    assert endpoint["port"] == 8000
    assert endpoint["base_url"] == "http://127.0.0.1:8000"
    assert endpoint["validated"] is True
    # Deprecated diagnostics-only fields are gone.
    assert "port_supplied" not in endpoint
    assert "port_supplied_is_valid" not in endpoint
    assert "port_status" not in endpoint


def test_runtime_endpoint_respects_explicit_overrides():
    settings = Settings(
        INTLLM_RUNTIME_PORT="8010",
        INTLLM_DATABASE_URL="postgresql+asyncpg://x/y",
    )
    endpoint = settings.runtime_endpoint
    assert endpoint["port"] == 8010
    assert endpoint["base_url"] == "http://127.0.0.1:8010"
    assert endpoint["validated"] is True


def test_database_url_rejects_non_loopback_wsl_host():
    with pytest.raises(ValidationError) as excinfo:
        Settings(INTLLM_DATABASE_URL="postgresql+asyncpg://u:p@172.22.0.1:5432/db")
    assert "172.22.0.1" in str(excinfo.value)


def test_cors_origins_parsed():
    settings = Settings(
        INTLLM_CORS_ORIGINS="http://a:1, http://b:2",
        INTLLM_DATABASE_URL="postgresql+asyncpg://x/y",
    )
    assert settings.cors_origins == ["http://a:1", "http://b:2"]
