"""Model-driven Agent loop.

The Agent is not a single completion: it runs a bounded loop in which the local
model proposes tool calls, INTLLM validates each call against the workspace,
applies the Allow / Ask Me permission gate, performs the real filesystem or
terminal operation, and feeds the structured result back to the model until it
produces a final answer.

Protocol
--------
Models served by Ollama do not all support native tool calling, so INTLLM uses a
small, robust JSON protocol:

* to call a tool the model replies with a single JSON object, e.g.
  ``{"tool": "fs.read", "args": {"path": "src/main.py"}}``;
* to finish it replies with ordinary text.

Nothing here fabricates progress: every ``agent.tool.*`` event corresponds to a
real ``AgentService`` operation, and a failing tool returns its real error so the
model can reason about it and retry.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger
from app.services.agent.permissions import (
    DECISION_ALLOW,
    PermissionBroker,
)
from app.services.agent.service import (
    _OPERATION_RISK,
    AGENT_TOOL_OPERATIONS,
    AgentResult,
    AgentService,
)
from app.services.runtime.base import ChatMessage, RuntimeUnavailable

logger = get_logger(__name__)

DEFAULT_MAX_STEPS = 12
PERMISSION_TIMEOUT_SECONDS = 300.0
# Tool output fed back into the model is truncated to keep the context small.
_RESULT_TRANSCRIPT_LIMIT = 6000

def _system_prompt(service: AgentService, *, permission_mode: str) -> str:
    workspace = service.workspace
    tools = "\n".join(
        f"- {spec['name']}: {spec['description']} args={json.dumps(spec['args'])}"
        for spec in service.tool_specs()
    )
    location = f"{workspace.name} ({workspace})" if workspace else "(no workspace selected)"
    mode_hint = (
        "The user set permission mode ALLOW: your workspace actions run automatically."
        if permission_mode == "allow"
        else "The user set permission mode ASK ME: actions that change files or run "
        "commands are shown to the user for explicit Allow/Deny approval."
    )
    return (
        "You are INTLLM Agent, a coding and computer-use assistant that performs "
        "REAL actions inside a single user-selected workspace. The workspace is "
        "your filesystem boundary; never use paths outside it.\n\n"
        f"Workspace: {location}\n"
        f"Available tools:\n{tools}\n\n"
        "HOW TO ACT — READ CAREFULLY\n"
        "- You cannot accomplish anything by describing it in prose. Writing 'I "
        "will create the file' does NOT create anything.\n"
        "- To perform an action you MUST output ONLY a single JSON object of the "
        'form {"tool": "<name>", "args": {...}} and NOTHING else — no markdown '
        "fences, no explanation, no text before or after.\n"
        "- After each tool call you receive a line starting with TOOL RESULT. Read "
        "it, then call the next tool. When the whole task is genuinely done, reply "
        "with your final answer as ordinary text.\n"
        "- Never claim an action succeeded unless its TOOL RESULT shows success.\n"
        "- Do not refuse because a later step depends on an earlier one: perform "
        "the steps in order with tools.\n\n"
        "EXAMPLES (output the JSON exactly like this)\n"
        'List files: {"tool": "fs.list", "args": {}}\n'
        'Read a file: {"tool": "fs.read", "args": {"path": "data.txt"}}\n'
        'Create a file: {"tool": "fs.write", "args": {"path": "report.txt", "content": "lines=3"}}\n'
        'Edit a file: {"tool": "fs.edit", "args": {"path": "a.txt", "find": "old", "replace": "new"}}\n'
        'Run a command: {"tool": "terminal", "args": {"command": "python -c \\"print(1)\\""}}\n\n'
        f"{mode_hint}"
    )


def _try_json(text: str) -> Any:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def _normalize(obj: dict[str, Any]) -> dict[str, Any]:
    args = obj.get("args")
    if not isinstance(args, dict):
        # Accept a flat {"tool": ..., "path": ...} shape too.
        args = {k: v for k, v in obj.items() if k not in ("tool", "name")}
    name = obj.get("tool") or obj.get("name")
    return {"tool": str(name), "args": args}


def _extract_tool_call(text: str) -> dict[str, Any] | None:
    """Return ``{"tool","args"}`` when the model emitted a tool call, else None."""
    if not text:
        return None
    candidate = text.strip()

    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", candidate, re.DOTALL)
    if fenced:
        candidate = fenced.group(1)

    obj = _try_json(candidate)
    if isinstance(obj, dict) and "tool" in obj:
        return _normalize(obj)

    # Scan for the first balanced JSON object containing a "tool" key.
    start = candidate.find("{")
    while start != -1:
        depth = 0
        for index in range(start, len(candidate)):
            char = candidate[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    block = candidate[start : index + 1]
                    found = _try_json(block)
                    if isinstance(found, dict) and "tool" in found:
                        return _normalize(found)
                    break
        start = candidate.find("{", start + 1)
    return None


def _result_summary(result: AgentResult) -> str:
    if result.status != "completed":
        return result.error or result.status
    output = result.output or {}
    # Terminal results report the real exit code and a short tail of stdout so
    # the activity line reflects what actually happened, not just the command.
    if "exitCode" in output:
        code = output.get("exitCode")
        stdout = (output.get("stdout") or "").strip()
        snippet = stdout.splitlines()[-1] if stdout else ""
        return f"exit {code}" + (f": {snippet[:120]}" if snippet else "")
    for key in ("path", "command", "query"):
        if output.get(key):
            return str(output[key])
    return result.operation


def _result_for_transcript(result: AgentResult) -> str:
    payload: dict[str, Any] = {
        "tool": result.operation,
        "status": result.status,
        "success": result.status == "completed",
    }
    if result.error:
        payload["error"] = result.error
    if result.output is not None:
        payload["output"] = _truncate_payload(result.output)
    return json.dumps(payload, ensure_ascii=False, default=str)


def _truncate_payload(output: dict[str, Any]) -> dict[str, Any]:
    trimmed: dict[str, Any] = {}
    for key, value in output.items():
        if isinstance(value, str) and len(value) > _RESULT_TRANSCRIPT_LIMIT:
            trimmed[key] = value[:_RESULT_TRANSCRIPT_LIMIT] + "…[truncated]"
        else:
            trimmed[key] = value
    return trimmed


def _risk_for(name: str) -> str:
    operation = AGENT_TOOL_OPERATIONS.get(name)
    if operation is None:
        return "Low"
    return _OPERATION_RISK.get(operation, "Low")


def _target_hint(args: dict[str, Any]) -> str | None:
    for key in ("path", "source", "command", "query"):
        value = args.get(key)
        if value:
            return str(value)
    return None


def _summary(name: str, args: dict[str, Any]) -> str:
    if name in ("terminal", "terminal.execute", "run"):
        return f"Run command: {args.get('command', '')}"
    if name in ("fs.edit", "edit"):
        return f"Edit {args.get('path', '')}"
    if name in ("fs.write", "write", "fs.create", "create"):
        return f"Write {args.get('path', '')}"
    if name in ("fs.delete", "delete"):
        return f"Delete {args.get('path', '')}"
    if name in ("fs.mkdir", "mkdir"):
        return f"Create folder {args.get('path', '')}"
    if name in ("fs.read", "read"):
        return f"Read {args.get('path', '')}"
    if name in ("fs.list", "list"):
        return f"List {args.get('path') or '.'}"
    if name in ("fs.move", "move"):
        return f"Move {args.get('source', '')} -> {args.get('destination', '')}"
    return name


@dataclass(slots=True)
class AgentLoop:
    service: AgentService
    adapter: Any
    broker: PermissionBroker
    max_steps: int = DEFAULT_MAX_STEPS
    activities: list[dict[str, Any]] = field(default_factory=list)

    async def run(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        options: dict[str, Any] | None = None,
        cancel: Any = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield agent events; the caller forwards them to the SSE stream."""
        workspace = self.service.workspace
        if workspace is None:
            yield {
                "type": "agent.error",
                "data": {"message": "No Agent workspace is selected."},
            }
            return

        if not await self._model_available(model):
            yield {
                "type": "agent.error",
                "data": {
                    "message": (
                        f"The selected model '{model}' is not available in Ollama. "
                        "Select an installed model and try again."
                    ),
                    "code": "model_unavailable",
                },
            }
            return

        transcript: list[ChatMessage] = [
            ChatMessage(
                role="system",
                content=_system_prompt(
                    self.service, permission_mode=self.service.permission_mode
                ),
            ),
            *messages,
        ]
        seen_signatures: dict[str, int] = {}

        for step in range(1, self.max_steps + 1):
            yield {"type": "agent.step", "data": {"step": step, "max": self.max_steps}}
            try:
                text = await self._generate(model, transcript, options)
            except RuntimeUnavailable as exc:
                yield {"type": "agent.error", "data": {"message": str(exc)}}
                return

            call = _extract_tool_call(text)
            if call is None:
                final_text = text.strip()
                if final_text:
                    yield {"type": "assistant.delta", "data": {"content": final_text}}
                else:
                    # The model returned no text (some local models do this after
                    # finishing). Never present that as a silent success: say so.
                    final_text = "Agent finished without a final message."
                    yield {
                        "type": "assistant.delta",
                        "data": {"content": final_text, "synthetic": True},
                    }
                yield {
                    "type": "agent.final",
                    "data": {"content": final_text, "steps": step},
                }
                return

            name = call["tool"]
            args = call["args"] if isinstance(call["args"], dict) else {}
            signature = f"{name}:{json.dumps(args, sort_keys=True, default=str)}"
            seen_signatures[signature] = seen_signatures.get(signature, 0) + 1
            if seen_signatures[signature] > 2:
                note = f"Repeated tool call '{name}' did not make progress; stopping."
                yield {"type": "assistant.delta", "data": {"content": note}}
                yield {"type": "agent.final", "data": {"content": note, "steps": step}}
                return

            target = _target_hint(args)
            risk = _risk_for(name)
            yield {
                "type": "agent.tool.started",
                "data": {
                    "tool": name,
                    "target": target,
                    "summary": _summary(name, args),
                    "risk": risk,
                },
            }

            decision: str | None = None
            if self.service.tool_requires_approval(name):
                if self.service.permission_mode == "allow":
                    decision = DECISION_ALLOW
                else:
                    request = self.broker.create(
                        {
                            "tool": name,
                            "target": target,
                            "summary": _summary(name, args),
                            "command": args.get("command"),
                            "cwd": args.get("cwd"),
                            "risk": risk,
                        }
                    )
                    # Emit the request BEFORE awaiting the user's decision.
                    yield {
                        "type": "agent.permission.required",
                        "data": {
                            "request_id": request.id,
                            "tool": name,
                            "target": target,
                            "summary": _summary(name, args),
                            "command": args.get("command"),
                            "cwd": args.get("cwd"),
                            "risk": risk,
                        },
                    }
                    decision = await self.broker.wait(
                        request, timeout=PERMISSION_TIMEOUT_SECONDS
                    )
                    yield {
                        "type": "agent.permission.resolved",
                        "data": {
                            "request_id": request.id,
                            "allowed": decision == DECISION_ALLOW,
                        },
                    }

            started = time.perf_counter()
            result = await self._run_tool(name, args, decision=decision, cancel=cancel)
            duration = round((time.perf_counter() - started) * 1000.0, 1)
            record = {
                "tool": name,
                "target": result.target,
                "status": result.status,
                "detail": _result_summary(result),
                "durationMs": duration,
                "risk": risk,
            }
            self.activities.append({"type": "agent_tool", **record})
            yield {"type": "agent.tool.completed", "data": record}
            transcript.append(ChatMessage(role="assistant", content=text.strip()))
            transcript.append(
                ChatMessage(
                    role="user",
                    content="TOOL RESULT: " + _result_for_transcript(result),
                )
            )

        stop_note = (
            f"Reached the {self.max_steps}-step limit before finishing. "
            "Ask me to continue if more work is needed."
        )
        yield {"type": "assistant.delta", "data": {"content": stop_note}}
        yield {
            "type": "agent.final",
            "data": {"content": stop_note, "steps": self.max_steps},
        }

    async def _run_tool(
        self,
        name: str,
        args: dict[str, Any],
        *,
        decision: str | None,
        cancel: Any,
    ) -> AgentResult:
        try:
            return await self.service.execute_tool(
                name, args, decision=decision, cancel=cancel
            )
        except Exception as exc:  # noqa: BLE001 - returned to the model as a failure
            return AgentResult(
                operation=name,
                status="failed",
                error=f"{type(exc).__name__}: {exc}",
                target=_target_hint(args),
                risk=_risk_for(name),
                permission="requires-approval",
            )

    async def _generate(
        self, model: str, transcript: list[ChatMessage], options: dict[str, Any] | None
    ) -> str:
        pieces: list[str] = []
        error: str | None = None
        async for chunk in self.adapter.chat(model, transcript, options=options):
            if chunk.type == "delta":
                pieces.append(chunk.content)
            elif chunk.type == "error":
                error = chunk.error
                break
        if error:
            raise RuntimeUnavailable(error)
        return "".join(pieces)

    async def _model_available(self, model: str) -> bool:
        try:
            models = await self.adapter.list_models()
        except Exception:  # noqa: BLE001 - inventory failure is surfaced by the caller
            return True
        return any(info.name == model for info in models)
