"""Test configuration.

Tests run without a live PostgreSQL or Ollama daemon: external boundaries are
monkeypatched. No test asserts fabricated runtime data.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("INTLLM_ENV", "test")
os.environ.setdefault("INTLLM_BROWSER_ENABLED", "false")
os.environ.setdefault("INTLLM_LOG_LEVEL", "WARNING")
os.environ.setdefault(
    "INTLLM_DATABASE_URL", "postgresql+asyncpg://intllm:intllm@127.0.0.1:5432/intllm_test"
)


@pytest.fixture
def settings():
    from app.config.settings import Settings

    return Settings(
        INTLLM_DATABASE_URL="postgresql+asyncpg://intllm:intllm@127.0.0.1:5432/intllm_test",
        INTLLM_BROWSER_ENABLED=False,
    )
