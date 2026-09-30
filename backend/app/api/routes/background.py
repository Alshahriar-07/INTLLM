"""Background learning endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.sse import SSE_HEADERS, sse_from_events
from app.core.events import event_bus
from app.schemas import BackgroundStatusResponse, BackgroundTaskOut
from app.services.background.service import get_background_service

router = APIRouter(prefix="/background", tags=["background"])


@router.get("/status", response_model=BackgroundStatusResponse)
async def background_status() -> BackgroundStatusResponse:
    status = await get_background_service().status()
    return BackgroundStatusResponse(
        connected=status["connected"],
        tasks=[BackgroundTaskOut(**task) for task in status["tasks"]],
        isThrottled=status["isThrottled"],
        paused=status["paused"],
        state=status["state"],
        recentLatencyMs=status["recentLatencyMs"],
        error=status["error"],
    )


@router.post("/pause")
async def pause() -> dict[str, object]:
    get_background_service().pause()
    await event_bus.emit("background", "background.paused", {"reason": "manual"})
    return {"ok": True, "paused": True}


@router.post("/resume")
async def resume() -> dict[str, object]:
    get_background_service().resume()
    await event_bus.emit("background", "background.resumed", {"reason": "manual"})
    return {"ok": True, "paused": False}


@router.get("/stream")
async def background_stream() -> StreamingResponse:
    return StreamingResponse(
        sse_from_events(event_bus.stream("background")),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
