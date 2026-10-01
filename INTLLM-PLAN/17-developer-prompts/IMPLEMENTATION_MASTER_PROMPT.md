# Master Implementation Prompt

You are implementing INTLLM, a local-first AI runtime.

Follow all documents in this plan as the source of truth.

## Non-negotiable architecture

- Python + FastAPI backend.
- React + TypeScript + Vite frontend.
- PostgreSQL + pgvector locally.
- Ollama as the initial local model backend.
- L0 Flash Brain -> L1 Hot Cache -> L2 Secondary Brain -> live retrieval when required.
- Browser/tools behind a policy-enforced Tool Gateway.
- OpenAI-compatible local API.
- Background learning is low priority and must yield to user requests.
- No silent cloud storage.
- No unrestricted model-controlled shell/browser access.

## Implementation order

1. Foundation/config/logging.
2. PostgreSQL/migrations.
3. Ollama adapter.
4. chat/orchestrator.
5. React UI.
6. L2 memory.
7. L0 Flash Brain.
8. retrieval.
9. tool gateway.
10. browser.
11. API keys/OpenAI compatibility.
12. background learning.
13. diagnostics.
14. packaging.
15. tests/release.

Do not invent architecture that conflicts with this plan. If a requirement is ambiguous, choose the smallest safe implementation and document the decision.
