"""Agent runtime tests: workspace sandbox, permissions, filesystem, terminal.

These use a real temporary directory. No PostgreSQL or Ollama is required: the
workspace persistence path degrades gracefully when the database is down.
"""

from __future__ import annotations

import sys

import pytest

from app.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from app.services.agent.service import AgentOperation, AgentService


@pytest.fixture
def agent(tmp_path):
    service = AgentService()
    return service, tmp_path


async def test_workspace_must_exist(agent):
    service, tmp_path = agent
    with pytest.raises(NotFoundError):
        await service.set_workspace(str(tmp_path / "does-not-exist"))
    with pytest.raises(ValidationError):
        await service.set_workspace("")


async def test_workspace_and_readonly_ops(agent):
    service, tmp_path = agent
    (tmp_path / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")

    status = await service.set_workspace(str(tmp_path))
    assert status.configured and status.exists

    listing = await service.list_dir(".")
    names = {entry["name"] for entry in listing.output["entries"]}
    assert {"main.py", "src"} <= names

    read = await service.read_file("main.py")
    assert read.status == "completed"
    assert "print('hi')" in read.output["content"]

    found = await service.search("VALUE")
    assert found.status == "completed"
    assert found.output["matches"][0]["path"] == "src/app.py"


async def test_path_escape_is_blocked(agent):
    service, tmp_path = agent
    await service.set_workspace(str(tmp_path))
    with pytest.raises(PermissionDeniedError):
        service.resolve("../outside.txt")
    with pytest.raises(PermissionDeniedError):
        await service.read_file("../../etc/passwd")


async def test_create_and_overwrite_require_approval_in_ask_mode(agent):
    service, tmp_path = agent
    await service.set_workspace(str(tmp_path))
    await service.set_permission_mode("ask")

    # ASK ME: creating a new workspace file needs explicit approval.
    blocked = await service.write_file("notes.txt", "hello")
    assert blocked.status == "permission_required"
    assert not (tmp_path / "notes.txt").exists()

    created = await service.write_file("notes.txt", "hello", decision="allow")
    assert created.status == "completed"
    assert created.operation == AgentOperation.CREATE.value
    assert (tmp_path / "notes.txt").read_text(encoding="utf-8") == "hello"

    overwrite = await service.write_file("notes.txt", "world")
    assert overwrite.status == "permission_required"
    assert (tmp_path / "notes.txt").read_text(encoding="utf-8") == "hello"

    allowed = await service.write_file("notes.txt", "world", decision="allow")
    assert allowed.status == "completed"
    assert (tmp_path / "notes.txt").read_text(encoding="utf-8") == "world"


async def test_allow_mode_auto_approves_create(agent):
    service, tmp_path = agent
    await service.set_workspace(str(tmp_path))
    await service.set_permission_mode("allow")

    created = await service.write_file("auto.txt", "ok")
    assert created.status == "completed"
    assert (tmp_path / "auto.txt").read_text(encoding="utf-8") == "ok"


async def test_delete_requires_approval_and_session_grant(agent):
    service, tmp_path = agent
    await service.set_workspace(str(tmp_path))
    target = tmp_path / "temp.txt"
    target.write_text("x", encoding="utf-8")

    blocked = await service.delete("temp.txt")
    assert blocked.status == "permission_required"
    assert target.exists()

    denied = await service.delete("temp.txt", decision="deny")
    assert denied.status == "denied"
    assert target.exists()

    granted = await service.delete("temp.txt", decision="allow_session")
    assert granted.status == "completed"
    assert not target.exists()

    # Session grant suppresses repeat prompts for the same operation.
    again = tmp_path / "temp2.txt"
    again.write_text("x", encoding="utf-8")
    second = await service.delete("temp2.txt")
    assert second.status == "completed"


async def test_cannot_delete_workspace_root(agent):
    service, tmp_path = agent
    await service.set_workspace(str(tmp_path))
    with pytest.raises(PermissionDeniedError):
        await service.delete(".")


async def test_move_and_mkdir(agent):
    service, tmp_path = agent
    await service.set_workspace(str(tmp_path))
    await service.set_permission_mode("allow")
    await service.create_dir("pkg")
    assert (tmp_path / "pkg").is_dir()

    source = tmp_path / "a.txt"
    source.write_text("data", encoding="utf-8")
    moved = await service.move("a.txt", "pkg/b.txt", decision="allow")
    assert moved.status == "completed"
    assert (tmp_path / "pkg" / "b.txt").is_file()


async def test_terminal_requires_approval_and_runs(agent):
    service, tmp_path = agent
    await service.set_workspace(str(tmp_path))

    blocked = await service.run_command("echo hi")
    assert blocked.status == "permission_required"

    if sys.platform == "win32":
        command = "echo hi"
    else:
        command = "echo hi"
    result = await service.run_command(command, decision="allow")
    assert result.status == "completed"
    assert "hi" in result.output["stdout"]
    assert result.output["exitCode"] == 0


async def test_terminal_reports_outside_workspace_hint(agent):
    service, tmp_path = agent
    await service.set_workspace(str(tmp_path))
    outside = "C:\\Windows" if sys.platform == "win32" else "/etc"
    result = await service.run_command(f"dir {outside}", decision="allow")
    assert result.output["outsideWorkspaceHint"] is True
