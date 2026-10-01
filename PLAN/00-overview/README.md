# INTLLM — Complete Project Plan

INTLLM is a local AI runtime that turns compatible local LLMs into a richer intelligence environment through live retrieval, browser/tools, layered memory, verification, and background knowledge maintenance.

## Core principle

INTLLM does not need to retrain the base Ollama model for every new fact. The model remains the reasoning engine while INTLLM supplies current context, tools, memory and orchestration around it.

## Primary stack

- Backend: Python 3.11+ / FastAPI
- Frontend: React + TypeScript + Vite
- Styling: Tailwind CSS + shadcn/ui
- Database: local PostgreSQL + pgvector
- LLM runtime: Ollama
- Realtime: SSE and WebSocket where appropriate
- Browser automation: Playwright
- Package management: uv/pip + npm/pnpm
- Testing: pytest + Playwright/Vitest
- Packaging: Windows-first, then Linux
- API: OpenAI-compatible local API

## Golden rule

User response always has priority. Background learning is a low-priority task and must yield resources whenever interactive work needs them.

## Project outcomes

1. Zero/low-configuration local AI onboarding.
2. Automatic Ollama detection/startup.
3. Hardware-aware model recommendations.
4. Direct local chat.
5. Flash Brain + Hot Cache + Secondary Brain.
6. Live web retrieval and verification.
7. Browser agent with permission controls.
8. Local OpenAI-compatible API with API keys.
9. Claude Code/Codex/SeedCode-compatible integration where protocol-compatible.
10. 24/7 low-priority background memory maintenance.
11. Fully local database and user data by default.
12. Production-quality web UI and installer.
