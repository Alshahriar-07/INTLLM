# Python Backend Plan

## Framework

FastAPI with async-first services.

## Layers

```text
Routes
  -> Services
      -> Domain logic
          -> Repositories / adapters
              -> PostgreSQL / Ollama / browser / web
```

## Required services

- `ChatService`
- `InferenceService`
- `BrainService`
- `RetrievalService`
- `BrowserService`
- `ToolService`
- `ModelService`
- `ApiKeyService`
- `HardwareService`
- `BackgroundLearningService`
- `DiagnosticsService`

## Backend rules

- Never block the event loop with heavy synchronous work.
- Stream model output.
- Put long-running work into bounded workers.
- Use cancellation tokens for interactive tasks.
- Enforce timeouts for external network/tool calls.
- Keep provider-specific code behind adapters.
- Validate all tool arguments.
- Log structured events, never secrets.

## Configuration

Use environment variables plus a local config file.

Important settings:

- database URL
- Ollama base URL
- web retrieval settings
- browser settings
- memory limits
- worker limits
- API host/port
- logging level
- security policy
