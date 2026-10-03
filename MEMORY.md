# INTLLM Memory (Brain)

INTLLM gives local models a layered memory system stored entirely in local
PostgreSQL with pgvector. Relevant knowledge is retrieved during chat and
labelled in the response.

---

## Layers

| Layer | Name | Purpose |
| --- | --- | --- |
| **L0** | Flash Brain | Fast routing/index over memory: is useful memory available, where, how fresh, how confident? |
| **L1** | Hot Cache | Short-lived promoted context (TTL) — a repeat lookup avoids all vector work |
| **L2** | Secondary Brain | Durable, curated knowledge store backed by PostgreSQL + pgvector |

L0 is an **index**, not the full knowledge store. Full content lives in L2; L0
makes lookup fast. L0 lookup runs a vector search against the flash index and
falls back to L2 keyword search when embeddings are unavailable.

## Memory items

A memory item is a structured record, not a raw page dump:

- type: `fact` / `workflow` / `lesson` / `preference`
- compact content, keywords
- confidence and importance scores
- status
- freshness: score, policy, `verified_at`, optional `expires_at`
- provenance: source records in `memory_sources` (URL, title, source type,
  retrieval/verification timestamps)

## Freshness policies (TTL)

| Policy | Approximate lifetime |
| --- | --- |
| `static` | ~1 year |
| `long` | ~180 days |
| `medium` | ~30 days |
| `short` | ~7 days |
| `live` | 6 hours |

## Promotion to the hot cache

A top memory match that is both confident (≥ 55) and fresh (≥ 60 freshness
score) is promoted to the hot cache. Background cleanup invalidates expired
entries. Promoted query results default to a 30-minute TTL.

## Availability

Memory is reported available only when PostgreSQL, pgvector **and** the schema
are ready. If the vector store is not ready, the UI reports memory as
unavailable — INTLLM never pretends semantic memory works.

## Creating memories

Users can create memories explicitly through the Brain workspace / API
(`POST /api/brain/memories`). Automatic post-response learning (candidate →
verify → promote) is **planned**, not implemented.

## Background maintenance

Low-priority background jobs keep memory and indexes fresh:

- memory verification (expired items marked stale)
- stale data refresh (freshness statistics)
- embedding index updates (honest indexed/total counts)
- hot-cache promotion/cleanup

These are memory/index maintenance jobs — **not** continuous retraining of
Ollama model weights. A resource governor tracks interactive latency and CPU/RAM
thresholds and throttles or pauses background work under pressure; user requests
always have priority.

## Storage

Memory lives in the local PostgreSQL + pgvector database alongside chat history.
See [DATABASE.md](DATABASE.md) for backup and location details.
