# INTLLM Release Notes

## Version 0.4.2

- **Version:** 0.4.2 (single source of truth: `backend/app/__init__.py`)
- **Release date:** 2026-10-01
- **Commit range:** production backend, local API, database, documentation,
  installers and release engineering.

---

## Highlights

- A production-ready, local-first runtime with an **OpenAI-compatible API** at
  `/v1`, an **INTLLM-owned API key system**, and an in-app **Docs** page.
- One-command builds that produce a Python wheel, source archive, a Windows x64
  executable and a SHA256 manifest, driven by tested CI/CD workflows.
- Installers for Windows (`install.ps1`) and Linux/macOS (`install.sh`) that
  download, verify and install the correct release artifact.

## Backend changes

- CLI added (`app.cli`) with `--version`, `--help`, `start`, `serve`, `doctor`.
- Windows launcher gained `--version` / `--help` and a raised health timeout
  (10 s) so the web UI opens even when Ollama is unreachable and `/api/health`
  is slow.
- Repaired a corrupted SSE generator in `app/api/routes/openai.py`.
- Removed dead code in the Ollama status service.

## API changes

- Implemented endpoints (documented and test-covered):
  - `GET  /v1/models`
  - `GET  /v1/models/{model}`
  - `POST /v1/chat/completions` — `stream: false` and `stream: true` (SSE)
- Authentication via `Authorization: Bearer <key>` or `x-api-key`.
- Extra request fields `intllm_use_brain` / `intllm_use_web` control memory and
  live retrieval for a single request.
- **Not implemented** and deliberately undocumented: `/v1/embeddings`,
  `/v1/responses`, audio, images, files, batches, fine-tuning.

## Database changes

- Schema managed by Alembic (`backend/migrations`, current revision `0001`) with
  a SQLAlchemy metadata fallback for the frozen executable.
- Startup verifies PostgreSQL reachability, the `pgvector` extension and schema
  state; failures are reported as `unavailable` / `misconfigured` with an
  actionable step.
- New opt-in integration tests exercise migrations, persistence and restart
  recovery against a real database.

## Frontend compatibility

- New **Docs** page and a consolidated **API** settings section.
- Existing services, tabs and design tokens are unchanged; `NavigationTab`
  gained a `docs` member.
- The frontend never receives or renders stored secrets (only a masked
  fingerprint after creation).

## Installer changes

- `IRM_INSTALL/install.ps1`: architecture check (x64), latest/pinned version
  resolution, SHA256 verification, per-user install, PATH update, Start Menu
  shortcut, `--version` verification.
- `IRM_INSTALL/install.sh`: POSIX shell, Python 3.11+ check, SHA256
  verification, isolated venv install, `intllm` wrapper, verification.
- Both are copied verbatim to `public/` (and served as `/install.ps1`,
  `/install.sh`); `IRM_INSTALL/` remains the single source.
- `IRM_INSTALL/INTLLM-Setup.iss` defines the per-user Inno Setup installer.

## Packaging

Artifacts are staged in `build/release/`:

```text
build/release/
├── INTLLM-windows-x64.exe
├── INTLLM-Setup.exe                 # when Inno Setup is available
├── intllm-0.4.2-py3-none-any.whl
├── intllm-0.4.2.tar.gz
└── SHA256.txt
```

> `dist/` is reserved for the Vite frontend build (which also carries the
> served installer scripts), so it is not the release staging directory.

The Windows executable is a PyInstaller onefile build bundling the backend and
the built frontend. Compute the wheel/sdist checksums with
`python scripts/make_sha256.py build/release`.

## Security changes

- API keys: salted scrypt hash + short fingerprint only; full key shown once.
- Loopback bootstrap access ends as soon as a key exists.
- Secret redaction in logs; no secrets in bundles, Git or artifacts.
- Localhost binding by default; restricted CORS; request-size limits.
- Tool execution always passes through the permission gateway.

## Breaking changes

- The Python distribution is renamed from `intllm-backend` to **`intllm`**, and
  the CLI entry point is now `intllm` (previously `intllm` pointed directly at
  the launcher). Console script `intllm-api` is unchanged.
- The Windows executable is named `INTLLM-windows-x64.exe` (previously
  `INTLLM.exe`).
- `INTLLM_PORT` must be a valid TCP port (0–65535).

## Migration requirements

- No manual database steps: run INTLLM and the schema is applied automatically
  (Alembic where available, metadata DDL otherwise).
- Existing deployments using a `intllm-backend` install should install the
  `intllm` package instead; user data under the data directory is untouched.

## Known limitations

- **PostgreSQL and Ollama are not bundled or auto-installed.** They are external
  local dependencies that INTLLM detects and reports.
- **Embeddings / responses / audio / images / files are not implemented.**
- **No third-party CLI compatibility is claimed** unless verified against a
  build.
- Background learning performs low-priority memory/index maintenance; it does
  **not** continuously retrain Ollama model weights.
- `INTLLM-Setup.exe` is produced only where Inno Setup's compiler (`iscc`) is
  available; the release workflow installs it on the Windows runner. The
  Linux/macOS path installs the universal wheel.
- The generated `INTLLM-Setup.exe` was compiled and statically validated (PE
  header, Inno Setup payload, SHA256) but **not executed** in this environment,
  because a silent test install would modify the user `PATH` and per-user
  locations. Run it interactively, or `INTLLM-Setup.exe /VERYSILENT
  /SUPPRESSMSGBOXES /NORESTART`, to install.

## Verification results (this build)

| Check | Result |
| --- | --- |
| Backend unit tests (`pytest`) | **53 passed**, 6 skipped |
| Database integration tests | **skipped locally** (no `INTLLM_TEST_DATABASE_URL`); run in CI with a pgvector PostgreSQL service |
| Backend lint (`ruff`, E/F/I) | **passed** |
| Frontend typecheck (`tsc --noEmit`) | **passed** |
| Frontend production build (`vite build`) | **passed** |
| Wheel build (`intllm-0.4.2-py3-none-any.whl`) | **built** |
| Source archive (`intllm-0.4.2.tar.gz`) | **built** |
| Wheel install + `intllm --version` / `--help` | **passed** (`validate_release.py --install-check`) |
| Windows x64 executable | **built** — 33.9 MB, PE machine `x64 (AMD64)` |
| Executable smoke test | **passed** — `/api/health` OK, SPA fallback OK |
| `INTLLM-Setup.exe` | **built** with Inno Setup 6 (valid PE bootstrapper, x64-gated, 35 MB); compiled and statically checked — see note below |
| SHA256 manifest | **generated** and verified for the staged artifacts |
| PostgreSQL / Ollama live integration | **not available in this environment**; reported honestly at runtime |

## SHA256 verification

After downloading artifacts, verify against the release `SHA256.txt`:

```bash
# Linux/macOS
sha256sum -c SHA256.txt

# Windows PowerShell
Get-FileHash .\INTLLM-windows-x64.exe -Algorithm SHA256
```

The checksums are generated by `scripts/make_sha256.py` and re-verified by the
release workflow (`scripts/validate_release.py`) before publishing. Hashes are
never typed by hand.

## Artifact list

```text
INTLLM-windows-x64.exe
INTLLM-Setup.exe
intllm-0.4.2-py3-none-any.whl
intllm-0.4.2.tar.gz
SHA256.txt
```
