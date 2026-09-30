"""Browser agent endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.sse import SSE_HEADERS, sse_from_events
from app.core.errors import ValidationError
from app.core.events import event_bus
from app.schemas import BrowserActionRequest, BrowserStateResponse
from app.services.browser.service import get_browser_service
from app.services.tools.gateway import PermissionDecision, get_tool_gateway

router = APIRouter(prefix="/browser", tags=["browser"])


@router.get("/status", response_model=BrowserStateResponse)
async def browser_status() -> BrowserStateResponse:
    return BrowserStateResponse(**await get_browser_service().state())


@router.post("/action")
async def browser_action(body: BrowserActionRequest) -> dict[str, object]:
    browser = get_browser_service()

    if body.action == "screenshot":
        return await browser.screenshot()
    if body.action in ("open", "read"):
        if not body.url:
            raise ValidationError("`url` is required for this browser action")
        if body.action == "open":
            return await browser.open(body.url)
        return await browser.read(body.url)
    if body.action == "click":
        if not body.selector:
            raise ValidationError("`selector` is required for click")
        decision = PermissionDecision(body.decision) if body.decision else None
        result = await get_tool_gateway().run(
            "browser.click", {"selector": body.selector}, decision=decision
        )
        return {
            "status": result.status,
            "output": result.output,
            "error": result.error,
            "permission": result.permission,
        }
    raise ValidationError(f"Unsupported browser action: {body.action}")


@router.get("/stream")
async def browser_stream() -> StreamingResponse:
    return StreamingResponse(
        sse_from_events(event_bus.stream("browser")),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
