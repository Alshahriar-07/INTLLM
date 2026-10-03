"""Agent loop, permission modes and new file tools.

These use a real temporary workspace and a scripted model adapter, so the loop's
multi-step execution, permission gating and error recovery run for real with no
PostgreSQL or Ollama required.
"""

from __future__ import annotations

from app.services.agent.loop import AgentLoop, _extract_tool_call
from app.services.agent.permissions import PermissionBroker
from app.services.agent.service import AgentOperation, AgentService
from app.services.runtime.base import ChatMessage, ModelInfo, StreamChunk


class _ScriptedAdapter:
    """Returns pre-scripted model outputs, one per generation step."""

    def __init__(self, script: list[str], *, models: list[str] | None = None) -> None:
        self._script = list(script)
        self._models = models if models is not None else ["test-model"]
        self.generations = 0

    async def list_models(self) -> list[ModelInfo]:
        return [ModelInfo(name=name) for name in self._models]

    async def chat(self, model, messages, *, options=None):
        self.generations += 1
        text = self._script.pop(0) if self._script else "done"
        yield StreamChunk(type="delta", content=text, model=model)
        yield StreamChunk(type="done", model=model, metrics={})


async def _run_loop(service, adapter, script, *, messages=None, resolver=None):
    broker = PermissionBroker()
    loop = AgentLoop(service=service, adapter=adapter, broker=broker)
    events: list[dict] = []
    gen = loop.run(
        model="test-model",
        messages=messages or [ChatMessage(role="user", content="do the task")],
    )
    async for event in gen:
        events.append(event)
        if event["type"] == "agent.permission.required" and resolver is not None:
            broker.resolve(event["data"]["request_id"], resolver(event))
    return (events, loop)


# --- parser ---------------------------------------------------------------


def test_extract_tool_call_variants():
    assert _extract_tool_call('{"tool":"fs.read","args":{"path":"a"}}') == {
        "tool": "fs.read",
        "args": {"path": "a"},
    }
    fenced = _extract_tool_call('ok\n```json\n{"tool":"terminal","args":{"command":"ls"}}\n```')
    assert fenced == {"tool": "terminal", "args": {"command": "ls"}}
    assert _extract_tool_call("No tools needed. Done.") is None


# --- multi-step loop ------------------------------------------------------


async def test_allow_mode_multistep_read_then_write(tmp_path):
    service = AgentService()
    await service.set_workspace(str(tmp_path))
    await service.set_permission_mode("allow")
    (tmp_path / "data.txt").write_text("hello world", encoding="utf-8")

    adapter = _ScriptedAdapter(
        [
            '{"tool":"fs.read","args":{"path":"data.txt"}}',
            '{"tool":"fs.write","args":{"path":"out.txt","content":"report"}}',
            "Done: created out.txt.",
        ]
    )
    (events, loop) = await _run_loop(service, adapter, adapter._script)

    types = [e["type"] for e in events]
    assert "agent.step" in types
    assert types.count("agent.tool.completed") == 2
    assert types[-1] == "agent.final"
    assert (tmp_path / "out.txt").read_text(encoding="utf-8") == "report"
    # Two real tool activities were recorded.
    assert [a["tool"] for a in loop.activities] == ["fs.read", "fs.write"]


async def test_ask_mode_denied_write_is_blocked(tmp_path):
    service = AgentService()
    await service.set_workspace(str(tmp_path))
    await service.set_permission_mode("ask")

    adapter = _ScriptedAdapter(
        [
            '{"tool":"fs.write","args":{"path":"blocked.txt","content":"nope"}}',
            "I could not write the file because it was denied.",
        ]
    )
    events, _loop = await _run_loop(
        service, adapter, adapter._script, resolver=lambda _e: "deny"
    )

    assert not (tmp_path / "blocked.txt").exists()
    completed = [e for e in events if e["type"] == "agent.tool.completed"]
    assert completed and completed[0]["data"]["status"] == "denied"
    # The loop continued and produced a final answer.
    assert events[-1]["type"] == "agent.final"


async def test_ask_mode_allowed_write_executes(tmp_path):
    service = AgentService()
    await service.set_workspace(str(tmp_path))
    await service.set_permission_mode("ask")

    adapter = _ScriptedAdapter(
        [
            '{"tool":"fs.write","args":{"path":"ok.txt","content":"allowed"}}',
            "Done.",
        ]
    )
    await _run_loop(service, adapter, adapter._script, resolver=lambda _e: "allow")
    assert (tmp_path / "ok.txt").read_text(encoding="utf-8") == "allowed"


async def test_tool_failure_is_returned_and_loop_recovers(tmp_path):
    service = AgentService()
    await service.set_workspace(str(tmp_path))
    await service.set_permission_mode("allow")

    adapter = _ScriptedAdapter(
        [
            '{"tool":"fs.read","args":{"path":"missing.txt"}}',
            '{"tool":"fs.write","args":{"path":"created.txt","content":"ok"}}',
            "Recovered and finished.",
        ]
    )
    (events, loop) = await _run_loop(service, adapter, adapter._script)

    statuses = [a["status"] for a in loop.activities]
    assert statuses[0] == "failed"  # the read failed honestly
    assert statuses[1] == "completed"
    assert (tmp_path / "created.txt").is_file()


async def test_workspace_escape_is_blocked_in_loop(tmp_path):
    service = AgentService()
    await service.set_workspace(str(tmp_path))
    await service.set_permission_mode("allow")

    adapter = _ScriptedAdapter(
        [
            '{"tool":"fs.read","args":{"path":"../secret.txt"}}',
            "Cannot read outside the workspace.",
        ]
    )
    (events, loop) = await _run_loop(service, adapter, adapter._script)
    assert loop.activities[0]["status"] == "failed"
    assert "outside" in (loop.activities[0]["detail"] or "").lower()


async def test_missing_model_reports_error(tmp_path):
    service = AgentService()
    await service.set_workspace(str(tmp_path))
    adapter = _ScriptedAdapter(["unused"], models=[])
    events, _loop = await _run_loop(service, adapter, [])
    assert events[0]["type"] == "agent.error"
    assert events[0]["data"]["code"] == "model_unavailable"


async def test_step_limit_stops_runaway_loop(tmp_path):
    service = AgentService()
    await service.set_workspace(str(tmp_path))
    await service.set_permission_mode("allow")

    # A model that always repeats the same read must be stopped, not spin.
    repeating = '{"tool":"fs.list","args":{}}'
    adapter = _ScriptedAdapter([repeating] * 10)
    broker = PermissionBroker()
    loop = AgentLoop(service=service, adapter=adapter, broker=broker, max_steps=5)
    events = [
        event
        async for event in loop.run(
            model="test-model",
            messages=[ChatMessage(role="user", content="loop")],
        )
    ]
    assert events[-1]["type"] == "agent.final"
    assert len(loop.activities) <= 3  # repeated call detected early


# --- new file tools -------------------------------------------------------


async def test_edit_tool_replaces_text(tmp_path):
    service = AgentService()
    await service.set_workspace(str(tmp_path))
    await service.set_permission_mode("allow")
    (tmp_path / "config.py").write_text("VALUE = 1\n", encoding="utf-8")

    result = await service.edit_file("config.py", "VALUE = 1", "VALUE = 2")
    assert result.status == "completed"
    assert result.operation == AgentOperation.EDIT.value
    assert (tmp_path / "config.py").read_text(encoding="utf-8") == "VALUE = 2\n"


async def test_edit_tool_fails_when_text_absent(tmp_path):
    from app.core.errors import ValidationError

    service = AgentService()
    await service.set_workspace(str(tmp_path))
    await service.set_permission_mode("allow")
    (tmp_path / "a.txt").write_text("original", encoding="utf-8")

    import pytest

    with pytest.raises(ValidationError):
        await service.edit_file("a.txt", "not-present", "x")
    # No silent partial write.
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "original"


async def test_binary_file_returns_metadata_not_bytes(tmp_path):
    service = AgentService()
    await service.set_workspace(str(tmp_path))
    (tmp_path / "blob.bin").write_bytes(b"\x00\x01\x02\x03binary\x00")

    result = await service.read_file("blob.bin")
    assert result.status == "completed"
    assert result.output["binary"] is True
    assert result.output["content"] is None


async def test_tool_specs_cover_required_capabilities():
    service = AgentService()
    names = {spec["name"] for spec in service.tool_specs()}
    assert {"fs.list", "fs.read", "fs.edit", "fs.write", "fs.mkdir", "fs.delete", "terminal"} <= names


async def test_execute_tool_rejects_unknown(tmp_path):
    import pytest

    from app.core.errors import NotFoundError

    service = AgentService()
    await service.set_workspace(str(tmp_path))
    with pytest.raises(NotFoundError):
        await service.execute_tool("does.not.exist", {})
