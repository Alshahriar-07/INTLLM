"""Interactive approval broker for Agent mode.

In ASK ME mode the agent loop pauses on an action that changes the workspace and
waits for the user's Allow/Deny decision. The decision arrives out-of-band (a
separate HTTP request) while the chat stream stays open, so the loop needs a
small coordination point:

* ``create`` registers a pending request and returns an id plus a future,
* the loop emits ``agent.permission.required`` with that id and awaits,
* the UI POSTs the decision, which resolves the future,
* a timeout or a cancelled stream resolves it as a deny (never a fake allow).
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

DECISION_ALLOW = "allow"
DECISION_DENY = "deny"
_VALID_DECISIONS = {DECISION_ALLOW, DECISION_DENY}

# How long a pending approval waits before being treated as denied.
DEFAULT_TIMEOUT_SECONDS = 300.0


@dataclass(slots=True)
class PendingApproval:
    id: str
    payload: dict[str, Any] = field(default_factory=dict)
    future: asyncio.Future | None = None
    resolved: bool = False


class PermissionBroker:
    def __init__(self) -> None:
        self._pending: dict[str, PendingApproval] = {}

    def create(self, payload: dict[str, Any]) -> PendingApproval:
        loop = asyncio.get_running_loop()
        request = PendingApproval(
            id=uuid.uuid4().hex, payload=payload, future=loop.create_future()
        )
        self._pending[request.id] = request
        return request

    def resolve(self, request_id: str, decision: str) -> bool:
        request = self._pending.get(request_id)
        if request is None or request.future is None:
            return False
        if request.future.done():
            return False
        normalized = decision if decision in _VALID_DECISIONS else DECISION_DENY
        request.resolved = True
        request.future.set_result(normalized)
        return True

    def cancel(self, request_id: str) -> None:
        """Resolve a pending request as denied (used when a stream ends)."""
        request = self._pending.get(request_id)
        if request is not None and request.future is not None and not request.future.done():
            request.future.set_result(DECISION_DENY)

    def cancel_all(self) -> None:
        for request in list(self._pending.values()):
            self.cancel(request.id)

    async def wait(self, request: PendingApproval, timeout: float) -> str:
        try:
            if request.future is None:
                return DECISION_DENY
            return await asyncio.wait_for(request.future, timeout=timeout)
        except TimeoutError:
            logger.info(
                "agent approval timed out",
                extra={"intllm_extra": {"request_id": request.id}},
            )
            return DECISION_DENY
        except asyncio.CancelledError:
            # Client disconnected / task cancelled: propagate so the agent loop
            # stops and the pending approval is never silently allowed.
            raise
        finally:
            self._pending.pop(request.id, None)

    def pending_ids(self) -> list[str]:
        return list(self._pending.keys())


_broker: PermissionBroker | None = None


def get_permission_broker() -> PermissionBroker:
    global _broker
    if _broker is None:
        _broker = PermissionBroker()
    return _broker
