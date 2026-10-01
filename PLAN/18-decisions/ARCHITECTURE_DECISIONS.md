# Architecture Decisions

## ADR-001 — Local-first

Persistent user data is local by default.

## ADR-002 — PostgreSQL

Use PostgreSQL instead of SQLite because INTLLM expects structured data, concurrency, and vector search.

## ADR-003 — pgvector

Use pgvector for semantic memory retrieval.

## ADR-004 — FastAPI

Use FastAPI for Python API/runtime orchestration.

## ADR-005 — React

Use React + TypeScript for the rich local web portal.

## ADR-006 — Ollama first

Ollama is the first model runtime. Adapter boundaries keep future backends possible.

## ADR-007 — Memory instead of constant weight training

The first system improves usefulness through retrieval, memory and tools instead of continuous base-model retraining.

## ADR-008 — User-first scheduling

Interactive requests preempt/throttle background learning.

## ADR-009 — Tool gateway

The model never directly owns OS/browser privileges.

## ADR-010 — OpenAI-compatible API

Expose a familiar local protocol to maximize compatibility with coding clients.
