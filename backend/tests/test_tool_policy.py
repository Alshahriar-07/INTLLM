"""Tool Gateway policy and security boundaries."""

from __future__ import annotations

import pytest

from app.core.errors import NotFoundError, PermissionDeniedError
from app.services.tools.gateway import (
    PermissionDecision,
    ToolGateway,
    get_tool_gateway,
)


def test_unknown_tool_is_not_found():
    with pytest.raises(NotFoundError):
        ToolGateway().get_tool("does.not.exist")


async def test_restricted_disabled_tool_is_denied():
    gateway = ToolGateway()
    with pytest.raises(PermissionDeniedError):
        await gateway.run("terminal.execute", {"command": "rm -rf /"})


async def test_approval_tool_requires_decision():
    gateway = ToolGateway()
    result = await gateway.run("browser.click", {"selector": "#submit"})
    assert result.status == "permission_required"
    assert result.output is None


async def test_approval_tool_runs_with_allow_session_decision(monkeypatch):
    gateway = ToolGateway()

    async def fake_click(self, selector):
        return {"clicked": selector}

    from app.services.browser.service import BrowserService

    monkeypatch.setattr(BrowserService, "click", fake_click)
    result = await gateway.run(
        "browser.click", {"selector": "#ok"}, decision=PermissionDecision.ALLOW_SESSION
    )
    assert result.status == "completed"
    assert result.output == {"clicked": "#ok"}
    # Session grant persists for subsequent calls without re-approval.
    assert "browser.click" in gateway.session_grants()


async def test_filesystem_read_blocks_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setenv("INTLLM_FILESYSTEM_ALLOWLIST", str(tmp_path))
    monkeypatch.setenv("INTLLM_WORKSPACE_DIR", str(tmp_path))
    import app.services.tools.gateway as gateway_module

    monkeypatch.setattr(gateway_module, "get_settings", lambda: type("S", (), {
        "filesystem_allowlist": [tmp_path],
        "workspace_dir": tmp_path,
    })())

    gateway = ToolGateway()
    result = await gateway.run(
        "filesystem.read", {"path": "../escape.txt"}, decision=PermissionDecision.ALLOW
    )
    assert result.status == "denied"
    assert "allowlist" in (result.error or "")


async def test_missing_required_argument_fails_validation():
    from app.core.errors import ValidationError

    gateway = ToolGateway()
    with pytest.raises(ValidationError):
        await gateway.run("web.search", {})


def test_registry_has_static_schemas_for_frontend():
    tools = {tool.id for tool in get_tool_gateway().list_tools()}
    assert {"web.search", "browser.read", "filesystem.read", "system.info"} <= tools
