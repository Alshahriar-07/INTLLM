# Layered Memory Architecture

## L0 Flash Brain

Purpose: extremely fast routing/index lookup.

Stores:

- memory ID
- compact keywords
- semantic embedding/vector
- memory type
- confidence
- freshness/TTL
- source pointer
- last updated
- status

It does NOT store full knowledge.

## L1 Hot Cache

Stores frequently accessed compact knowledge in memory/fast cache.

Candidate promotion signals:

- frequency
- recency
- latency benefit
- confidence
- user relevance

## L2 Secondary Brain

Persistent knowledge:

- Facts
- Workflows
- Failures/lessons
- Preferences that are explicitly allowed to persist
- Source metadata
- Verification metadata

## Routing

```text
Query
 -> L0
    -> strong fresh match: L1/L2
    -> weak/stale match: verify/retrieve
    -> no match: live retrieval when required
```

## TTL

- Static workflows: long
- Software documentation: medium
- Pricing/current availability: short
- News/live events: very short

## Memory quality

Every stored item should have:

- confidence
- source(s)
- created_at
- verified_at
- freshness policy
- provenance
- optional expiry
