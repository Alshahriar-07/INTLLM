"""Agent runtime service.

The Agent works inside a single user-selected **workspace** directory. Every
filesystem path is resolved against that workspace and rejected when it escapes
it, so enabling Agent mode never exposes the whole filesystem. Destructive or
arbitrary-execution operations (overwrite, delete, move, terminal) require an
explicit approval decision; harmless reads/lists/searches run without one and a
``allow_session`` decision can suppress repeat prompts for the session.

Nothing here fabricates results: an unavailable workspace or a refused command
is reported as an explicit state.
"""

from __future__ import annotations

import asyncio
import os
import platform
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.config.settings import get_settings
from app.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from app.core.logging import get_logger
from app.db.models import AppSetting
from app.db.session import get_database

logger = get_logger(__name__)

WORKSPACE_SETTING_KEY = "agent.workspace"
PERMISSION_MODE_SETTING_KEY = "agent.permission_mode"

#: The only two permission choices the user sees.
PERMISSION_ALLOW = "allow"
PERMISSION_ASK = "ask"
DEFAULT_PERMISSION_MODE = PERMISSION_ASK
PERMISSION_MODES = (PERMISSION_ALLOW, PERMISSION_ASK)

# Directories never traversed by the workspace search/listing helpers.
_IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    ".cache",
    ".idea",
    ".vscode",
}

# Files larger than this are not scanned by content search.
_SEARCH_MAX_FILE_BYTES = 1_000_000


class AgentOperation(str, Enum):
    READ = "fs.read"
    LIST = "fs.list"
    SEARCH = "fs.search"
    CREATE = "fs.create"
    WRITE = "fs.write"
    EDIT = "fs.edit"
    DELETE = "fs.delete"
    MOVE = "fs.move"
    TERMINAL = "terminal.execute"


# Operations that change the workspace and therefore require an explicit
# approval decision in ASK ME mode (they are auto-approved in ALLOW mode).
# Creating a file/folder is included: ASK ME asks before anything that changes
# the workspace; only reads/lists/searches run without prompting.
_APPROVAL_REQUIRED = {
    AgentOperation.CREATE,
    AgentOperation.WRITE,
    AgentOperation.EDIT,
    AgentOperation.DELETE,
    AgentOperation.MOVE,
    AgentOperation.TERMINAL,
}

_OPERATION_RISK: dict[AgentOperation, str] = {
    AgentOperation.READ: "Low",
    AgentOperation.LIST: "Low",
    AgentOperation.SEARCH: "Low",
    AgentOperation.CREATE: "Low",
    AgentOperation.WRITE: "High",
    AgentOperation.EDIT: "High",
    AgentOperation.DELETE: "High",
    AgentOperation.MOVE: "Medium",
    AgentOperation.TERMINAL: "Critical",
}

#: Tools the model may call in Agent mode. Every one is executed through the
#: workspace sandbox and the permission gate (see ``AgentService.execute_tool``).
AGENT_TOOL_SPECS: tuple[dict[str, Any], ...] = (
    {
        "name": "fs.list",
        "description": "List files and subfolders inside the workspace.",
        "args": {"path": "optional path relative to the workspace (default '.') "},
    },
    {
        "name": "fs.read",
        "description": "Read a UTF-8 text file in the workspace.",
        "args": {"path": "file path relative to the workspace"},
    },
    {
        "name": "fs.search",
        "description": "Search file contents inside the workspace for a string.",
        "args": {"query": "text to find", "path": "optional subfolder"},
    },
    {
        "name": "fs.write",
        "description": "Create a file or overwrite an existing file with content.",
        "args": {"path": "file path", "content": "full file content"},
    },
    {
        "name": "fs.edit",
        "description": "Replace an exact piece of text inside an existing file.",
        "args": {
            "path": "file path",
            "find": "exact text to replace",
            "replace": "replacement text",
        },
    },
    {
        "name": "fs.mkdir",
        "description": "Create a folder inside the workspace.",
        "args": {"path": "folder path"},
    },
    {
        "name": "fs.delete",
        "description": "Delete a file or folder inside the workspace.",
        "args": {"path": "path to delete"},
    },
    {
        "name": "fs.move",
        "description": "Move or rename a path inside the workspace.",
        "args": {"source": "current path", "destination": "new path"},
    },
    {
        "name": "terminal",
        "description": "Run a shell command with the workspace as the working directory.",
        "args": {"command": "shell command", "cwd": "optional subfolder"},
    },
)


def _require_arg(args: dict[str, Any], name: str) -> str:
    value = args.get(name)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"Missing required tool argument '{name}'")
    return value if isinstance(value, str) else str(value)


#: Maps model-facing tool names (and short aliases) onto the operation used for
#: permission and risk decisions.
AGENT_TOOL_OPERATIONS: dict[str, AgentOperation] = {
    "fs.list": AgentOperation.LIST,
    "list": AgentOperation.LIST,
    "fs.read": AgentOperation.READ,
    "read": AgentOperation.READ,
    "fs.search": AgentOperation.SEARCH,
    "search": AgentOperation.SEARCH,
    "fs.write": AgentOperation.WRITE,
    "write": AgentOperation.WRITE,
    "fs.create": AgentOperation.CREATE,
    "create": AgentOperation.CREATE,
    "fs.edit": AgentOperation.EDIT,
    "edit": AgentOperation.EDIT,
    "fs.mkdir": AgentOperation.CREATE,
    "mkdir": AgentOperation.CREATE,
    "fs.delete": AgentOperation.DELETE,
    "delete": AgentOperation.DELETE,
    "fs.move": AgentOperation.MOVE,
    "move": AgentOperation.MOVE,
    "terminal": AgentOperation.TERMINAL,
    "terminal.execute": AgentOperation.TERMINAL,
    "run": AgentOperation.TERMINAL,
}


@dataclass(slots=True)
class AgentResult:
    operation: str
    status: str  # completed | permission_required | denied | failed
    output: dict[str, Any] | None = None
    error: str | None = None
    target: str | None = None
    risk: str = "Low"
    duration_ms: float = 0.0
    permission: str = "read-only"

    def as_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "status": self.status,
            "output": self.output,
            "error": self.error,
            "target": self.target,
            "risk": self.risk,
            "duration_ms": self.duration_ms,
            "permission": self.permission,
        }


@dataclass(slots=True)
class WorkspaceStatus:
    configured: bool
    path: str | None = None
    exists: bool = False
    writable: bool = False
    file_count: int | None = None
    session_grants: list[str] = field(default_factory=list)
    terminal_enabled: bool = True
    permission_mode: str = DEFAULT_PERMISSION_MODE
    name: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "configured": self.configured,
            "path": self.path,
            "name": self.name,
            "exists": self.exists,
            "writable": self.writable,
            "file_count": self.file_count,
            "session_grants": self.session_grants,
            "terminal_enabled": self.terminal_enabled,
            "permission_mode": self.permission_mode,
        }


class AgentService:
    """Workspace-scoped, permission-gated Agent runtime."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._workspace: Path | None = None
        self._grants: set[str] = set()
        self._loaded = False
        self._permission_mode: str = DEFAULT_PERMISSION_MODE

    # --- workspace --------------------------------------------------------
    @property
    def workspace(self) -> Path | None:
        return self._workspace

    @property
    def permission_mode(self) -> str:
        return self._permission_mode

    def _require_workspace(self) -> Path:
        if self._workspace is None:
            raise ValidationError(
                "No Agent workspace is selected. Choose a folder before using Agent mode."
            )
        return self._workspace

    async def ensure_loaded(self) -> None:
        """Load the persisted workspace once (best-effort; DB may be down)."""
        if self._loaded:
            return
        self._loaded = True
        try:
            database = get_database()
            available, _ = await database.ping()
            if not available:
                return
            async with database.session() as session:
                records = await session.execute(
                    select(AppSetting).where(
                        AppSetting.key.in_(
                            [WORKSPACE_SETTING_KEY, PERMISSION_MODE_SETTING_KEY]
                        )
                    )
                )
                values = {record.key: record.value for record in records.scalars().all()}
            workspace_value = values.get(WORKSPACE_SETTING_KEY) or {}
            if isinstance(workspace_value, dict):
                raw = workspace_value.get("path")
                if raw:
                    candidate = Path(str(raw)).expanduser()
                    if candidate.is_dir():
                        self._workspace = candidate.resolve()
            permission_value = values.get(PERMISSION_MODE_SETTING_KEY) or {}
            if isinstance(permission_value, dict):
                mode = str(permission_value.get("mode", "")).strip().lower()
                if mode in PERMISSION_MODES:
                    self._permission_mode = mode
        except Exception as exc:  # noqa: BLE001 - workspace persistence is best-effort
            logger.warning(
                "could not load agent workspace", extra={"intllm_extra": {"error": str(exc)}}
            )

    async def set_workspace(self, raw_path: str) -> WorkspaceStatus:
        if not raw_path or not raw_path.strip():
            raise ValidationError("Workspace path must not be empty")
        candidate = Path(raw_path.strip()).expanduser()
        try:
            resolved = candidate.resolve()
        except OSError as exc:
            raise ValidationError(f"Invalid workspace path: {exc}") from exc
        if not resolved.exists():
            raise NotFoundError(f"Workspace folder does not exist: {resolved}")
        if not resolved.is_dir():
            raise ValidationError(f"Workspace path is not a folder: {resolved}")
        self._workspace = resolved
        # A new workspace resets session grants so old approvals never carry over.
        self._grants.clear()
        await self._persist_workspace(resolved)
        return await self.status()

    async def pick_folder(self) -> str | None:
        """Open a real native folder chooser for the OS (best-effort).

        Windows uses the shell's FolderBrowserDialog (PowerShell), macOS uses
        ``choose folder`` via osascript, Linux uses zenity/kdialog, and Tk is the
        final cross-platform fallback. Returns ``None`` when no GUI is available
        (headless) or the user cancels, so the UI can fall back to manual path
        entry rather than pretending a folder was chosen.
        """
        try:
            return await asyncio.to_thread(pick_folder_native)
        except Exception as exc:  # noqa: BLE001 - GUI is optional
            logger.info("native folder picker unavailable: %s", exc)
            return None

    async def clear_workspace(self) -> WorkspaceStatus:
        self._workspace = None
        self._grants.clear()
        await self._persist_setting(WORKSPACE_SETTING_KEY, {"path": None})
        return await self.status()

    async def set_permission_mode(self, mode: str) -> str:
        """Switch between ALLOW and ASK ME. Persisted locally in app_settings."""
        normalized = (mode or "").strip().lower()
        if normalized not in PERMISSION_MODES:
            raise ValidationError("Permission mode must be 'allow' or 'ask'")
        self._permission_mode = normalized
        await self._persist_setting(PERMISSION_MODE_SETTING_KEY, {"mode": normalized})
        return normalized

    async def _persist_workspace(self, path: Path | None) -> None:
        await self._persist_setting(
            WORKSPACE_SETTING_KEY, {"path": str(path) if path else None}
        )

    async def _persist_setting(self, key: str, value: dict[str, Any]) -> None:
        try:
            database = get_database()
            available, _ = await database.ping()
            if not available:
                return
            async with database.session() as session:
                record = await session.scalar(
                    select(AppSetting).where(AppSetting.key == key)
                )
                if record is not None:
                    record.value = value
                else:
                    session.add(AppSetting(key=key, value=value))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "could not persist agent setting",
                extra={"intllm_extra": {"key": key, "error": str(exc)}},
            )

    async def status(self) -> WorkspaceStatus:
        await self.ensure_loaded()
        path = self._workspace
        if path is None:
            return WorkspaceStatus(
                configured=False,
                terminal_enabled=self._settings.intllm_agent_terminal_enabled,
                session_grants=sorted(self._grants),
                permission_mode=self._permission_mode,
            )
        exists = path.is_dir()
        writable = exists and _is_writable(path)
        file_count = len(self._quick_listing(path)) if exists else None
        return WorkspaceStatus(
            configured=True,
            path=str(path),
            name=path.name,
            exists=exists,
            writable=writable,
            file_count=file_count,
            terminal_enabled=self._settings.intllm_agent_terminal_enabled,
            session_grants=sorted(self._grants),
            permission_mode=self._permission_mode,
        )

    # --- permissions ------------------------------------------------------
    def grant_session(self, operation: str) -> None:
        if operation not in {op.value for op in AgentOperation}:
            raise NotFoundError(f"Unknown agent operation: {operation}")
        self._grants.add(operation)

    def revoke_session(self, operation: str) -> None:
        self._grants.discard(operation)

    def session_grants(self) -> list[str]:
        return sorted(self._grants)

    def _authorize(
        self,
        operation: AgentOperation,
        decision: str | None,
        *,
        target: str | None,
    ) -> tuple[bool, AgentResult | None]:
        """Return (allowed, blocked_result).

        Read-only operations always run. In ALLOW mode every workspace action is
        auto-approved (the sandbox still applies); in ASK ME mode an explicit
        per-action decision is required.
        """
        if operation not in _APPROVAL_REQUIRED:
            return True, None
        if self._permission_mode == PERMISSION_ALLOW:
            return True, None
        if decision == "allow_session":
            self._grants.add(operation.value)
        granted = decision in ("allow", "allow_session") or operation.value in self._grants
        if granted:
            return True, None
        denied = decision == "deny"
        return False, AgentResult(
            operation=operation.value,
            status="denied" if denied else "permission_required",
            error=(
                "The user denied this operation"
                if denied
                else "Explicit user approval is required before this operation"
            ),
            target=target,
            risk=_OPERATION_RISK[operation],
            permission="requires-approval",
        )

    # --- path sandbox -----------------------------------------------------
    def resolve(self, raw_path: str | None) -> Path:
        workspace = self._require_workspace()
        if raw_path is None or str(raw_path).strip() in ("", "."):
            return workspace
        candidate = Path(str(raw_path).strip()).expanduser()
        candidate = candidate if candidate.is_absolute() else workspace / candidate
        resolved = candidate.resolve()
        if resolved != workspace and workspace not in resolved.parents:
            raise PermissionDeniedError(
                f"Path is outside the Agent workspace: {resolved}"
            )
        return resolved

    def _relative(self, path: Path) -> str:
        workspace = self._workspace
        if workspace is None:
            return str(path)
        try:
            return path.relative_to(workspace).as_posix() or "."
        except ValueError:
            return str(path)

    # --- filesystem read --------------------------------------------------
    def _quick_listing(self, root: Path) -> list[Path]:
        entries: list[Path] = []
        try:
            for child in root.iterdir():
                if child.name in _IGNORED_DIRS:
                    continue
                entries.append(child)
        except OSError:
            return []
        return entries

    async def list_dir(self, raw_path: str | None = None) -> AgentResult:
        started = time.perf_counter()
        target = self.resolve(raw_path)
        if not target.exists():
            raise NotFoundError(f"Path not found: {self._relative(target)}")
        if target.is_file():
            raise ValidationError(f"Not a directory: {self._relative(target)}")
        entries: list[dict[str, Any]] = []
        for child in sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            if child.name in _IGNORED_DIRS:
                continue
            try:
                stat = child.stat()
                size = stat.st_size if child.is_file() else None
            except OSError:
                size = None
            entries.append(
                {
                    "name": child.name,
                    "path": self._relative(child),
                    "isDir": child.is_dir(),
                    "size": size,
                }
            )
        return AgentResult(
            operation=AgentOperation.LIST.value,
            status="completed",
            output={"path": self._relative(target), "entries": entries},
            target=self._relative(target),
            duration_ms=round((time.perf_counter() - started) * 1000.0, 2),
        )

    async def read_file(self, raw_path: str) -> AgentResult:
        started = time.perf_counter()
        target = self.resolve(raw_path)
        if not target.exists():
            raise NotFoundError(f"File not found: {self._relative(target)}")
        if not target.is_file():
            raise ValidationError(f"Not a file: {self._relative(target)}")
        max_bytes = self._settings.intllm_agent_max_read_bytes
        size = target.stat().st_size
        truncated = size > max_bytes
        content, binary = await asyncio.to_thread(_read_text_safe, target, max_bytes)
        return AgentResult(
            operation=AgentOperation.READ.value,
            status="completed",
            output={
                "path": self._relative(target),
                # Binary files return metadata only; never dump raw bytes.
                "content": content,
                "binary": binary,
                "truncated": truncated,
                "size": size,
            },
            target=self._relative(target),
            duration_ms=round((time.perf_counter() - started) * 1000.0, 2),
        )

    async def edit_file(
        self,
        raw_path: str,
        find: str,
        replace: str,
        *,
        decision: str | None = None,
        replace_all: bool = False,
    ) -> AgentResult:
        """Apply a targeted text replacement to an existing file.

        Fails safely when the target text is absent (no silent partial writes),
        and verifies the written content afterwards.
        """
        target = self.resolve(raw_path)
        if not target.exists():
            raise NotFoundError(f"File not found: {self._relative(target)}")
        if not target.is_file():
            raise ValidationError(f"Not a file: {self._relative(target)}")
        if not find:
            raise ValidationError("The text to find must not be empty")
        allowed, blocked = self._authorize(
            AgentOperation.EDIT, decision, target=self._relative(target)
        )
        if not allowed:
            return blocked  # type: ignore[return-value]

        def _do_edit() -> tuple[str, int]:
            try:
                text = target.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                raise ValidationError(
                    f"Not a UTF-8 text file: {self._relative(target)}"
                ) from exc
            occurrences = text.count(find)
            if occurrences == 0:
                raise ValidationError(
                    f"Text to replace was not found in {self._relative(target)}"
                )
            updated = (
                text.replace(find, replace)
                if replace_all
                else text.replace(find, replace, 1)
            )
            target.write_text(updated, encoding="utf-8")
            return updated, (occurrences if replace_all else 1)

        started = time.perf_counter()
        updated_text, replacements = await asyncio.to_thread(_do_edit)
        if len(updated_text.encode("utf-8")) > self._settings.intllm_agent_max_write_bytes:
            raise ValidationError("Resulting content exceeds the Agent write size limit")
        return AgentResult(
            operation=AgentOperation.EDIT.value,
            status="completed",
            output={
                "path": self._relative(target),
                "replacements": replacements,
                "bytesWritten": len(updated_text.encode("utf-8")),
                "created": False,
            },
            target=self._relative(target),
            risk=_OPERATION_RISK[AgentOperation.EDIT],
            permission="requires-approval",
            duration_ms=round((time.perf_counter() - started) * 1000.0, 2),
        )

    async def search(self, query: str, raw_path: str | None = None) -> AgentResult:
        if not query or not query.strip():
            raise ValidationError("Search query must not be empty")
        started = time.perf_counter()
        root = self.resolve(raw_path)
        limit = self._settings.intllm_agent_max_search_results
        matches = await asyncio.to_thread(_search_workspace, root, query.strip(), limit)
        return AgentResult(
            operation=AgentOperation.SEARCH.value,
            status="completed",
            output={"query": query, "matches": matches, "truncated": len(matches) >= limit},
            target=self._relative(root),
            duration_ms=round((time.perf_counter() - started) * 1000.0, 2),
        )

    # --- filesystem write -------------------------------------------------
    async def write_file(
        self, raw_path: str, content: str, *, decision: str | None = None
    ) -> AgentResult:
        workspace = self._require_workspace()
        target = self.resolve(raw_path)
        if target == workspace or target.is_dir():
            raise ValidationError(f"Cannot write to a directory: {self._relative(target)}")
        exists = target.exists()
        operation = AgentOperation.WRITE if exists else AgentOperation.CREATE
        allowed, blocked = self._authorize(
            operation, decision, target=self._relative(target)
        )
        if not allowed:
            return blocked  # type: ignore[return-value]
        data = content.encode("utf-8")
        if len(data) > self._settings.intllm_agent_max_write_bytes:
            raise ValidationError("Content exceeds the Agent write size limit")
        started = time.perf_counter()

        def _do_write() -> int:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            return len(data)

        written = await asyncio.to_thread(_do_write)
        return AgentResult(
            operation=operation.value,
            status="completed",
            output={"path": self._relative(target), "bytesWritten": written, "created": not exists},
            target=self._relative(target),
            risk=_OPERATION_RISK[operation],
            permission=(
                "requires-approval" if operation is AgentOperation.WRITE else "read-only"
            ),
            duration_ms=round((time.perf_counter() - started) * 1000.0, 2),
        )

    async def create_dir(self, raw_path: str, *, decision: str | None = None) -> AgentResult:
        target = self.resolve(raw_path)
        if target.exists():
            raise ValidationError(f"Path already exists: {self._relative(target)}")
        allowed, blocked = self._authorize(
            AgentOperation.CREATE, decision, target=self._relative(target)
        )
        if not allowed:
            return blocked  # type: ignore[return-value]
        started = time.perf_counter()
        await asyncio.to_thread(lambda: target.mkdir(parents=True, exist_ok=True))
        return AgentResult(
            operation=AgentOperation.CREATE.value,
            status="completed",
            output={"path": self._relative(target), "created": True},
            target=self._relative(target),
            duration_ms=round((time.perf_counter() - started) * 1000.0, 2),
        )

    async def delete(self, raw_path: str, *, decision: str | None = None) -> AgentResult:
        workspace = self._require_workspace()
        target = self.resolve(raw_path)
        if target == workspace:
            raise PermissionDeniedError("Refusing to delete the workspace root")
        if not target.exists():
            raise NotFoundError(f"Path not found: {self._relative(target)}")
        allowed, blocked = self._authorize(
            AgentOperation.DELETE, decision, target=self._relative(target)
        )
        if not allowed:
            return blocked  # type: ignore[return-value]
        started = time.perf_counter()
        await asyncio.to_thread(_delete_path, target)
        return AgentResult(
            operation=AgentOperation.DELETE.value,
            status="completed",
            output={"path": self._relative(target), "deleted": True},
            target=self._relative(target),
            risk=_OPERATION_RISK[AgentOperation.DELETE],
            permission="requires-approval",
            duration_ms=round((time.perf_counter() - started) * 1000.0, 2),
        )

    async def move(
        self, raw_source: str, raw_destination: str, *, decision: str | None = None
    ) -> AgentResult:
        source = self.resolve(raw_source)
        destination = self.resolve(raw_destination)
        if not source.exists():
            raise NotFoundError(f"Source not found: {self._relative(source)}")
        if destination.exists():
            raise ValidationError(f"Destination already exists: {self._relative(destination)}")
        allowed, blocked = self._authorize(
            AgentOperation.MOVE,
            decision,
            target=f"{self._relative(source)} -> {self._relative(destination)}",
        )
        if not allowed:
            return blocked  # type: ignore[return-value]
        started = time.perf_counter()

        def _do_move() -> None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.rename(destination)

        await asyncio.to_thread(_do_move)
        return AgentResult(
            operation=AgentOperation.MOVE.value,
            status="completed",
            output={
                "source": self._relative(source),
                "destination": self._relative(destination),
            },
            target=self._relative(destination),
            risk=_OPERATION_RISK[AgentOperation.MOVE],
            permission="requires-approval",
            duration_ms=round((time.perf_counter() - started) * 1000.0, 2),
        )

    # --- terminal ---------------------------------------------------------
    async def run_command(
        self,
        command: str,
        *,
        cwd: str | None = None,
        decision: str | None = None,
        cancel: asyncio.Event | None = None,
    ) -> AgentResult:
        workspace = self._require_workspace()
        if not self._settings.intllm_agent_terminal_enabled:
            raise PermissionDeniedError("Terminal execution is disabled in INTLLM configuration")
        if not command or not command.strip():
            raise ValidationError("Command must not be empty")
        workdir = self.resolve(cwd) if cwd else workspace
        if workdir.is_file():
            workdir = workdir.parent
        allowed, blocked = self._authorize(
            AgentOperation.TERMINAL, decision, target=command.strip()
        )
        if not allowed:
            return blocked  # type: ignore[return-value]

        started = time.perf_counter()
        timeout = self._settings.intllm_agent_terminal_timeout_seconds
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=str(workdir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        timed_out = False
        cancelled = False
        stdout_b = stderr_b = b""
        try:
            communicate = asyncio.ensure_future(proc.communicate())
            cancel_task: asyncio.Future | None = None
            waiters: set[asyncio.Future] = {communicate}
            if cancel is not None:
                cancel_task = asyncio.ensure_future(cancel.wait())
                waiters.add(cancel_task)
            done, _pending = await asyncio.wait(
                waiters, timeout=timeout, return_when=asyncio.FIRST_COMPLETED
            )
            if communicate in done:
                stdout_b, stderr_b = communicate.result()
            elif cancel_task is not None and cancel_task in done:
                cancelled = True
                proc.kill()
                stdout_b, stderr_b = await communicate
            else:
                timed_out = True
                proc.kill()
                stdout_b, stderr_b = await communicate
            if cancel_task is not None and not cancel_task.done():
                cancel_task.cancel()
        except asyncio.CancelledError:
            # Client disconnected mid-command: never leave the process running.
            proc.kill()
            raise
        duration = round((time.perf_counter() - started) * 1000.0, 2)
        status = "cancelled" if cancelled else ("failed" if timed_out else "completed")
        error = "Command cancelled" if cancelled else ("Command timed out" if timed_out else None)
        return AgentResult(
            operation=AgentOperation.TERMINAL.value,
            status=status,
            output={
                "command": command,
                "cwd": self._relative(workdir),
                "exitCode": proc.returncode,
                "stdout": stdout_b.decode("utf-8", errors="replace")[-20000:],
                "stderr": stderr_b.decode("utf-8", errors="replace")[-20000:],
                "timedOut": timed_out,
                "cancelled": cancelled,
                "timeoutSeconds": timeout,
                "outsideWorkspaceHint": _mentions_outside_paths(command, workspace),
            },
            error=error,
            target=command.strip(),
            risk=_OPERATION_RISK[AgentOperation.TERMINAL],
            permission="requires-approval",
            duration_ms=duration,
        )

    # --- unified tool dispatcher -----------------------------------------
    def tool_specs(self) -> list[dict[str, Any]]:
        """Machine-readable descriptions of the workspace tools the Agent may call."""
        return [dict(spec) for spec in AGENT_TOOL_SPECS]

    def operation_for_tool(self, name: str) -> AgentOperation | None:
        return AGENT_TOOL_OPERATIONS.get(name)

    def tool_requires_approval(self, name: str) -> bool:
        """True when the tool changes the workspace (needs approval in ASK ME)."""
        operation = AGENT_TOOL_OPERATIONS.get(name)
        if operation is None:
            return True
        return operation in _APPROVAL_REQUIRED

    async def execute_tool(
        self,
        name: str,
        args: dict[str, Any] | None,
        *,
        decision: str | None = None,
        cancel: asyncio.Event | None = None,
    ) -> AgentResult:
        """Route a model tool call through workspace validation + permission."""
        args = args or {}
        if name in ("fs.list", "list"):
            return await self.list_dir(args.get("path"))
        if name in ("fs.read", "read"):
            return await self.read_file(_require_arg(args, "path"))
        if name in ("fs.search", "search"):
            return await self.search(_require_arg(args, "query"), args.get("path"))
        if name in ("fs.write", "write", "fs.create", "create"):
            return await self.write_file(
                _require_arg(args, "path"),
                str(args.get("content", "")),
                decision=decision,
            )
        if name in ("fs.edit", "edit"):
            return await self.edit_file(
                _require_arg(args, "path"),
                _require_arg(args, "find"),
                str(args.get("replace", "")),
                decision=decision,
                replace_all=bool(args.get("replace_all")),
            )
        if name in ("fs.mkdir", "mkdir"):
            return await self.create_dir(_require_arg(args, "path"), decision=decision)
        if name in ("fs.delete", "delete"):
            return await self.delete(_require_arg(args, "path"), decision=decision)
        if name in ("fs.move", "move"):
            return await self.move(
                _require_arg(args, "source"),
                _require_arg(args, "destination"),
                decision=decision,
            )
        if name in ("terminal", "terminal.execute", "run"):
            return await self.run_command(
                _require_arg(args, "command"), cwd=args.get("cwd"), decision=decision,
                cancel=cancel,
            )
        raise NotFoundError(f"Unknown agent tool: {name}")


# --- blocking helpers ----------------------------------------------------------

_PICK_TITLE = "Select INTLLM Agent workspace"


def _tk_pick_folder() -> str | None:
    import tkinter
    from tkinter import filedialog

    root = tkinter.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askdirectory(title=_PICK_TITLE)
    finally:
        root.destroy()
    return selected or None


def _windows_pick_folder() -> str | None:
    """Native Windows folder dialog via PowerShell + WinForms.

    Works from the packaged executable without requiring Tk, and is STA so the
    WinForms dialog renders correctly.
    """
    if not shutil.which("powershell"):
        return None
    script = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "$d = New-Object System.Windows.Forms.FolderBrowserDialog;"
        f"$d.Description = '{_PICK_TITLE}';"
        "$d.ShowNewFolderButton = $true;"
        "if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK)"
        " { Write-Output $d.SelectedPath }"
    )
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-STA",
                "-NonInteractive",
                "-Command",
                script,
            ],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as exc:  # noqa: BLE001 - fall back to Tk
        logger.info("powershell folder picker failed: %s", exc)
        return None
    selected = (result.stdout or "").strip()
    return selected or None


def _macos_pick_folder() -> str | None:
    if not shutil.which("osascript"):
        return None
    try:
        result = subprocess.run(
            [
                "osascript",
                "-e",
                f'POSIX path of (choose folder with prompt "{_PICK_TITLE}")',
            ],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        logger.info("osascript folder picker failed: %s", exc)
        return None
    if result.returncode != 0:
        return None
    return (result.stdout or "").strip() or None


def _linux_pick_folder() -> str | None:
    commands: list[list[str]] = []
    if shutil.which("zenity"):
        commands.append(
            ["zenity", "--file-selection", "--directory", f"--title={_PICK_TITLE}"]
        )
    if shutil.which("kdialog"):
        commands.append(["kdialog", "--getexistingdirectory", os.path.expanduser("~")])
    for command in commands:
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=300, check=False
            )
        except Exception:  # noqa: BLE001
            continue
        if result.returncode == 0 and (result.stdout or "").strip():
            return result.stdout.strip()
    return None


def pick_folder_native() -> str | None:
    """Return a user-selected folder using the most native mechanism available."""
    system = platform.system()
    selected: str | None = None
    if system == "Windows":
        selected = _windows_pick_folder() or _tk_pick_folder()
    elif system == "Darwin":
        selected = _macos_pick_folder() or _tk_pick_folder()
    else:
        selected = _linux_pick_folder() or _tk_pick_folder()
    return selected or None


def _read_text_safe(path: Path, max_bytes: int) -> tuple[str | None, bool]:
    """Return ``(text, is_binary)``. Binary files never return raw bytes."""
    with path.open("rb") as handle:
        data = handle.read(max_bytes)
    if b"\x00" in data[:8000]:
        return None, True
    return data.decode("utf-8", errors="replace"), False


def _is_writable(path: Path) -> bool:
    try:
        probe = path / ".intllm_write_probe"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def _delete_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        for child in path.iterdir():
            _delete_path(child)
        path.rmdir()
    else:
        path.unlink()


def _search_workspace(root: Path, query: str, limit: int) -> list[dict[str, Any]]:
    needle = query.lower()
    matches: list[dict[str, Any]] = []
    for file in _walk_files(root):
        if len(matches) >= limit:
            break
        try:
            if file.stat().st_size > _SEARCH_MAX_FILE_BYTES:
                continue
            text = file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if needle in line.lower():
                try:
                    rel = file.relative_to(root).as_posix()
                except ValueError:
                    rel = str(file)
                matches.append(
                    {
                        "path": rel,
                        "line": line_number,
                        "text": line.strip()[:300],
                    }
                )
                if len(matches) >= limit:
                    break
    return matches


def _walk_files(root: Path):
    if root.is_file():
        yield root
        return
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            children = list(current.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_dir():
                if child.name in _IGNORED_DIRS:
                    continue
                stack.append(child)
            elif child.is_file():
                yield child


def _mentions_outside_paths(command: str, workspace: Path) -> bool:
    """Best-effort hint that a command references paths outside the workspace.

    Informational only: all terminal commands already require approval. A path
    token that resolves outside the workspace is flagged so the UI can warn.
    """
    try:
        tokens = shlex.split(command, posix=False)
    except ValueError:
        tokens = command.split()
    for token in tokens:
        stripped = token.strip("\"'")
        if not stripped or stripped.startswith("-"):
            continue
        looks_absolute = (
            stripped.startswith("/")
            or (len(stripped) > 2 and stripped[1] == ":" and stripped[2] in ("\\", "/"))
        )
        if not looks_absolute:
            continue
        try:
            resolved = Path(stripped).expanduser().resolve()
        except OSError:
            continue
        if resolved != workspace and workspace not in resolved.parents:
            return True
    return False


_agent: AgentService | None = None


def get_agent_service() -> AgentService:
    global _agent
    if _agent is None:
        _agent = AgentService()
    return _agent
