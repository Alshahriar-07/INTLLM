"""System / hardware telemetry endpoints."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.sse import SSE_HEADERS
from app.schemas import SystemStatusResponse
from app.services.system.service import get_hardware_service, get_system_service

router = APIRouter(tags=["system"])


async def _build_status() -> SystemStatusResponse:
    hardware = await get_hardware_service().snapshot()
    status = await get_system_service().status()
    frontend_services = {
        "intllm": status["intllm"]["status"] == "connected",
        "ollama": status["ollama"]["status"] == "connected",
        "postgres": status["postgres"]["status"] == "connected",
        "web": status["web"]["status"] == "connected",
        "browser": bool(status["browser"]["status"]),
    }
    return SystemStatusResponse(
        connected=True,
        cpu=hardware["cpu"],
        ram=hardware["ram"],
        gpu=hardware["gpu"],
        disk=hardware["disk"],
        os=hardware["os"],
        services={**frontend_services, "detail": status},
        capturedAt=hardware["captured_at"],
    )


@router.get("/system", response_model=SystemStatusResponse)
async def get_system() -> SystemStatusResponse:
    return await _build_status()


@router.get("/system/services")
async def get_services() -> dict[str, object]:
    return await get_system_service().status()


@router.get("/system/stream")
async def stream_system(interval: float = 3.0) -> StreamingResponse:
    async def generator():
        while True:
            payload = await _build_status()
            yield f"event: system.metrics\ndata: {json.dumps(payload.model_dump(), default=str)}\n\n"
            await asyncio.sleep(max(1.0, min(interval, 30.0)))

    return StreamingResponse(generator(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.get("/system/time")
async def server_time() -> dict[str, str]:
    return {"time": datetime.now(timezone.utc).isoformat()}
