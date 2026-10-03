# INTLLM Agent Mode

Agent Mode turns the INTLLM chat workspace into a coding and computer-use
assistant that performs **real** actions inside a single, user-selected
workspace directory.

The Agent is not a single completion. It runs a bounded loop in which the local
model proposes tool calls; INTLLM validates each call against the workspace,
applies the Allow / Ask Me permission gate, performs the real filesystem or
terminal operation, and feeds the structured result back to the model until it
produces a final answer.

---

## Workspace selection

- Switch the composer to **Agent** mode; a **Workspace** selector appears above
  the input.
- Use the selector to pick a folder through the **native folder chooser**
  (Windows shell dialog, macOS `choose folder`, Linux zenity/kdialog, Tk
  fallback). You can also enter a path manually.
- The selected folder is the Agent's **filesystem boundary** and is stored by
  the backend (`app_settings`), not just in the browser.
- Changing the workspace **clears all session permission grants** so old
  approvals never carry over.

## File access (read-only, no approval)

| Operation | Tool | Description |
| --- | --- | --- |
| List | `fs.list` | List files and folders inside the workspace |
| Read | `fs.read` | Read a UTF-8 text file (size-limited; binary files return metadata only) |
| Search | `fs.search` | Search file contents for a string (results limited) |

## File creation

| Operation | Tool | Description |
| --- | --- | --- |
| Create / overwrite file | `fs.write` | Create a file or overwrite an existing one |
| Create folder | `fs.mkdir` | Create a directory |

Creating is a workspace-changing action: in **Ask Me** mode it requires approval.

## File editing

| Operation | Tool | Description |
| --- | --- | --- |
| Edit | `fs.edit` | Replace an exact piece of text in an existing file (`find`/`replace`) |

Edits fail safely when the target text is absent — there is no silent partial
write — and the written content is size-checked.

## File deletion

| Operation | Tool | Description |
| --- | --- | --- |
| Delete | `fs.delete` | Delete a file or folder inside the workspace |

The workspace root itself can never be deleted.

## Folder operations

| Operation | Tool | Description |
| --- | --- | --- |
| Move / rename | `fs.move` | Move or rename a path inside the workspace |

## Terminal

| Operation | Tool | Description |
| --- | --- | --- |
| Run command | `terminal` | Run a shell command with the workspace as the working directory |

- Commands run with the workspace as `cwd` and a configurable timeout
  (`INTLLM_AGENT_TERMINAL_TIMEOUT_SECONDS`, default 60s).
- Output is captured (truncated) and the real exit code is shown.
- Commands that reference paths outside the workspace are flagged to the user.
- Terminal execution can be disabled entirely with
  `INTLLM_AGENT_TERMINAL_ENABLED=false`.

## Allow mode

In **Allow** mode, actions that change the workspace run automatically (the
workspace sandbox still applies). Use it when you trust the task and want the
Agent to work without prompts.

## Ask Me mode (default)

In **Ask Me** mode, every action that changes the workspace — create, write,
edit, delete, move and terminal — pauses the Agent loop and raises an
**Allow / Deny** request in the UI, showing the tool, target, command and risk
level.

- A decision of **Allow** runs the action once; **Allow for session** suppresses
  repeat prompts for that operation.
- A **Deny** returns a denial to the model so it can reason about it.
- A timeout (5 minutes) or a cancelled stream resolves the request as **deny** —
  it is never silently allowed.

## Workspace security boundary

- Every path is resolved against the workspace root; a path that resolves
  outside it (including via `..` or absolute paths) is rejected.
- Enabling Agent mode never exposes the whole filesystem.
- Read/write sizes are limited (`INTLLM_AGENT_MAX_READ_BYTES`,
  `INTLLM_AGENT_MAX_WRITE_BYTES`).

## Agent limitations

- **Not a kernel sandbox.** Terminal commands run with the user's own
  privileges. The permission gate and workspace working directory are
  guardrails, not OS-level isolation. Approve commands deliberately.
- The model must be installed in Ollama; if the selected model is unavailable
  the Agent reports it rather than proceeding.
- The loop is bounded (`DEFAULT_MAX_STEPS = 12`); when it hits the limit it says
  so and asks you to continue.
- Repeated identical tool calls stop the loop to avoid spinning.
- The Agent cannot reach outside the workspace, so tasks that genuinely require
  other paths must be done by changing the workspace.

See [SECURITY.md](SECURITY.md) §11–14 for the security model.
