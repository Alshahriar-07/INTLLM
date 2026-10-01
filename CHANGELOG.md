# Changelog

All notable changes to INTLLM are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to semantic versioning. The authoritative version lives in
`backend/app/__init__.py`.

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
- Project is licensed under the **MIT License** (`LICENSE`).
- README, RELEASE.md, the in-app Docs page and this changelog describe only
  implemented functionality. No embedding, responses, audio or image endpoints
  are claimed, and no third-party CLI compatibility is claimed without a
  verified test.
