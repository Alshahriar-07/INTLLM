"""End-to-end Agent workflow against a REAL local Ollama model.

This is the only test that exercises the full stack for real: the live model
proposes tool calls, INTLLM executes them against a real temporary workspace,
and the resulting files/commands are verified on disk. It is opt-in because it
requires a running Ollama with an installed model and is inherently slow.

Run it with::

    INTLLM_E2E_OLLAMA=1 INTLLM_E2E_MODEL=qwen2.5-coder:7b \\
        python -m pytest -o addopts="" tests/test_agent_e2e_ollama.py

Without ``INTLLM_E2E_OLLAMA`` it is skipped so the default suite stays hermetic.
"""

from __future__ import annotations

import os

import pytest

from app.services.agent.service import get_agent_service
from app.services.chat.service import ChatRequest, ChatService
from app.services.runtime.base import ChatMessage
from app.services.runtime.ollama import get_ollama_adapter

pytestmark = pytest.mark.skipif(
    not os.environ.get("INTLLM_E2E_OLLAMA"),
    reason="set INTLLM_E2E_OLLAMA=1 to run the real-Ollama Agent E2E",
)

MODEL = os.environ.get("INTLLM_E2E_MODEL", "gemma3:4b")

_TASK = (
    "Complete this task using tools, one step at a time.\n"
    "1) List the files in the workspace.\n"
    "2) Read the file data.txt.\n"
    "3) Create a file report.txt whose content is exactly: lines=3\n"
    "4) Run this exact shell command: "
    "python -c \"print('LINES=' + str(sum(1 for _ in open('report.txt'))))\"\n"
    "5) Give your final answer summarizing what really happened."
)


async def test_real_agent_multistep_workflow(tmp_path):
    adapter = get_ollama_adapter()
    try:
        models = {info.name for info in await adapter.list_models()}
    except Exception as exc:  # noqa: BLE001 - Ollama is an external dependency
        pytest.skip(f"Ollama is not reachable: {exc}")
    if MODEL not in models:
        pytest.skip(f"model '{MODEL}' is not installed in Ollama")

    (tmp_path / "data.txt").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

    service = get_agent_service()
    await service.set_workspace(str(tmp_path))
    await service.set_permission_mode("allow")
    try:
        request = ChatRequest(
            messages=[ChatMessage(role="user", content=_TASK)],
            model=MODEL,
            mode="agent",
            use_brain=False,
            use_web=False,
        )
        events = [event async for event in ChatService().stream(request)]
    finally:
        await service.clear_workspace()

    tool_events = [e for e in events if e["type"] == "agent.tool.completed"]
    done = {e["data"]["tool"] for e in tool_events if e["data"]["status"] == "completed"}

    # The agent really listed/read/wrote and ran a command against the workspace.
    assert "fs.list" in done
    assert "fs.write" in done
    assert "terminal" in done

    # The write is a real file on disk with the requested content.
    report = tmp_path / "report.txt"
    assert report.is_file()
    assert report.read_text(encoding="utf-8").strip() == "lines=3"

    # The terminal result reported a real exit code (not fabricated).
    terminal = next(e for e in tool_events if e["data"]["tool"] == "terminal")
    assert terminal["data"]["detail"].startswith("exit ")

    # The exchange ended with a final answer event.
    assert events[-1]["type"] == "chat.completed"
    assert any(e["type"] == "agent.final" for e in events)
