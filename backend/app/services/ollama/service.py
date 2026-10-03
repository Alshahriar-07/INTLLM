"""Ollama runtime control service.

State machine over the process manager + live HTTP adapter:
``running | stopped | starting | stopping | unavailable | error``.
Details (version, model count, loaded models, memory) come from the real
daemon; anything the daemon does not expose is reported as ``None`` and
rendered as N/A by the frontend.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx

from app.config.settings import get_settings
from app.core.logging import get_logger
from app.services.ollama import process
from app.services.runtime.ollama import get_ollama_adapter

logger = get_logger(__name__)

# One control operation at a time; concurrent callers see the transition state.
_OP_LOCK = asyncio.Lock()

_VALID_STATES = ("running", "stopped", "starting", "stopping", "unavailable", "error")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class OllamaControlService:
    def __init__(self) -> None:
        self._state: str = "stopped"
        self._last_error: str | None = None
        self._transition_task: asyncio.Task | None = None

    # --- introspection -----------------------------------------------------

    async def describe(self) -> dict[str, Any]:
        """Real snapshot of the daemon. Never invents values."""
        settings = get_settings()
        adapter = get_ollama_adapter()
        available, error = await process.is_running()

        if not available:
            # Keep a transitioning state visible during start/stop calls.
            if self._state not in ("starting", "stopping"):
                self._state = "stopped" if not self._last_error else self._state
            return {
                "status": self._state if self._state in ("starting", "stopping") else "unavailable",
                "endpoint": settings.intllm_ollama_url,
                "version": None,
                "modelCount": None,
                "loadedModels": [],
                "memory": None,
                "reason": error or self._last_error,
                "lastChecked": _now_iso(),
            }

        version: str | None = None
        model_count: int | None = None
        loaded: list[dict[str, Any]] = []
        memory: dict[str, Any] | None = None

        try:
            async with httpx.AsyncClient(
                base_url=settings.intllm_ollama_url.rstrip("/"), timeout=5.0
            ) as client:
                version_response = await client.get("/api/version")
                if version_response.status_code == 200:
                    version = version_response.json().get("version")
        except Exception as exc:  # noqa: BLE001 - optional detail
            logger.warning("ollama version probe failed", extra={"intllm_extra": {"error": str(exc)}})

        try:
            model_count = len(await adapter.list_models())
        except Exception as exc:  # noqa: BLE001
            logger.warning("ollama model listing failed", extra={"intllm_extra": {"error": str(exc)}})

        # Real loaded-model info (Ollama exposes this in /api/ps when models
        # are resident in memory); empty when nothing is loaded.
        try:
            async with httpx.AsyncClient(
                base_url=settings.intllm_ollama_url.rstrip("/"), timeout=5.0
            ) as client:
                ps_response = await client.get("/api/ps")
                if ps_response.status_code == 200:
                    for entry in ps_response.json().get("models", []):
                        size_vram = entry.get("size_vram")
                        loaded.append(
                            {
                                "name": entry.get("name") or entry.get("model"),
                                "sizeBytes": entry.get("size"),
                                "vramBytes": size_vram,
                                "expiresAt": entry.get("expires_at"),
                            }
                        )
                        if size_vram:
                            memory = memory or {"loadedModels": 0, "vramUsedBytes": 0}
                            memory["loadedModels"] += 1
                            memory["vramUsedBytes"] += int(size_vram)
        except Exception as exc:  # noqa: BLE001 - optional detail
            logger.warning("ollama ps probe failed", extra={"intllm_extra": {"error": str(exc)}})

        self._state = "running"
        self._last_error = None
        return {
            "status": "running",
            "endpoint": settings.intllm_ollama_url,
            "version": version,
            "modelCount": model_count,
            "loadedModels": loaded,
            "memory": memory,
            "reason": None,
            "lastChecked": _now_iso(),
        }

    # --- lifecycle ---------------------------------------------------------

    async def _apply(self, operation: str) -> dict[str, Any]:
        if operation == "start":
            self._state = "starting"
            result = await process.start()
            self._state = "running" if result.get("running") else "error"
        elif operation == "stop":
            self._state = "stopping"
            result = await process.stop()
            self._state = "stopped" if not result.get("running") else "error"
        elif operation == "restart":
            self._state = "starting"
            result = await process.restart()
            self._state = "running" if result.get("running") else "error"
        else:  # pragma: no cover
            result = {"error": f"Unknown operation: {operation}"}
        if result.get("error"):
            self._last_error = result["error"]
        else:
            self._last_error = None
        return result

    async def _run_operation(self, operation: str) -> dict[str, Any]:
        if self._transition_task and not self._transition_task.done():
            return {
                "ok": False,
                "status": self._state,
                "error": f"An Ollama {self._state} operation is already in progress",
            }
        async with _OP_LOCK:
            try:
                result = await self._apply(operation)
            except Exception as exc:
                logger.exception("ollama control failed", exc_info=exc)
                self._state = "error"
                self._last_error = str(exc)
                result = {"ok": False, "error": str(exc)}
        return {"ok": not result.get("error"), "status": self._state, **result}

    async def start(self) -> dict[str, Any]:
        return await self._run_operation("start")

    async def stop(self) -> dict[str, Any]:
        return await self._run_operation("stop")

    async def restart(self) -> dict[str, Any]:
        return await self._run_operation("restart")

    @property
    def state(self) -> str:
        return self._state


_control: OllamaControlService | None = None


def get_ollama_control_service() -> OllamaControlService:
    global _control
    if _control is None:
        _control = OllamaControlService()
    return _control
