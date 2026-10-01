# Recommended Repository Structure

```text
intllm/
├─ assets/
├─ apps/
│  ├─ web/
│  └─ api/
├─ intllm/
│  ├─ __init__.py
│  ├─ main.py
│  ├─ config/
│  ├─ api/
│  ├─ core/
│  ├─ runtime/
│  ├─ orchestrator/
│  ├─ brain/
│  │  ├─ flash/
│  │  ├─ hot_cache/
│  │  └─ secondary/
│  ├─ retrieval/
│  ├─ browser/
│  ├─ tools/
│  ├─ models/
│  ├─ system/
│  ├─ security/
│  ├─ background/
│  ├─ database/
│  └─ observability/
├─ migrations/
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  ├─ e2e/
│  └─ performance/
├─ scripts/
├─ packaging/
├─ docs/
├─ pyproject.toml
├─ package.json
├─ docker-compose.dev.yml
├─ README.md
└─ LICENSE
```

Keep business logic out of route handlers. Use service/repository boundaries.
