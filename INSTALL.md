# Installing INTLLM

INTLLM v1.1.0 ships as a Windows desktop application, a portable Windows
executable, a universal Python wheel, and a source distribution. Ollama and
PostgreSQL are **external local dependencies** that INTLLM detects and reports —
they are never bundled or silently installed.

---

## Requirements

| Component | Requirement |
| --- | --- |
| OS (desktop app) | Windows 10/11 x64 |
| WebView2 | Evergreen WebView2 Runtime (preinstalled on Windows 11 and most Windows 10 systems; otherwise install from Microsoft) |
| Ollama | Installed and running, with at least one model pulled |
| PostgreSQL | 14+ with the **pgvector** extension |
| Python (wheel path) | 3.11+ |

---

## Windows desktop installation

### Option A — the one-line installer

```powershell
irm https://intllm.vercel.app/install.ps1 | iex
```

The script:

1. detects the platform (requires Windows x64),
2. resolves the release (latest, or pin with `INTLLM_VERSION=v1.1.0`),
3. downloads `SHA256.txt` and verifies the artifact's SHA256 against it,
4. installs `INTLLM.exe` under `%LOCALAPPDATA%\Programs\INTLLM`,
5. adds that directory to your **user** `PATH` and installs an `intllm` shim,
6. creates Start Menu and desktop shortcuts, and
7. verifies the install with `INTLLM.exe --version`.

Environment overrides:

| Variable | Effect |
| --- | --- |
| `INTLLM_REPO` | GitHub repo (default `Alshahriar-07/INTLLM`) |
| `INTLLM_VERSION` | Pin a release tag (default `latest`) |
| `INTLLM_USE_SETUP` | Set to `1` to prefer `INTLLM-v1.1.0-Setup.exe` |
| `INTLLM_NO_PATH_EDIT` | Set to `1` to skip the PATH update |
| `INTLLM_NO_ANIMATION` | Set to `1` for plain output (CI) |

### Option B — run the installer directly

Download `INTLLM-v1.1.0-Setup.exe` from the release and run it. It performs a
per-user install (no admin prompt), creates Start Menu and desktop shortcuts,
and registers an uninstaller.

For a silent install:

```powershell
.\INTLLM-v1.1.0-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
```

### Option C — portable executable

Download `INTLLM-v1.1.0-win64x.exe` and run it directly. No installation
required. Configuration and data still go to `%LOCALAPPDATA%\INTLLM`.

### Where things live

| Path | Contents | Removed on uninstall? |
| --- | --- | --- |
| `%LOCALAPPDATA%\Programs\INTLLM` | Program files (`INTLLM.exe`, `intllm.cmd`) | Yes |
| `%LOCALAPPDATA%\INTLLM` | Data, workspace, logs | **No** (preserved) |
| PostgreSQL data directory | Conversations, memory, keys | No (managed by PostgreSQL) |

Upgrades and uninstall do **not** delete your runtime data. To remove it,
delete `%LOCALAPPDATA%\INTLLM` manually and drop the PostgreSQL database if you
no longer want it.

---

## Linux / macOS

```bash
curl -fsSL https://intllm.vercel.app/install.sh | bash
```

The script verifies Python 3.11+, downloads and SHA256-verifies the wheel,
installs it into an isolated virtual environment at `~/.intllm`, and exposes an
`intllm` command in `~/.local/bin`.

The **native desktop window** on Linux/macOS needs a webview backend:

```bash
~/.intllm/venv/bin/pip install "intllm[desktop]"
```

Without one, `intllm` serves the backend headlessly and prints the local URL.

---

## Python package (PyPI)

```bash
python -m pip install intllm
# optional desktop window:
python -m pip install "intllm[desktop]"
```

---

## From source (development)

```bash
git clone https://github.com/Alshahriar-07/INTLLM.git
cd INTLLM
npm install && npm run build
python -m pip install -e "./backend[dev]"
```

See [DEVELOPMENT.md](DEVELOPMENT.md).

---

## Ollama setup

1. Install Ollama from `https://ollama.com`.
2. Start it (`ollama serve`, or the desktop app — it runs a background service).
3. Pull at least one model, e.g. `ollama pull llama3.2`.

INTLLM detects Ollama at `INTLLM_OLLAMA_URL` (default
`http://127.0.0.1:11434`) and lists the **real** installed models. If Ollama is
not running, the startup window reports it as offline.

## PostgreSQL + pgvector setup

1. Install PostgreSQL 14 or newer.
2. Create a role and database, e.g.:

   ```sql
   CREATE ROLE intllm WITH LOGIN PASSWORD 'choose-a-strong-password';
   CREATE DATABASE intllm OWNER intllm;
   ```

3. Enable pgvector in that database:

   ```sql
   \c intllm
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

4. Point INTLLM at it (default matches the above):

   ```text
   INTLLM_DATABASE_URL=postgresql+asyncpg://intllm:your-password@127.0.0.1:5432/intllm
   ```

On first launch INTLLM verifies PostgreSQL, checks pgvector, and applies the
schema automatically (Alembic, or SQLAlchemy metadata DDL in the packaged
executable). If the configured database does not exist it may be created
(`INTLLM_DB_AUTO_CREATE=true`); it is never dropped.

---

## First launch

1. Launch **INTLLM** from the Start Menu, desktop shortcut, or by running the
   executable. The desktop window opens directly — **no browser is required**.
2. The startup window shows live readiness for **PostgreSQL**, **Ollama** and
   **INTLLM Backend**. If a dependency is missing it shows the reason and offers
   **Retry** or **Continue anyway** (degraded session).
3. Once ready, the INTLLM UI loads in the same window.

## Model installation

Open **Models** and either select an installed model or pull a new one (real
streaming progress). Set a default model if you like. Classification is by
parameter count: `< 3B` Potato, `3B–8B` Medium, `>= 8B` High.

## API setup

1. Open **Settings → API**.
2. Create an API key. The full key is shown **once** — copy it then.
3. Point an OpenAI-compatible client at `http://127.0.0.1:8000/v1` with that
   key. See [API.md](API.md).

## LAN API setup

1. In **Settings → API**, switch access mode to **LAN**.
2. Restart INTLLM (the bound interface changes on launch).
3. Use the LAN base URL shown in the UI, e.g. `http://192.168.1.20:8000/v1`,
   with a valid API key.
4. Only `/v1` is exposed to the LAN; management routes stay loopback-only. See
   [SECURITY.md](SECURITY.md) §10 before enabling this.

## Agent workspace selection

Switch the composer to **Agent**, then use the **Workspace** selector to pick a
folder (native folder picker). That folder becomes the Agent's filesystem
boundary. See [AGENT.md](AGENT.md).

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Startup shows PostgreSQL unavailable | Start the PostgreSQL service; confirm `INTLLM_DATABASE_URL`. |
| Startup shows pgvector missing | `CREATE EXTENSION vector;` in the INTLLM database. |
| Startup shows Ollama offline | Start Ollama and pull a model. |
| Desktop window is blank | Install the Evergreen WebView2 Runtime. |
| `intllm` not found | Open a new terminal (PATH changes need a fresh shell). |
| Port already in use | INTLLM tries the next 10 ports; or set `INTLLM_PORT`. |
| Installer is blocked by SmartScreen | The release is unsigned; choose "More info → Run anyway" only if you trust the source and the SHA256 matches. |

Verify a downloaded artifact:

```powershell
Get-FileHash .\INTLLM-v1.1.0-win64x.exe -Algorithm SHA256
```

```bash
sha256sum -c SHA256.txt
```
