# Packaging Strategy

## Developer mode

```text
git clone
uv sync
npm install
npm run dev
```

## User mode

Target:

```text
intllm
```

Expected behavior:

1. dependency check
2. local services check
3. start required services
4. start FastAPI
5. serve built React app
6. open browser
7. show ready state

## Windows

Plan for:

- CLI launcher
- installer EXE
- optional portable package
- uninstaller
- Start Menu shortcut
- desktop shortcut optional
- versioned release artifacts
- SHA256 checksums

## Linux

Later:

- install script
- CLI entrypoint
- desktop integration where practical

## PostgreSQL

Do not assume end users have PostgreSQL installed. Provide a guided local setup/managed service strategy after operational testing.

## Ollama

Detect existing installation. If missing, offer guided installation instead of silently downloading software.
