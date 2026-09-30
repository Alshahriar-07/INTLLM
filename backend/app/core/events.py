"""In-process async event bus.

Powers SSE/WebSocket fan-out for chat activity, browser activity, system
telemetry and background-learning states. Subscribers each get their own
bounded queue; slow consumers are dropped rather than blocking producers.
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

_QUEUE_MAX = 256


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Event:
    channel: str
    type: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now_iso)


class EventBus:
    def __init__(self, history_size: int = 200) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[Event]]] = {}
        self._history: dict[str, deque[Event]] = {}
        self._history_size = history_size
        self._lock = asyncio.Lock()

    async def subscribe(self, channel: str | None = None) -> asyncio.Queue[Event]:
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=_QUEUE_MAX)
        key = channel or "*"
        async with self._lock:
            self._subscribers.setdefault(key, set()).add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[Event], channel: str | None = None) -> None:
        key = channel or "*"
        async with self._lock:
            subscribers = self._subscribers.get(key)
            if subscribers:
                subscribers.discard(queue)

    async def publish(self, event: Event) -> None:
        async with self._lock:
            history = self._history.setdefault(event.channel, deque(maxlen=self._history_size))
            history.append(event)
            targets = set(self._subscribers.get(event.channel, set()))
            targets |= set(self._subscribers.get("*", set()))

        for queue in targets:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Drop the slowest consumer's oldest event instead of blocking.
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    logger.warning(
                        "event dropped for slow subscriber",
                        extra={"intllm_extra": {"channel": event.channel}},
                    )

    async def emit(
        self, channel: str, event_type: str, data: dict[str, Any] | None = None
    ) -> None:
        await self.publish(Event(channel=channel, type=event_type, data=data or {}))

    def history(self, channel: str) -> list[Event]:
        return list(self._history.get(channel, ()))

    async def stream(self, channel: str) -> AsyncIterator[Event]:
        queue = await self.subscribe(channel)
        try:
            # Replay recent history so a late subscriber sees current state.
            for event in self.history(channel):
                yield event
            while True:
                yield await queue.get()
        finally:
            await self.unsubscribe(queue, channel)


# Process-wide singleton.
event_bus = EventBus()
