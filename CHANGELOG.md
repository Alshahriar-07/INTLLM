# Changelog

All notable changes to INTLLM are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to semantic versioning. The authoritative version lives in
`backend/app/__init__.py`.

## [1.0.2] — 2026-10-02

Agent mode, parameter-based model classification, PostgreSQL readiness clarity,
a production release pipeline and a license change.

### Added
- **Agent Mode** in Chat with a Chat/Agent mode control and a **workspace**
  selector above the composer. The selected folder is the Agent's filesystem
  boundary and is stored by the backend (`app_settings`), never frontend-only.
- **Agent runtime** (`backend/app/services/agent`): sandboxed directory listing,
  file read/search, file/dir creation, writes, deletes, moves and terminal
  execution — each path resolved against the workspace and rejected when it
  escapes it. Destructive/terminal operations require an explicit approval
  decision with optional per-session grants; `allow_session` suppresses repeat
  prompts for harmless repeated work. The workspace root cannot be deleted.
- **Agent API** under `/api/agent` (status, workspace get/set/pick/clear,
  `fs/*`, `terminal`, `permissions`).
- **Hardware-based recommendations** using real `psutil`/`nvidia-smi` data
  (CPU, RAM, GPU/VRAM, disk, OS); undetectable values render as `N/A`.
- **Dedicated PyPI publishing workflow** (`.github/workflows/pypi.yml`) using
  PyPI Trusted Publishing (OIDC) — build, test, `twine check`, distribution
  content validation and a wheel install check before publishing.
- `intllm` command shim (`IRM_INSTALL/intllm.cmd`) installed with the Windows
  package so a new terminal can run `intllm`, `intllm --version` and
  `intllm --help`.
- Desktop shortcut created by default by the Inno Setup installer; Start Menu
  shortcut retained.
- `RELEASE_INFO.md` with the production artifact, testing and license summary.
- Agent runtime tests (`test_agent.py`) and model-classification tests
  (`test_model_tiers.py`).

### Fixed
- **PostgreSQL availability handling** — startup now initializes the schema
  (Alembic or metadata DDL) and reports `connected` / `degraded` / `unavailable`
  / `offline` instead of a bare online/offline flag.
- **OpenAI-compatible API and API-key creation** — the `/v1` surface and key
  management were correct but appeared broken when PostgreSQL was down; the
  dependency is now surfaced clearly (`503`/`degraded`) rather than as a silent
  failure. PostgreSQL remains the primary database (no SQLite fallback).
- **Chat history** — server-side conversation/message persistence verified and
  retained; history is restored on reload/reconnect.
- **Installation behaviour** — desktop/Start Menu shortcuts, `intllm` shim,
  correct shortcut targets and per-user PATH handling in both installers.

### Changed
- **Model classification is now parameter-count based everywhere**: `< 3B` →
  **Potato**, `3B to < 8B` → **Medium**, `>= 8B` → **High** (backend registry,
  recommendations, model list and the Models UI). The previous VRAM-based tiers
  (`POTATO` / `NEUTRAL` / `I PAID FOR MY WHOLE PC`) are removed.
- **Windows executable renamed** from `INTLLM-windows-x64.exe` to
  `INTLLM.exe`; the release stages it alongside `INTLLM-Setup.exe`.
- **Installation experience** — both `install.ps1` and `install.sh` were
  rewritten with platform/architecture detection, real download/verify steps,
  clear status output, and robust error handling.
- **Licensing** — the project is now released under the **PolyForm
  Noncommercial License 1.0.0** (previously MIT). Copyright © 2026 Al Shahriar
  Sowan.
- Version bumped to **1.0.2** across the Python package, frontend, CLI,
  installers and documentation.

### Documentation
- Rewrote `README.md` for the 1.0.2 release; added `RELEASE_INFO.md`,
  `INTLLM-PLAN/07-tools-browser/AGENT_WORKSPACE.md` and
  `INTLLM-PLAN/13-packaging/PYPI_PUBLISHING.md`; updated model-tier, licensing
  and version references.

## [0.4.2] — 2026-10-01

Production packaging, local API hardening, documentation and release
engineering.

### Added
- **Local OpenAI-compatible API** at `/v1`: `GET /v1/models`,
  `GET /v1/models/{model}` and `POST /v1/chat/completions` (streaming SSE and
  non-streaming), routed through the INTLLM orchestrator.
- **API contract tests** covering model listing, chat (streaming and
  non-streaming), missing/invalid/revoked keys, database-unavailable and
  Ollama-unavailable responses, and malformed bodies.
- **PostgreSQL integration tests** (opt-in via `INTLLM_TEST_DATABASE_URL`)
  covering fresh schema creation, Alembic migrations, conversation/API-key/
  memory persistence and restart recovery.
- **`intllm` CLI** (`backend/app/cli.py`) with `--version`, `--help`, `start`,
  `serve` and `doctor`.
- **In-app Docs page** documenting only implemented endpoints.
- **CI/CD workflows**: `.github/workflows/ci.yml` (backend tests + lint,
  frontend typecheck + build, packaging validation) and
  `.github/workflows/release.yml` (test gate, wheel/sdist, Windows exe +
  installer, checksum generation, artifact validation, GitHub release).
- **Install scripts**: `IRM_INSTALL/install.ps1`, `IRM_INSTALL/install.sh`,
  served verbatim from the site as `/install.ps1` and `/install.sh`.
- **Inno Setup definition** (`IRM_INSTALL/INTLLM-Setup.iss`) for
  `INTLLM-Setup.exe`.
- **Release tooling**: `scripts/build_release.py`, `scripts/make_sha256.py`,
  `scripts/validate_release.py`, `scripts/sync-installers.mjs`.
- **Windows executable** `--version` / `--help` support.

### Changed
- Inno Setup definition hardened: the installer places program files in
  `%LOCALAPPDATA%\Programs\INTLLM` while INTLLM runtime data stays in
  `%LOCALAPPDATA%\INTLLM` (preserved on upgrade/uninstall); canonical per-user
  PATH append with `ChangesEnvironment`; Start Menu/desktop icons from
  `assets/ico/INTLLM.ico`.
- `scripts/build_release.py` now auto-detects Inno Setup's `iscc` in its
  standard install locations, not only on `PATH`, and builds
  `INTLLM-Setup.exe` alongside the portable executable.
- Distribution renamed to `intllm`; version is single-sourced from
  `app.__version__` via `[tool.setuptools.dynamic]`.
- Windows executable renamed to `INTLLM-windows-x64.exe` for predictable
  release naming.
- Launcher health timeout raised to 10 s: `/api/health` can take several
  seconds when Ollama is unreachable, which previously prevented the UI from
  auto-opening.
- README rewritten for production, and `RELEASE.md` added.

### Fixed
- Repaired a corrupted SSE generator in `backend/app/api/routes/openai.py`
  (literal newlines inside f-strings caused an unimportable module).
- Removed dead code in the Ollama status service (`models` list was built but
  never used).
- Build smoke test now accepts the honest `503 degraded` health response
  instead of treating it as a failure.

### Security
- API keys remain salted **scrypt** hashes; only a fingerprint is stored for
  lookup.
- Startup-only bootstrap access is loopback-restricted and ends once a key
  exists.
- Secrets are redacted from logs and are never written to frontend bundles,
  Git or release artifacts.

### Packaging
- `dist/` is reserved for the Vite frontend build (which also carries the
  served installer scripts); release artifacts are staged in `build/release/`.
- `.gitignore` updated for Python/Node artifacts; previously tracked `.pyc`
  files removed and the plan directory no longer ignored.

### Documentation
- At 0.4.2 the project was licensed under the MIT License (`LICENSE`); it was relicensed to the **PolyForm Noncommercial License 1.0.0** in 1.0.2.
- README, RELEASE.md, the in-app Docs page and this changelog describe only
  implemented functionality. No embedding, responses, audio or image endpoints
  are claimed, and no third-party CLI compatibility is claimed without a
  verified test.
