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
import shlex
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
    DELETE = "fs.delete"
    MOVE = "fs.move"
    TERMINAL = "terminal.execute"


# Operations that require an explicit approval decision before running.
_APPROVAL_REQUIRED = {
    AgentOperation.WRITE,
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
    AgentOperation.DELETE: "High",
    AgentOperation.MOVE: "Medium",
    AgentOperation.TERMINAL: "Critical",
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

    def as_dict(self) -> dict[str, Any]:
        return {
            "configured": self.configured,
            "path": self.path,
            "exists": self.exists,
            "writable": self.writable,
            "file_count": self.file_count,
            "session_grants": self.session_grants,
            "terminal_enabled": self.terminal_enabled,
        }


class AgentService:
    """Workspace-scoped, permission-gated Agent runtime."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._workspace: Path | None = None
        self._grants: set[str] = set()
        self._loaded = False

    # --- workspace --------------------------------------------------------
    @property
    def workspace(self) -> Path | None:
        return self._workspace

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
                record = await session.scalar(
                    select(AppSetting).where(AppSetting.key == WORKSPACE_SETTING_KEY)
                )
            if record and isinstance(record.value, dict):
                raw = record.value.get("path")
                if raw:
                    candidate = Path(str(raw)).expanduser()
                    if candidate.is_dir():
                        self._workspace = candidate.resolve()
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
        """Open the local OS folder chooser (best-effort).

        Runs Tk's ``askdirectory`` in a worker thread. Returns ``None`` when a
        GUI is unavailable (headless server or frozen build without Tk), so the
        UI can fall back to manual path entry rather than pretending to pick.
        """
        try:
            return await asyncio.to_thread(_tk_pick_folder)
        except Exception as exc:  # noqa: BLE001 - GUI is optional
            logger.info("native folder picker unavailable: %s", exc)
            return None

    async def clear_workspace(self) -> WorkspaceStatus:
        self._workspace = None
        self._grants.clear()
        await self._persist_workspace(None)
        return await self.status()

    async def _persist_workspace(self, path: Path | None) -> None:
        try:
            database = get_database()
            available, _ = await database.ping()
            if not available:
                return
            async with database.session() as session:
                record = await session.scalar(
                    select(AppSetting).where(AppSetting.key == WORKSPACE_SETTING_KEY)
                )
                value = {"path": str(path)} if path else {"path": None}
                if record is not None:
                    record.value = value
                else:
                    session.add(AppSetting(key=WORKSPACE_SETTING_KEY, value=value))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "could not persist agent workspace", extra={"intllm_extra": {"error": str(exc)}}
            )

    async def status(self) -> WorkspaceStatus:
        await self.ensure_loaded()
        path = self._workspace
        if path is None:
            return WorkspaceStatus(
                configured=False,
                terminal_enabled=self._settings.intllm_agent_terminal_enabled,
                session_grants=sorted(self._grants),
            )
        exists = path.is_dir()
        writable = exists and _is_writable(path)
        file_count = len(self._quick_listing(path)) if exists else None
        return WorkspaceStatus(
            configured=True,
            path=str(path),
            exists=exists,
            writable=writable,
            file_count=file_count,
            terminal_enabled=self._settings.intllm_agent_terminal_enabled,
            session_grants=sorted(self._grants),
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
        """Return (allowed, blocked_result). Read-only ops always run."""
        if operation not in _APPROVAL_REQUIRED:
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
        truncated = target.stat().st_size > max_bytes
        content = await asyncio.to_thread(_read_text, target, max_bytes)
        return AgentResult(
            operation=AgentOperation.READ.value,
            status="completed",
            output={
                "path": self._relative(target),
                "content": content,
                "truncated": truncated,
                "size": target.stat().st_size,
            },
            target=self._relative(target),
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
        try:
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            timed_out = True
            proc.kill()
            stdout_b, stderr_b = await proc.communicate()
        duration = round((time.perf_counter() - started) * 1000.0, 2)
        return AgentResult(
            operation=AgentOperation.TERMINAL.value,
            status="completed" if not timed_out else "failed",
            output={
                "command": command,
                "cwd": self._relative(workdir),
                "exitCode": proc.returncode,
                "stdout": stdout_b.decode("utf-8", errors="replace")[-20000:],
                "stderr": stderr_b.decode("utf-8", errors="replace")[-20000:],
                "timedOut": timed_out,
                "timeoutSeconds": timeout,
                "outsideWorkspaceHint": _mentions_outside_paths(command, workspace),
            },
            error="Command timed out" if timed_out else None,
            target=command.strip(),
            risk=_OPERATION_RISK[AgentOperation.TERMINAL],
            permission="requires-approval",
            duration_ms=duration,
        )


# --- blocking helpers ----------------------------------------------------------


def _tk_pick_folder() -> str | None:
    import tkinter  # noqa: PLC0415 - optional GUI dependency
    from tkinter import filedialog

    root = tkinter.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askdirectory(title="Select INTLLM Agent workspace")
    finally:
        root.destroy()
    return selected or None


def _read_text(path: Path, max_bytes: int) -> str:
    with path.open("rb") as handle:
        data = handle.read(max_bytes)
    return data.decode("utf-8", errors="replace")


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
