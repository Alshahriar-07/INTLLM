"""Environment-driven application settings.

All values come from environment variables (optionally loaded from a local
``.env`` file). Secrets are never baked into code and never logged.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Valid TCP port range.
VALID_PORT_MIN = 1
VALID_PORT_MAX = 65535


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application -------------------------------------------------------
    intllm_env: str = Field(default="development", alias="INTLLM_ENV")
    intllm_host: str = Field(default="127.0.0.1", alias="INTLLM_HOST")
    intllm_port: int = Field(default=8000, alias="INTLLM_PORT")

    @field_validator("intllm_runtime_port", "intllm_port")
    @classmethod
    def _validate_runtime_port(cls, value: int) -> int:
        if value is not None and not (VALID_PORT_MIN <= value <= VALID_PORT_MAX):
            raise ValueError(
                f"INTLLM runtime port must be a valid TCP port ({VALID_PORT_MIN}-{VALID_PORT_MAX}); "
                f"got {value}. The value 240426 is not a valid port and must not be used."
            )
        return value
    intllm_log_level: str = Field(default="INFO", alias="INTLLM_LOG_LEVEL")
    intllm_api_prefix: str = Field(default="/api", alias="INTLLM_API_PREFIX")
    intllm_cors_origins: str = Field(
        default="http://127.0.0.1:3000,http://localhost:3000",
        alias="INTLLM_CORS_ORIGINS",
    )
    # Reject oversized request bodies before they are parsed (10 MiB default).
    intllm_max_request_bytes: int = Field(
        default=10 * 1024 * 1024, alias="INTLLM_MAX_REQUEST_BYTES"
    )

    # --- Local API access mode --------------------------------------------
    # "local" binds the whole backend to the loopback interface only.
    # "lan" binds to the LAN interface; the public /v1 API becomes reachable
    # from the same network (authentication is always required and internal
    # /api management routes stay loopback-only). Default is the safe option.
    intllm_api_access_mode: str = Field(default="local", alias="INTLLM_API_ACCESS_MODE")
    # Interface used when LAN access is enabled (all interfaces by default).
    intllm_api_lan_host: str = Field(default="0.0.0.0", alias="INTLLM_API_LAN_HOST")

    # --- INTLLM runtime endpoint (this server's actual listening address) ---
    # This is NOT a separate runtime ID. It is the real host:port the backend
    # binds to and the frontend connects to. The deprecated 240426 value was
    # never a valid TCP port and must not be used anywhere.
    intllm_runtime_host: str = Field(default="127.0.0.1", alias="INTLLM_RUNTIME_HOST")
    intllm_runtime_port: int | None = Field(default=None, alias="INTLLM_RUNTIME_PORT")
    intllm_runtime_base_url: str | None = Field(default=None, alias="INTLLM_RUNTIME_BASE_URL")

    # --- PostgreSQL --------------------------------------------------------
    intllm_database_url: str = Field(
        default="postgresql+asyncpg://intllm:intllm@127.0.0.1:5432/intllm",
        alias="INTLLM_DATABASE_URL",
    )

    @field_validator("intllm_database_url")
    @classmethod
    def _validate_database_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("INTLLM_DATABASE_URL must not be empty")
        if "172.22.0.1" in value:
            raise ValueError(
                "INTLLM_DATABASE_URL must not use 172.22.0.1. Use 127.0.0.1 for local PostgreSQL."
            )
        return value
    intllm_database_url_sync: str = Field(
        default="postgresql+psycopg://intllm:intllm@127.0.0.1:5432/intllm",
        alias="INTLLM_DATABASE_URL_SYNC",
    )
    # Bounded connect/command timeout so a down PostgreSQL cannot hang startup
    # or a request for the OS TCP timeout.
    intllm_db_connect_timeout_seconds: float = Field(
        default=5.0, alias="INTLLM_DB_CONNECT_TIMEOUT_SECONDS"
    )
    # On a fresh local install the configured database may not exist yet.
    # INTLLM creates it (CREATE DATABASE only, never DROP) when this is enabled.
    intllm_db_auto_create: bool = Field(default=True, alias="INTLLM_DB_AUTO_CREATE")

    # --- Ollama ------------------------------------------------------------
    intllm_ollama_url: str = Field(default="http://127.0.0.1:11434", alias="INTLLM_OLLAMA_URL")
    intllm_ollama_timeout_seconds: float = Field(
        default=120.0, alias="INTLLM_OLLAMA_TIMEOUT_SECONDS"
    )
    intllm_default_model: str = Field(default="", alias="INTLLM_DEFAULT_MODEL")

    # --- Data / workspace --------------------------------------------------
    intllm_data_dir: str = Field(default="./data", alias="INTLLM_DATA_DIR")
    intllm_workspace_dir: str = Field(default="./workspace", alias="INTLLM_WORKSPACE_DIR")
    intllm_filesystem_allowlist: str = Field(
        default="./workspace", alias="INTLLM_FILESYSTEM_ALLOWLIST"
    )

    # --- Agent mode / workspace -------------------------------------------
    # The Agent's filesystem boundary is the user-selected workspace. Paths
    # outside it are rejected; destructive operations require approval.
    intllm_agent_terminal_enabled: bool = Field(
        default=True, alias="INTLLM_AGENT_TERMINAL_ENABLED"
    )
    intllm_agent_terminal_timeout_seconds: float = Field(
        default=60.0, alias="INTLLM_AGENT_TERMINAL_TIMEOUT_SECONDS"
    )
    intllm_agent_max_read_bytes: int = Field(
        default=200_000, alias="INTLLM_AGENT_MAX_READ_BYTES"
    )
    intllm_agent_max_write_bytes: int = Field(
        default=2_000_000, alias="INTLLM_AGENT_MAX_WRITE_BYTES"
    )
    intllm_agent_max_search_results: int = Field(
        default=200, alias="INTLLM_AGENT_MAX_SEARCH_RESULTS"
    )

    # --- Web retrieval -----------------------------------------------------
    intllm_web_provider: str = Field(default="duckduckgo", alias="INTLLM_WEB_PROVIDER")
    intllm_web_searxng_url: str = Field(default="", alias="INTLLM_WEB_SEARXNG_URL")
    intllm_web_timeout_seconds: float = Field(default=15.0, alias="INTLLM_WEB_TIMEOUT_SECONDS")
    intllm_web_max_results: int = Field(default=8, alias="INTLLM_WEB_MAX_RESULTS")

    # --- Browser -----------------------------------------------------------
    intllm_browser_enabled: bool = Field(default=True, alias="INTLLM_BROWSER_ENABLED")
    intllm_browser_headless: bool = Field(default=True, alias="INTLLM_BROWSER_HEADLESS")
    intllm_browser_timeout_seconds: float = Field(
        default=30.0, alias="INTLLM_BROWSER_TIMEOUT_SECONDS"
    )

    # --- Background learning ----------------------------------------------
    intllm_max_background_workers: int = Field(default=1, alias="INTLLM_MAX_BACKGROUND_WORKERS")
    intllm_background_poll_seconds: float = Field(
        default=5.0, alias="INTLLM_BACKGROUND_POLL_SECONDS"
    )
    intllm_background_latency_threshold_ms: float = Field(
        default=1500.0, alias="INTLLM_BACKGROUND_LATENCY_THRESHOLD_MS"
    )
    intllm_background_cpu_threshold_percent: float = Field(
        default=85.0, alias="INTLLM_BACKGROUND_CPU_THRESHOLD_PERCENT"
    )
    intllm_background_ram_threshold_percent: float = Field(
        default=90.0, alias="INTLLM_BACKGROUND_RAM_THRESHOLD_PERCENT"
    )

    @field_validator("intllm_port")
    @classmethod
    def _validate_port(cls, value: int) -> int:
        if not VALID_PORT_MIN <= value <= VALID_PORT_MAX:
            raise ValueError(
                f"INTLLM_PORT must be a valid TCP port ({VALID_PORT_MIN}-{VALID_PORT_MAX}); "
                f"got {value}."
            )
        return value

    @field_validator("intllm_max_request_bytes")
    @classmethod
    def _validate_max_request_bytes(cls, value: int) -> int:
        if value < 1024:
            raise ValueError("INTLLM_MAX_REQUEST_BYTES must be at least 1024 bytes")
        return value

    @field_validator("intllm_db_connect_timeout_seconds")
    @classmethod
    def _validate_db_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("INTLLM_DB_CONNECT_TIMEOUT_SECONDS must be greater than 0")
        return value

    @field_validator("intllm_api_access_mode")
    @classmethod
    def _validate_access_mode(cls, value: str) -> str:
        normalized = (value or "local").strip().lower()
        if normalized not in ("local", "lan"):
            raise ValueError(
                "INTLLM_API_ACCESS_MODE must be 'local' or 'lan'; "
                f"got {value!r}."
            )
        return normalized

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.intllm_cors_origins.split(",") if origin.strip()]

    @property
    def api_bind_host(self) -> str:
        """Interface the backend binds to for the current access mode."""
        if self.intllm_api_access_mode == "lan":
            return self.intllm_api_lan_host
        return self.intllm_host

    @property
    def active_api_port(self) -> int:
        """The port actually being served (launcher port-conflict fallback wins)."""
        raw = os.environ.get("INTLLM_EFFECTIVE_PORT", "").strip()
        if raw:
            try:
                candidate = int(raw)
                if VALID_PORT_MIN <= candidate <= VALID_PORT_MAX:
                    return candidate
            except ValueError:
                pass
        return self.intllm_port

    @property
    def lan_enabled(self) -> bool:
        return self.intllm_api_access_mode == "lan"

    @property
    def filesystem_allowlist(self) -> list[Path]:
        return [
            Path(p.strip()).expanduser().resolve()
            for p in self.intllm_filesystem_allowlist.split(",")
            if p.strip()
        ]

    @property
    def data_dir(self) -> Path:
        return Path(self.intllm_data_dir).expanduser().resolve()

    @property
    def workspace_dir(self) -> Path:
        return Path(self.intllm_workspace_dir).expanduser().resolve()

    @property
    def runtime_endpoint(self) -> dict[str, object]:
        """Non-secret description of the configured INTLLM runtime endpoint.

        The effective port is the one the server actually binds to
        (INTLLM_EFFECTIVE_PORT if set by the launcher's port-resolution step,
        otherwise intllm_port). Host defaults to 127.0.0.1.
        """
        host = self.intllm_runtime_host or "127.0.0.1"
        port: int | None = None

        # Launcher-set effective port wins (handles port conflicts / fallback).
        raw = os.environ.get("INTLLM_EFFECTIVE_PORT", "").strip()
        if raw:
            try:
                candidate = int(raw)
                if VALID_PORT_MIN <= candidate <= VALID_PORT_MAX:
                    port = candidate
            except ValueError:
                pass

        if port is None:
            try:
                candidate = int(self.intllm_runtime_port) if self.intllm_runtime_port is not None else self.intllm_port
                if VALID_PORT_MIN <= candidate <= VALID_PORT_MAX:
                    port = candidate
            except (ValueError, TypeError):
                port = self.intllm_port

        base_url = self.intllm_runtime_base_url
        if not base_url and port is not None:
            base_url = f"http://{host}:{port}"

        validated = port is not None and 1 <= port <= 65535
        return {
            "host": host,
            "port": port if validated else None,
            "base_url": base_url or None,
            "validated": validated,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
