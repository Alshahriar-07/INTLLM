"""Environment-driven application settings.

All values come from environment variables (optionally loaded from a local
``.env`` file). Secrets are never baked into code and never logged.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Valid TCP/UDP port range. The project owner supplied 240426 for the INTLLM
# runtime, which is outside this range and therefore cannot be bound or dialed.
VALID_PORT_MIN = 0
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

    # --- INTLLM runtime endpoint (advertised, not necessarily this server) --
    intllm_runtime_host: str = Field(default="172.22.0.1", alias="INTLLM_RUNTIME_HOST")
    intllm_runtime_port: str | None = Field(default=None, alias="INTLLM_RUNTIME_PORT")
    intllm_runtime_base_url: str | None = Field(default=None, alias="INTLLM_RUNTIME_BASE_URL")
    intllm_runtime_port_supplied: str = Field(
        default="240426", alias="INTLLM_RUNTIME_PORT_SUPPLIED"
    )
    intllm_runtime_port_status: str = Field(
        default="requires_validation", alias="INTLLM_RUNTIME_PORT_STATUS"
    )

    # --- PostgreSQL --------------------------------------------------------
    intllm_database_url: str = Field(
        default="postgresql+asyncpg://intllm:intllm@127.0.0.1:5432/intllm",
        alias="INTLLM_DATABASE_URL",
    )
    intllm_database_url_sync: str = Field(
        default="postgresql+psycopg://intllm:intllm@127.0.0.1:5432/intllm",
        alias="INTLLM_DATABASE_URL_SYNC",
    )

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

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.intllm_cors_origins.split(",") if origin.strip()]

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

        ``port_supplied`` (240426) is preserved verbatim and flagged as invalid
        rather than being silently replaced with a different port.
        """
        parsed_port: int | None = None
        if self.intllm_runtime_port:
            try:
                candidate = int(self.intllm_runtime_port)
                if VALID_PORT_MIN <= candidate <= VALID_PORT_MAX:
                    parsed_port = candidate
            except ValueError:
                parsed_port = None

        base_url = self.intllm_runtime_base_url
        if not base_url and parsed_port is not None:
            base_url = f"http://{self.intllm_runtime_host}:{parsed_port}"

        return {
            "host": self.intllm_runtime_host,
            "port": parsed_port,
            "port_supplied": self.intllm_runtime_port_supplied,
            "port_supplied_is_valid": _is_valid_port_supplied(self.intllm_runtime_port_supplied),
            "port_status": self.intllm_runtime_port_status,
            "base_url": base_url or None,
            "validated": parsed_port is not None,
        }


def _is_valid_port_supplied(raw: str) -> bool:
    try:
        return VALID_PORT_MIN <= int(raw) <= VALID_PORT_MAX
    except (TypeError, ValueError):
        return False


@lru_cache
def get_settings() -> Settings:
    return Settings()
