"""Tool Gateway endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.db.models import ToolRun
from app.db.session import get_database
from app.schemas import ToolListResponse, ToolOut, ToolRunRequest, ToolRunResponse
from app.services.tools.gateway import PermissionDecision, get_tool_gateway

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=ToolListResponse)
async def list_tools() -> ToolListResponse:
    gateway = get_tool_gateway()
    tools = [
        ToolOut(
            id=tool.id,
            name=tool.name,
            category=tool.category,
            description=tool.description,
            permissionLevel=tool.permission_level.value,
            enabled=tool.enabled,
            riskScore=tool.risk_level.value,
        )
        for tool in gateway.list_tools()
    ]
    return ToolListResponse(connected=True, tools=tools)


@router.post("/{tool_id}/run", response_model=ToolRunResponse)
async def run_tool(tool_id: str, body: ToolRunRequest) -> ToolRunResponse:
    gateway = get_tool_gateway()
    decision = PermissionDecision(body.decision) if body.decision else None
    result = await gateway.run(tool_id, body.arguments, decision=decision)
    await _persist_run(tool_id, body.arguments, result)
    return ToolRunResponse(
        tool=result.tool,
        status=result.status,
        output=result.output,
        error=result.error,
        duration_ms=result.duration_ms,
        permission=result.permission,
    )


@router.get("/permissions")
async def list_permissions() -> dict[str, object]:
    return {"session_grants": get_tool_gateway().session_grants()}


@router.post("/{tool_id}/permission")
async def grant_permission(tool_id: str) -> dict[str, object]:
    get_tool_gateway().get_tool(tool_id)
    get_tool_gateway().grant_session(tool_id)
    return {"ok": True, "granted": tool_id}


async def _persist_run(tool_id: str, arguments: dict, result) -> None:
    """Best-effort audit persistence; never blocks execution on DB failure."""
    database = get_database()
    available, _ = await database.ping()
    if not available:
        return
    try:
        async with database.session() as session:
            session.add(
                ToolRun(
                    tool_name=tool_id,
                    arguments=arguments,
                    permission=result.permission or "read-only",
                    status=result.status,
                    result=result.output,
                    error=result.error,
                    duration_ms=result.duration_ms,
                )
            )
    except Exception:  # noqa: BLE001
        pass
