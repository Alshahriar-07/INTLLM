# Agent Mode & Workspace

**Status: Implemented (v1.0.2 Stage 1).**

## Purpose

Agent mode turns the Chat workspace into a coding assistant that can act on a
single user-selected **workspace** folder: reading and searching source, creating
and editing files, deleting, renaming/moving, and running project commands.

## Boundary and safety

* The Agent is **sandboxed to the selected workspace**. Every path supplied to
  the Agent service is resolved and rejected when it escapes the workspace
  (`PermissionDeniedError`). Deletes of the workspace root are refused.
* Enabling Agent mode never exposes the whole filesystem.
* Destructive or arbitrary-execution operations require an explicit approval
  decision:

  | Operation | Permission | Risk |
  | --- | --- | --- |
  | `fs.list` / `fs.read` / `fs.search` | read-only | Low |
  | `fs.create` (new file or directory) | allowed | Low |
  | `fs.write` (overwrite existing) | requires-approval | High |
  | `fs.delete` | requires-approval | High |
  | `fs.move` | requires-approval | Medium |
  | `terminal.execute` | requires-approval | Critical |

* A decision of `allow_session` grants the operation for the session so harmless
  repeated work does not re-prompt. Starting a new workspace clears all session
  grants.
* Terminal commands run through a dedicated service with the workspace as the
  working directory and a configurable timeout. Commands that reference paths
  outside the workspace are flagged (`outsideWorkspaceHint`) in the result.

## Backend

* `backend/app/services/agent/service.py` — `AgentService`, the single place that
  performs filesystem/terminal work.
* `backend/app/api/routes/agent.py` — HTTP surface under `/api/agent`.
* Workspace persistence uses `app_settings` (`agent.workspace`); the running
  process keeps an in-memory copy so Agent mode still works when PostgreSQL is
  briefly unavailable. The frontend never owns the workspace state.

### Endpoints

```text
GET    /api/agent/status
POST   /api/agent/workspace            { path }
POST   /api/agent/workspace/pick       # native folder chooser (best-effort)
DELETE /api/agent/workspace
GET    /api/agent/fs/list?path=
GET    /api/agent/fs/read?path=
GET    /api/agent/fs/search?query=&path=
POST   /api/agent/fs/write             { path, content, decision? }
POST   /api/agent/fs/mkdir             { path, decision? }
POST   /api/agent/fs/delete            { path, decision? }
POST   /api/agent/fs/move              { source, destination, decision? }
POST   /api/agent/terminal             { command, cwd?, decision? }
GET    /api/agent/permissions
POST   /api/agent/permissions          { operation, decision }
```

## Frontend

* The Chat workspace owns the mode (`chat` | `agent`) and the workspace state,
  loaded from `/api/agent/status` and echoed to the backend on every Agent chat
  request.
* `ChatComposer` renders the Chat/Agent control and, in Agent mode, the
  workspace row (`Select Folder` / `Change` / `Clear`, plus a real status badge).
* When the native folder chooser is unavailable the UI falls back to a modal
  where the absolute path can be entered and validated by the backend.

## Configuration

```text
INTLLM_AGENT_TERMINAL_ENABLED=true
INTLLM_AGENT_TERMINAL_TIMEOUT_SECONDS=60
INTLLM_AGENT_MAX_READ_BYTES=200000
INTLLM_AGENT_MAX_WRITE_BYTES=2000000
INTLLM_AGENT_MAX_SEARCH_RESULTS=200
```

## Not yet implemented (Stage 2 / later)

* Autonomous model-driven tool-calling loop (the runtime and its permission gate
  exist; wiring the model's tool *decisions* through them is future work).
* Per-path persistent grants and multi-folder workspaces.
