"""Tool Gateway.

The model never directly owns OS/browser privileges. Every call passes through
schema validation, a policy check, a permission decision and result
sanitization before anything executes.
"""

from __future__ import annotations

import dataclasses
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from app.config.settings import get_settings
from app.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from app.core.events import event_bus
from app.core.logging import get_logger

logger = get_logger(__name__)


class PermissionLevel(str, Enum):
    READ_ONLY = "read-only"
    REQUIRES_APPROVAL = "requires-approval"
    RESTRICTED = "restricted"


class PermissionDecision(str, Enum):
    ALLOW = "allow"
    ALLOW_SESSION = "allow_session"
    DENY = "deny"


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


@dataclass(slots=True)
class ToolDefinition:
    id: str
    name: str
    category: str
    description: str
    permission_level: PermissionLevel
    risk_level: RiskLevel
    enabled: bool = True
    timeout_seconds: float = 30.0
    required_args: tuple[str, ...] = field(default_factory=tuple)
    handler_name: str = ""


@dataclass(slots=True)
class ToolResult:
    tool: str
    status: str  # completed | denied | permission_required | failed
    output: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: float = 0.0
    permission: str | None = None


# Capability registry. Mirrors PLAN/07-tools-browser/TOOL_GATEWAY.md.
TOOL_REGISTRY: dict[str, ToolDefinition] = {
    "web.search": ToolDefinition(
        id="web.search", name="Web Search Gateway", category="web",
        description="Queries live search engines for real-time documentation and news.",
        permission_level=PermissionLevel.READ_ONLY, risk_level=RiskLevel.LOW,
        required_args=("query",), handler_name="web_search",
    ),
    "web.open": ToolDefinition(
        id="web.open", name="Web Page Opener", category="web",
        description="Retrieves and extracts readable text from a URL.",
        permission_level=PermissionLevel.READ_ONLY, risk_level=RiskLevel.LOW,
        required_args=("url",), handler_name="web_open",
    ),
    "web.extract": ToolDefinition(
        id="web.extract", name="Web Page Extractor", category="web",
        description="Extracts clean HTML/Markdown text from target URL web pages.",
        permission_level=PermissionLevel.READ_ONLY, risk_level=RiskLevel.LOW,
        required_args=("url",), handler_name="web_open",
    ),
    "browser.open": ToolDefinition(
        id="browser.open", name="Browser Open", category="browser",
        description="Opens a URL in the managed Playwright browser session.",
        permission_level=PermissionLevel.REQUIRES_APPROVAL, risk_level=RiskLevel.MEDIUM,
        required_args=("url",), handler_name="browser_open",
    ),
    "browser.read": ToolDefinition(
        id="browser.read", name="Headless Browser Reader", category="browser",
        description="Navigates and inspects JavaScript-rendered DOM elements via Playwright.",
        permission_level=PermissionLevel.READ_ONLY, risk_level=RiskLevel.LOW,
        required_args=("url",), handler_name="browser_read",
    ),
    "browser.click": ToolDefinition(
        id="browser.click", name="Browser Action Clicker", category="browser",
        description="Triggers mouse clicks, input selections, and form submissions.",
        permission_level=PermissionLevel.REQUIRES_APPROVAL, risk_level=RiskLevel.MEDIUM,
        required_args=("selector",), handler_name="browser_click",
    ),
    "browser.screenshot": ToolDefinition(
        id="browser.screenshot", name="Browser Screenshot", category="browser",
        description="Captures a screenshot of the current browser page.",
        permission_level=PermissionLevel.READ_ONLY, risk_level=RiskLevel.LOW,
        handler_name="browser_screenshot",
    ),
    "brain.search": ToolDefinition(
        id="brain.search", name="Memory Brain Search", category="system",
        description="Searches layered memory (L0/L1/L2) for relevant knowledge.",
        permission_level=PermissionLevel.READ_ONLY, risk_level=RiskLevel.LOW,
        required_args=("query",), handler_name="brain_search",
    ),
    "system.info": ToolDefinition(
        id="system.info", name="Hardware & Process Monitor", category="system",
        description="Reads CPU, VRAM, and RAM metrics from local system runtime.",
        permission_level=PermissionLevel.READ_ONLY, risk_level=RiskLevel.LOW,
        handler_name="system_info",
    ),
    "filesystem.read": ToolDefinition(
        id="filesystem.read", name="Local Directory Reader", category="filesystem",
        description="Reads local workspace files, project structures, and code files.",
        permission_level=PermissionLevel.REQUIRES_APPROVAL, risk_level=RiskLevel.MEDIUM,
        required_args=("path",), handler_name="filesystem_read",
    ),
    "filesystem.write": ToolDefinition(
        id="filesystem.write", name="Local File Writer", category="filesystem",
        description="Creates, edits, or deletes files inside approved workspace paths.",
        permission_level=PermissionLevel.RESTRICTED, risk_level=RiskLevel.HIGH,
        enabled=False, required_args=("path", "content"), handler_name="filesystem_write",
    ),
    "terminal.execute": ToolDefinition(
        id="terminal.execute", name="Terminal Subprocess Executor", category="terminal",
        description="Executes shell commands in isolated subshells.",
        permission_level=PermissionLevel.RESTRICTED, risk_level=RiskLevel.CRITICAL,
        enabled=False, required_args=("command",), handler_name="terminal_execute",
    ),
}


class ToolGateway:
    """Validates, authorizes and dispatches tool calls."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._session_grants: set[str] = set()
        self._handlers: dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]] = {}
        self._register_default_handlers()

    # --- registry ---------------------------------------------------------
    def list_tools(self) -> list[ToolDefinition]:
        return list(TOOL_REGISTRY.values())

    def get_tool(self, tool_id: str) -> ToolDefinition:
        tool = TOOL_REGISTRY.get(tool_id)
        if tool is None:
            raise NotFoundError(f"Unknown tool: {tool_id}")
        return tool

    def grant_session(self, tool_id: str) -> None:
        self._session_grants.add(tool_id)

    def revoke_session(self, tool_id: str) -> None:
        self._session_grants.discard(tool_id)

    def session_grants(self) -> list[str]:
        return sorted(self._session_grants)

    # --- execution --------------------------------------------------------
    async def run(
        self,
        tool_id: str,
        arguments: dict[str, Any],
        *,
        decision: PermissionDecision | None = None,
    ) -> ToolResult:
        tool = self.get_tool(tool_id)
        started = time.perf_counter()

        if not tool.enabled:
            raise PermissionDeniedError(f"Tool '{tool_id}' is disabled by policy")

        self._validate_args(tool, arguments)

        # Permission policy: risky tools require an approval decision.
        if tool.permission_level is PermissionLevel.REQUIRES_APPROVAL:
            if decision == PermissionDecision.ALLOW_SESSION:
                self.grant_session(tool_id)
            granted = decision in (PermissionDecision.ALLOW, PermissionDecision.ALLOW_SESSION)
            already = tool_id in self._session_grants
            if not (granted or already):
                await event_bus.emit(
                    "tools",
                    "tool.permission_required",
                    {"tool": tool_id, "risk": tool.risk_level.value},
                )
                return ToolResult(
                    tool=tool_id,
                    status="permission_required",
                    error="Explicit user approval is required before execution",
                    permission=tool.permission_level.value,
                    duration_ms=round((time.perf_counter() - started) * 1000.0, 2),
                )

        handler = self._handlers.get(tool.handler_name)
        if handler is None:
            raise NotFoundError(f"No handler registered for tool '{tool_id}'")

        try:
            output = await handler({"tool": tool, "args": arguments})
            status = "completed"
            error = None
        except PermissionDeniedError as exc:
            output, status, error = None, "denied", str(exc)
        except (ValidationError, NotFoundError) as exc:
            output, status, error = None, "failed", str(exc)
        except Exception as exc:
            logger.exception("tool execution failed")
            output, status, error = None, "failed", f"{type(exc).__name__}: {exc}"

        duration = round((time.perf_counter() - started) * 1000.0, 2)
        await event_bus.emit(
            "tools",
            "tool.completed",
            {"tool": tool_id, "status": status, "duration_ms": duration},
        )
        return ToolResult(
            tool=tool_id,
            status=status,
            output=output,
            error=error,
            duration_ms=duration,
            permission=tool.permission_level.value,
        )

    def _validate_args(self, tool: ToolDefinition, arguments: dict[str, Any]) -> None:
        if not isinstance(arguments, dict):
            raise ValidationError("Tool arguments must be an object")
        for required in tool.required_args:
            if required not in arguments:
                raise ValidationError(f"Missing required argument '{required}' for {tool.id}")
            if not isinstance(arguments[required], str) or not arguments[required].strip():
                raise ValidationError(f"Argument '{required}' must be a non-empty string")

    # --- handlers ---------------------------------------------------------
    def _register_default_handlers(self) -> None:
        async def web_search(payload: dict[str, Any]) -> dict[str, Any]:
            from app.services.web.service import get_web_service

            sources = await get_web_service().search(payload["args"]["query"])
            return {"results": [dataclasses.asdict(source) for source in sources]}

        async def web_open(payload: dict[str, Any]) -> dict[str, Any]:
            from app.services.web.service import get_web_service

            return await get_web_service().fetch(payload["args"]["url"])

        async def brain_search(payload: dict[str, Any]) -> dict[str, Any]:
            from app.db.session import get_database
            from app.services.brain.service import get_brain_service

            database = get_database()
            async with database.session() as session:
                result = await get_brain_service().lookup(session, payload["args"]["query"])
            return {
                "hit": result.hit,
                "source": result.source,
                "count": len(result.memories),
                "memories": [
                    {"id": str(m.id), "title": m.title, "confidence": m.confidence}
                    for m in result.memories
                ],
            }

        async def system_info(_: dict[str, Any]) -> dict[str, Any]:
            from app.services.system.service import get_hardware_service

            snapshot = await get_hardware_service().snapshot()
            return snapshot

        async def browser_open(payload: dict[str, Any]) -> dict[str, Any]:
            from app.services.browser.service import get_browser_service

            return await get_browser_service().open(payload["args"]["url"])

        async def browser_read(payload: dict[str, Any]) -> dict[str, Any]:
            from app.services.browser.service import get_browser_service

            return await get_browser_service().read(payload["args"]["url"])

        async def browser_click(payload: dict[str, Any]) -> dict[str, Any]:
            from app.services.browser.service import get_browser_service

            return await get_browser_service().click(payload["args"]["selector"])

        async def browser_screenshot(_: dict[str, Any]) -> dict[str, Any]:
            from app.services.browser.service import get_browser_service

            return await get_browser_service().screenshot()

        async def filesystem_read(payload: dict[str, Any]) -> dict[str, Any]:
            path = self._resolve_workspace_path(payload["args"]["path"])
            if not path.is_file():
                raise NotFoundError(f"File not found: {path}")
            return {"path": str(path), "content": path.read_text(encoding="utf-8", errors="replace")[:20000]}

        async def filesystem_write(_: dict[str, Any]) -> dict[str, Any]:
            raise PermissionDeniedError("Filesystem writes are disabled by default policy")

        async def terminal_execute(_: dict[str, Any]) -> dict[str, Any]:
            raise PermissionDeniedError("Terminal execution is disabled by default policy")

        self._handlers = {
            "web_search": web_search,
            "web_open": web_open,
            "brain_search": brain_search,
            "system_info": system_info,
            "browser_open": browser_open,
            "browser_read": browser_read,
            "browser_click": browser_click,
            "browser_screenshot": browser_screenshot,
            "filesystem_read": filesystem_read,
            "filesystem_write": filesystem_write,
            "terminal_execute": terminal_execute,
        }

    def _resolve_workspace_path(self, raw_path: str) -> Path:
        allowlist = self._settings.filesystem_allowlist or [self._settings.workspace_dir]
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = (self._settings.workspace_dir / candidate).resolve()
        else:
            candidate = candidate.resolve()
        if not any(candidate == root or root in candidate.parents for root in allowlist):
            raise PermissionDeniedError("Path is outside the approved workspace allowlist")
        return candidate


_gateway: ToolGateway | None = None


def get_tool_gateway() -> ToolGateway:
    global _gateway
    if _gateway is None:
        _gateway = ToolGateway()
    return _gateway

