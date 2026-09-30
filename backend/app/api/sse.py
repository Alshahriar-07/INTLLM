"""Server-Sent Events helpers."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from app.core.events import Event

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def format_event(event_type: str, data: dict[str, Any]) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, default=str)}\n\n"


def format_stream_event(event: Event) -> str:
    payload = {"type": event.type, "data": event.data, "timestamp": event.timestamp}
    return format_event(event.type, payload)


async def sse_from_events(stream: AsyncIterator[Event]) -> AsyncIterator[str]:
    async for event in stream:
        yield format_stream_event(event)
