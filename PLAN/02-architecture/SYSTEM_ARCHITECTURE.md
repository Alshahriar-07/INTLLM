# System Architecture

```text
                         INTLLM
                           |
              +------------+-------------+
              |                          |
          Web Portal                 Local API
       React/TypeScript          OpenAI-compatible
              |                          |
              +------------+-------------+
                           |
                      FastAPI Core
                           |
        +----------+-------+-------+----------+
        |          |               |          |
     Runtime     Brain          Tools      System
        |          |               |          |
     Ollama   L0/L1/L2         Web/Browser  Hardware
        |          |               |
        +----------+---------------+
                           |
                     PostgreSQL
                       + pgvector

Background Learner runs separately at low priority.
```

## Core modules

- `runtime`: model lifecycle and inference.
- `orchestrator`: query routing and execution planning.
- `brain`: L0/L1/L2 memory.
- `retrieval`: web search, page reading, source extraction.
- `browser`: Playwright-controlled browser.
- `tools`: controlled capability gateway.
- `api`: local OpenAI-compatible server.
- `models`: registry, compatibility and installation.
- `system`: hardware/dependency detection.
- `security`: authentication, permissions, secrets.
- `background`: maintenance and learning workers.
- `observability`: logs, metrics, diagnostics.

## Request lifecycle

```text
User query
  -> classify
  -> Flash Brain
  -> memory / live retrieval decision
  -> optional tools/browser
  -> context assembly
  -> Ollama
  -> response stream
  -> post-response memory candidate
  -> background persistence/verification
```

## Runtime isolation

The browser, shell and filesystem tools must not be direct model capabilities. They are INTLLM-managed tools with explicit policy checks.
