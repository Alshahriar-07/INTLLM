"""Local OpenAI-compatible API server status and access control.

The REST API lives on the same FastAPI process as the internal management API.
This service answers two questions for the UI without ever faking state:

* Is the API genuinely reachable? (a real loopback health probe)
* Which access mode is active, and is a restart required to change it?

Access modes:

* ``local`` — the process binds the loopback interface; only same-machine
  applications (and the local web UI) can reach it.
* ``lan``   — the process binds the LAN interface. The public ``/v1`` API is
  reachable from the same network and still requires an API key; internal
  ``/api`` management routes stay loopback-only (enforced by middleware).

The selected mode is persisted in ``app_settings`` so it survives a restart.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.core.logging import get_logger
from app.db.models import AppSetting

logger = get_logger(__name__)

ACCESS_MODE_LOCAL = "local"
ACCESS_MODE_LAN = "lan"
ACCESS_SETTING_KEY = "api_access_mode"

STATE_STARTING = "starting"
STATE_RUNNING = "running"
STATE_STOPPED = "stopped"
STATE_ERROR = "error"
STATE_RESTARTING = "restarting"

# Health probe timeout: the API must answer, not merely accept a socket.
_PROBE_TIMEOUT_SECONDS = 2.0


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def detect_lan_addresses() -> list[str]:
    """Return usable private LAN IPv4 addresses for this machine.

    Loopback, link-local (169.254.x), and non-private addresses are excluded.
    Results are ordered so the most conventional LAN range (192.168) is first.
    """
    try:
        import psutil
    except ImportError:  # pragma: no cover - psutil is a hard dependency
        return []

    found: set[str] = set()
    try:
        interfaces = psutil.net_if_addrs()
    except Exception:  # noqa: BLE001 - network enumeration is best-effort
        return []

    for addresses in interfaces.values():
        for entry in addresses:
            if entry.family != socket.AF_INET:
                continue
            raw = (entry.address or "").split("%")[0]
            try:
                address = ipaddress.IPv4Address(raw)
            except ValueError:
                continue
            if address.is_loopback or address.is_link_local or not address.is_private:
                continue
            found.add(str(address))

    def _rank(value: str) -> tuple[int, str]:
        if value.startswith("192.168."):
            return (0, value)
        if value.startswith("10."):
            return (1, value)
        return (2, value)

    return sorted(found, key=_rank)


class ApiServerService:
    async def _self_probe(self, port: int) -> tuple[bool, str | None]:
        """Hit the real loopback health endpoint. Never assume success."""
        try:
            async with httpx.AsyncClient(timeout=_PROBE_TIMEOUT_SECONDS) as client:
                response = await client.get(f"http://127.0.0.1:{port}/api/health")
            # 200 (ok) and 503 (degraded dependency) both prove the server serves.
            if response.status_code in (200, 503):
                return True, None
            return False, f"HTTP {response.status_code}"
        except Exception as exc:  # noqa: BLE001 - reported as a real state
            return False, f"{type(exc).__name__}: {exc}"

    # --- access mode persistence -----------------------------------------
    async def stored_access_mode(self, session: AsyncSession | None) -> str | None:
        if session is None:
            return None
        try:
            record = await session.scalar(
                select(AppSetting).where(AppSetting.key == ACCESS_SETTING_KEY)
            )
        except Exception:  # noqa: BLE001 - settings are best-effort
            return None
        if record is not None and isinstance(record.value, dict):
            mode = str(record.value.get("mode", "")).strip().lower()
            if mode in (ACCESS_MODE_LOCAL, ACCESS_MODE_LAN):
                return mode
        return None

    async def set_access_mode(self, session: AsyncSession, mode: str) -> str:
        normalized = (mode or "").strip().lower()
        if normalized not in (ACCESS_MODE_LOCAL, ACCESS_MODE_LAN):
            from app.core.errors import ValidationError

            raise ValidationError("mode must be 'local' or 'lan'")
        record = await session.scalar(
            select(AppSetting).where(AppSetting.key == ACCESS_SETTING_KEY)
        )
        value = {"mode": normalized}
        if record is not None:
            record.value = value
        else:
            session.add(AppSetting(key=ACCESS_SETTING_KEY, value=value))
        await session.flush()
        return normalized

    # --- status ----------------------------------------------------------
    async def status(
        self, session: AsyncSession | None = None, *, probe: bool = True
    ) -> dict[str, Any]:
        settings = get_settings()
        active_mode = settings.intllm_api_access_mode
        stored_mode = await self.stored_access_mode(session) or active_mode
        port = settings.active_api_port
        local_url = f"http://127.0.0.1:{port}/v1"

        lan_addresses = detect_lan_addresses()
        lan_enabled = active_mode == ACCESS_MODE_LAN
        lan_url = (
            f"http://{lan_addresses[0]}:{port}/v1"
            if lan_enabled and lan_addresses
            else None
        )

        if probe:
            reachable, probe_error = await self._self_probe(port)
        else:
            reachable, probe_error = True, None

        overall_state = STATE_RUNNING if reachable else STATE_ERROR
        detail = probe_error
        if overall_state == STATE_RUNNING and stored_mode != active_mode:
            detail = (
                "Access mode change is pending: restart INTLLM to bind the "
                f"{stored_mode} interface."
            )

        return {
            "state": overall_state,
            "reachable": reachable,
            "accessMode": active_mode,
            "storedAccessMode": stored_mode,
            "lanEnabled": lan_enabled,
            "requiresRestart": stored_mode != active_mode,
            "bindHost": settings.api_bind_host,
            "port": port,
            "localBaseUrl": local_url,
            "lanBaseUrl": lan_url,
            "lanAddresses": lan_addresses,
            "detail": detail,
            "checkedAt": _now_iso(),
        }


_service: ApiServerService | None = None


def get_api_server_service() -> ApiServerService:
    global _service
    if _service is None:
        _service = ApiServerService()
    return _service


def apply_persisted_access_mode() -> None:
    """Apply the stored access mode to the process environment at startup.

    The launcher calls this after the database is initialized, before uvicorn
    binds, so a mode change made in the UI takes effect on the next launch
    without the user editing environment variables. Never raises.
    """

    async def _run() -> None:
        from app.config.settings import get_settings
        from app.db.session import get_database

        database = get_database()
        try:
            available, _ = await database.ping()
            if not available:
                return
            async with database.session() as session:
                mode = await get_api_server_service().stored_access_mode(session)
            if mode:
                import os

                os.environ["INTLLM_API_ACCESS_MODE"] = mode
                get_settings.cache_clear()
        finally:
            await database.dispose()

    try:
        asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001 - startup must never fail on this
        logger.warning(
            "could not apply persisted API access mode",
            extra={"intllm_extra": {"error": str(exc)}},
        )


def is_loopback_host(host: str | None) -> bool:
    """True for the loopback aliases used by browsers, tests and the OS."""
    if not host:
        return False
    if host in ("localhost", "::1", "testclient"):
        return True
    try:
        return ipaddress.ip_address(host.split("%")[0]).is_loopback
    except ValueError:
        return False
