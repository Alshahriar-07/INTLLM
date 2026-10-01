# Configuration and Environment

Suggested variables:

```text
INTLLM_ENV=production
INTLLM_HOST=127.0.0.1
INTLLM_PORT=8000
INTLLM_DATABASE_URL=postgresql://...
INTLLM_OLLAMA_URL=http://127.0.0.1:11434
INTLLM_LOG_LEVEL=INFO
INTLLM_DATA_DIR=...
INTLLM_WORKSPACE_DIR=...
INTLLM_MAX_BACKGROUND_WORKERS=1
INTLLM_BACKGROUND_CPU_LIMIT=...
```

Never commit secrets or real production database credentials.

Provide a generated local configuration wizard.
