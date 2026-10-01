# Acceptance Criteria

## Core

- `intllm` starts successfully on a clean supported machine.
- Local portal opens automatically.
- Ollama is detected/started or guided through installation.
- A compatible model can be installed and used.
- Chat streams without full-page UI flicker.
- PostgreSQL stores conversations and memory.

## Brain

- L0 lookup is faster than a full semantic memory scan.
- Stale memory can trigger live retrieval.
- Validated knowledge can be stored compactly.
- Background learning yields to user requests.

## API

- `/v1/models` works.
- `/v1/chat/completions` works.
- streaming works where supported.
- API keys can be created/revoked.

## Security

- default binding is localhost.
- risky tools require policy/confirmation.
- raw API keys are not stored.
- webpage instructions cannot directly bypass tool policy.

## Packaging

- installer works on clean Windows environment.
- artifacts have matching version.
- checksum verification passes.
