# INTLLM Security Model

INTLLM is a **local-first** AI runtime. Its security posture is built around the
assumption that everything runs on the user's own machine and that the only
network surface is an API the user explicitly enables.

This document describes what the implementation **actually** does. It does not
claim properties the code does not provide.

**Version:** 1.1.0 · **License:** PolyForm Noncommercial 1.0.0

---

## 1. Local-first architecture

- The backend, database, memory, model orchestration and UI all run on the
  user's machine.
- The FastAPI backend binds to the **loopback interface (`127.0.0.1`) by
  default**. It is not reachable from other machines unless the user turns on
  LAN access.
- There is no hidden cloud sync and no telemetry endpoint. INTLLM does not send
  conversations, memory, prompts or keys anywhere.
- The only outbound network requests INTLLM makes are:
  - to the **local Ollama daemon** (`INTLLM_OLLAMA_URL`, default loopback),
  - to the **configured web provider** (DuckDuckGo or a self-hosted SearXNG)
    when the user explicitly enables web retrieval for a request,
  - to a URL the user explicitly asks the browser tool to open.

## 2. Local PostgreSQL

- Conversations, messages, memory items, API keys, Agent workspace state,
  background jobs and audit events live in a local PostgreSQL database with the
  `pgvector` extension.
- The default connection string points at `127.0.0.1:5432`. Credentials come
  from `INTLLM_DATABASE_URL` and are **never** committed to source.
- On a fresh install INTLLM may run `CREATE DATABASE` for the configured
  database if it is missing (`INTLLM_DB_AUTO_CREATE=true`). It **never** runs
  `DROP`, and never resets user data.
- Database errors are classified and surfaced with actionable remediation.
  Connection strings are sanitized before they reach logs or the UI, so a DSN
  password cannot leak through an error message.

## 3. Local chat history

- Chat history is persisted server-side in PostgreSQL and restored on reload and
  after a restart. It does not leave the machine.
- History is only available while the database is reachable; when PostgreSQL is
  down, the UI reports history as unavailable rather than showing stale or
  fabricated data.

## 4. Local memory

- Layered memory (L0 Flash Brain / L1 Hot Cache / L2 Secondary Brain) is stored
  in the local PostgreSQL + pgvector database.
- Memory retrieval is reported honestly: if the vector store is not ready, the
  UI says memory is unavailable instead of silently degrading to keyword-only
  results.

## 5. Local API

- The OpenAI-compatible API is served by the same local FastAPI process at
  `/v1`.
- In the default `local` mode the process binds loopback only, so `/v1` is
  reachable only from the same machine.
- The API routes through the INTLLM orchestrator (memory/security aware); it
  does not bypass the runtime.

## 6. API key handling

- Keys are generated locally with a cryptographically secure RNG and carry an
  `intllm_` prefix.
- Only a **salted scrypt hash** and a short **fingerprint** (for lookup) are
  stored. The raw key is shown **once** at creation and is never retrievable
  afterwards.
- Verification is constant-time.
- Keys are labelled, revocable, individually regenerable, and track last-used
  time.
- Secrets are redacted from logs by a logging filter and never included in
  frontend bundles, Git history or release artifacts.

## 7. API authentication

- `/v1` requires `Authorization: Bearer <key>` or `x-api-key: <key>`.
- Missing credentials return `401 authentication_error`; invalid or revoked keys
  return `401`.
- **Bootstrap exception:** while *no key exists yet*, loopback requests to `/v1`
  are allowed so the first key can be created in the UI. This exception ends as
  soon as a key exists, and it never applies to non-loopback clients.

## 8. LAN API behavior

- LAN access is an explicit opt-in (`INTLLM_API_ACCESS_MODE=lan`, or the toggle
  in Settings → API). It persists in the database and applies on the next
  launch.
- When enabled, the process binds the LAN interface and **only the public `/v1`
  API** becomes reachable from other machines. It still requires an API key.
- All internal routes (`/api/*`), the SPA, `/docs`, `/redoc` and diagnostics
  remain **loopback-only**, enforced by middleware.
- When LAN access is disabled, every non-loopback request is rejected with
  `403`.

## 9. LAN access default OFF

`INTLLM_API_ACCESS_MODE` defaults to `local`. A fresh install exposes nothing to
the network until the user deliberately enables LAN access.

## 10. LAN security considerations

Enabling LAN access means other devices on the same network can reach `/v1`.
Users should understand:

- The API is only as safe as the API key. Anyone who obtains a key can use your
  local models and (within the orchestrator's policies) memory-backed chat.
- INTLLM does **not** terminate TLS. On a LAN, `http://` traffic is unencrypted;
  use it only on a trusted network, or put a TLS-terminating reverse proxy in
  front of it.
- There is no built-in rate limiting or per-IP allowlist beyond key auth and the
  loopback restriction on management routes.
- Disable LAN access when you do not need it. Revoke keys you no longer use.

## 11. Agent workspace boundaries

- The Agent operates inside a single user-selected **workspace** directory.
- Every filesystem path is resolved against the workspace. A path that resolves
  outside the workspace (including via `..` or absolute paths) is rejected.
- Enabling Agent mode never exposes the whole filesystem.
- The workspace root itself can never be deleted.
- Changing the workspace clears all session permission grants.

## 12. File operation security

- Read, list and search run without approval.
- Operations that **change** the workspace — create, write, edit, delete, move
  and terminal execution — are permission-gated.
- Writes are size-limited (`INTLLM_AGENT_MAX_WRITE_BYTES`), reads are
  size-limited (`INTLLM_AGENT_MAX_READ_BYTES`), and binary files are returned as
  metadata only (never raw bytes).
- File edits fail safely when the target text is absent (no silent partial
  writes).

## 13. Terminal execution security

- Terminal execution is permission-gated like other workspace-changing actions.
- Commands run with the workspace as the working directory and a configurable
  timeout (`INTLLM_AGENT_TERMINAL_TIMEOUT_SECONDS`, default 60s); output is
  truncated.
- Commands that reference paths outside the workspace are flagged to the user.
- Terminal execution can be disabled entirely
  (`INTLLM_AGENT_TERMINAL_ENABLED=false`).
- **Honest limitation:** terminal execution is a shell command run with the
  user's own privileges. The permission gate and the workspace working directory
  are guardrails, not a kernel-level sandbox. Approve commands deliberately.

## 14. Allow / Ask Me permission system

- **Ask Me (default)** — every workspace-changing action pauses the Agent loop
  and raises an Allow/Deny request. A timeout (5 minutes) or a cancelled stream
  resolves the request as **deny**; it is never silently allowed.
- **Allow** — workspace-changing actions run automatically; the workspace sandbox
  still applies.
- A decision is delivered out-of-band over a separate HTTP request while the chat
  stream stays open. Pending requests live only in memory and are cleared when
  the stream ends.

## 15. Sensitive data handling

- API keys: salted scrypt hash + fingerprint only.
- Database DSNs: read from the environment; passwords are sanitized out of any
  error text before it is logged or returned.
- Logs: a redaction filter strips API keys and bearer tokens.
- Frontend: the UI receives only a masked key fingerprint after creation, never a
  stored secret.

## 16. Logging behavior

- Structured JSON logs with a redaction filter.
- The packaged desktop app writes rotating logs to
  `%LOCALAPPDATA%\INTLLM\logs\intllm.log` (2 MB × 5 files).
- Request access logs, health probes and dependency errors are recorded; secrets
  are not.

## 17. Network behavior

- Inbound: loopback only by default; `/v1` only when LAN is enabled.
- Outbound: local Ollama, the configured web provider (opt-in per request), and
  explicitly requested browser URLs.
- SSRF guards (`guard_url`) reject non-`http(s)` schemes and private, loopback,
  link-local and reserved addresses for web/browser tools.
- CORS is restricted to explicitly configured local origins — there is no
  wildcard fallback.
- Request bodies are size-limited (`INTLLM_MAX_REQUEST_BYTES`, default 10 MiB).

## 18. Ollama integration

- INTLLM talks to Ollama over its local HTTP API
  (`INTLLM_OLLAMA_URL`, default `http://127.0.0.1:11434`).
- Ollama start/stop/restart operations verify the real daemon state before
  reporting success; INTLLM does not blindly spawn processes.
- INTLLM never bundles, downloads or silently installs Ollama. When it is
  missing or unavailable, that is reported honestly.

## 19. Data storage

| Data | Location | Notes |
| --- | --- | --- |
| Conversations, messages | PostgreSQL | Local database |
| Memory items, embeddings | PostgreSQL + pgvector | Local database |
| API keys | PostgreSQL | Salted scrypt hash + fingerprint |
| Agent workspace setting | PostgreSQL (`app_settings`) | Path only |
| Application data / workspace / logs | `%LOCALAPPDATA%\INTLLM` (Windows) | Separate from program files |
| Program files | `%LOCALAPPDATA%\Programs\INTLLM` (Windows) | Removed on uninstall |

Runtime data under `%LOCALAPPDATA%\INTLLM` is **preserved** across upgrades and
uninstall; only the program directory is removed.

## 20. Threat model

**In scope / defended:**

- Another machine on the LAN reaching management endpoints → loopback-only
  middleware.
- Unauthenticated use of `/v1` → API key required (except the first-key
  bootstrap, loopback-only).
- Path traversal out of the Agent workspace → path resolution against the
  workspace root.
- Unapproved destructive Agent actions → Ask Me gate; timeout = deny.
- Credential leakage through logs → redaction filter and DSN sanitization.
- Oversized request bodies → size limit.
- SSRF via web/browser tools → URL guard.
- Prompt injection via retrieved web content → retrieved text is treated as
  data, not instructions.

**Out of scope / not defended:**

- An attacker who already has local code execution as the user (they can read
  the database and the logs directly).
- A compromised local machine, OS, PostgreSQL server or Ollama installation.
- Malware with access to the user's browser profile or file system.
- Unencrypted LAN traffic (INTLLM does not terminate TLS).
- A malicious model or model file.
- Denial of service by a local process.

## 21. Reporting a security issue

Please report suspected vulnerabilities privately rather than opening a public
issue:

- Open a private security advisory on GitHub:
  `https://github.com/Alshahriar-07/INTLLM/security/advisories/new`
- Or email the maintainer listed in `pyproject.toml`.

Include a description, reproduction steps, the INTLLM version
(`intllm --version`) and the affected component. Please allow reasonable time
for a fix before public disclosure.
