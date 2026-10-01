"""Configuration and INTLLM runtime endpoint validation."""

from __future__ import annotations

import pytest
from app.config.settings import Settings
from pydantic import ValidationError


def test_default_port_is_plan_value():
    settings = Settings(INTLLM_DATABASE_URL="postgresql+asyncpg://x/y")
    assert settings.intllm_port == 8000


def test_invalid_port_rejected():
    with pytest.raises(ValidationError):
        Settings(INTLLM_PORT=240426, INTLLM_DATABASE_URL="postgresql+asyncpg://x/y")


def test_supplied_runtime_port_flagged_as_invalid(settings):
    endpoint = settings.runtime_endpoint
    assert endpoint["host"] == "172.22.0.1"
    assert endpoint["port_supplied"] == "240426"
    assert endpoint["port_supplied_is_valid"] is False
    assert endpoint["validated"] is False
    # The invalid port must never be turned into a dialable base URL.
    assert endpoint["base_url"] is None


def test_valid_runtime_port_builds_base_url():
    settings = Settings(
        INTLLM_RUNTIME_HOST="172.22.0.1",
        INTLLM_RUNTIME_PORT="8000",
        INTLLM_DATABASE_URL="postgresql+asyncpg://x/y",
    )
    endpoint = settings.runtime_endpoint
    assert endpoint["validated"] is True
    assert endpoint["base_url"] == "http://172.22.0.1:8000"


def test_cors_origins_parsed():
    settings = Settings(
        INTLLM_CORS_ORIGINS="http://a:1, http://b:2",
        INTLLM_DATABASE_URL="postgresql+asyncpg://x/y",
    )
    assert settings.cors_origins == ["http://a:1", "http://b:2"]
