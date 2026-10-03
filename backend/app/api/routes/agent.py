"""Agent mode endpoints: workspace management + sandboxed filesystem/terminal.

Every filesystem path is validated against the selected workspace inside the
Agent service; these handlers only translate results to the API schema.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.errors import NotFoundError
from app.schemas import (
    AgentCreateDirRequest,
    AgentDeleteRequest,
    AgentMoveRequest,
    AgentOperationOut,
    AgentPermissionDecisionRequest,
    AgentPermissionModeRequest,
    AgentPermissionRequest,
    AgentTerminalRequest,
    AgentToolSpecOut,
    AgentWorkspaceOut,
    AgentWorkspaceRequest,
    AgentWriteRequest,
)
from app.services.agent.permissions import get_permission_broker
from app.services.agent.service import AgentResult, WorkspaceStatus, get_agent_service

router = APIRouter(prefix="/agent", tags=["agent"])


def _workspace_out(status: WorkspaceStatus) -> AgentWorkspaceOut:
    return AgentWorkspaceOut(
        configured=status.configured,
        path=status.path,
        name=status.name,
        exists=status.exists,
        writable=status.writable,
        fileCount=status.file_count,
        sessionGrants=status.session_grants,
        terminalEnabled=status.terminal_enabled,
        permissionMode=status.permission_mode,
    )


def _op_out(result: AgentResult) -> AgentOperationOut:
    return AgentOperationOut(
        operation=result.operation,
        status=result.status,
        output=result.output,
        error=result.error,
        target=result.target,
        risk=result.risk,
        durationMs=result.duration_ms,
        permission=result.permission,
    )


@router.get("/status", response_model=AgentWorkspaceOut)
async def agent_status() -> AgentWorkspaceOut:
    return _workspace_out(await get_agent_service().status())


@router.post("/workspace", response_model=AgentWorkspaceOut)
async def set_workspace(body: AgentWorkspaceRequest) -> AgentWorkspaceOut:
    return _workspace_out(await get_agent_service().set_workspace(body.path))


@router.post("/workspace/pick", response_model=AgentWorkspaceOut)
async def pick_workspace() -> AgentWorkspaceOut:
    """Open the local folder chooser and adopt the result when one is returned."""
    service = get_agent_service()
    selected = await service.pick_folder()
    if selected:
        return _workspace_out(await service.set_workspace(selected))
    return _workspace_out(await service.status())


@router.delete("/workspace", response_model=AgentWorkspaceOut)
async def clear_workspace() -> AgentWorkspaceOut:
    return _workspace_out(await get_agent_service().clear_workspace())


@router.get("/fs/list", response_model=AgentOperationOut)
async def list_directory(
    path: str | None = Query(default=None),
) -> AgentOperationOut:
    return _op_out(await get_agent_service().list_dir(path))


@router.get("/fs/read", response_model=AgentOperationOut)
async def read_file(path: str = Query(...)) -> AgentOperationOut:
    return _op_out(await get_agent_service().read_file(path))


@router.get("/fs/search", response_model=AgentOperationOut)
async def search_files(
    query: str = Query(...),
    path: str | None = Query(default=None),
) -> AgentOperationOut:
    return _op_out(await get_agent_service().search(query, path))


@router.post("/fs/write", response_model=AgentOperationOut)
async def write_file(body: AgentWriteRequest) -> AgentOperationOut:
    result = await get_agent_service().write_file(
        body.path, body.content, decision=body.decision
    )
    return _op_out(result)


@router.post("/fs/mkdir", response_model=AgentOperationOut)
async def create_directory(body: AgentCreateDirRequest) -> AgentOperationOut:
    return _op_out(await get_agent_service().create_dir(body.path, decision=body.decision))


@router.post("/fs/delete", response_model=AgentOperationOut)
async def delete_path(body: AgentDeleteRequest) -> AgentOperationOut:
    return _op_out(await get_agent_service().delete(body.path, decision=body.decision))


@router.post("/fs/move", response_model=AgentOperationOut)
async def move_path(body: AgentMoveRequest) -> AgentOperationOut:
    return _op_out(
        await get_agent_service().move(
            body.source, body.destination, decision=body.decision
        )
    )


@router.post("/terminal", response_model=AgentOperationOut)
async def run_terminal(body: AgentTerminalRequest) -> AgentOperationOut:
    return _op_out(
        await get_agent_service().run_command(
            body.command, cwd=body.cwd, decision=body.decision
        )
    )


@router.get("/tools", response_model=list[AgentToolSpecOut])
async def list_tools() -> list[AgentToolSpecOut]:
    """The workspace tools the Agent model may call."""
    return [AgentToolSpecOut(**spec) for spec in get_agent_service().tool_specs()]


@router.get("/permissions")
async def list_permissions() -> dict[str, object]:
    service = get_agent_service()
    await service.ensure_loaded()
    return {
        "session_grants": service.session_grants(),
        "mode": service.permission_mode,
    }


@router.get("/permissions/mode")
async def get_permission_mode() -> dict[str, object]:
    service = get_agent_service()
    await service.ensure_loaded()
    return {"mode": service.permission_mode}


@router.post("/permissions/mode")
async def set_permission_mode(body: AgentPermissionModeRequest) -> dict[str, object]:
    mode = await get_agent_service().set_permission_mode(body.mode)
    return {"ok": True, "mode": mode}


@router.post("/permissions/decide")
async def decide_permission(body: AgentPermissionDecisionRequest) -> dict[str, object]:
    """Resolve a pending Allow/Deny request raised by the Agent loop."""
    resolved = get_permission_broker().resolve(body.request_id, body.decision)
    if not resolved:
        raise NotFoundError("No pending Agent permission request with that id")
    return {"ok": True, "decision": body.decision}


@router.post("/permissions")
async def update_permission(body: AgentPermissionRequest) -> dict[str, object]:
    service = get_agent_service()
    if body.decision == "allow_session":
        service.grant_session(body.operation)
    else:
        service.revoke_session(body.operation)
    return {"ok": True, "session_grants": service.session_grants()}
