# Background Learning Engine

## Goal

Continuously improve memory quality without hurting interactive response performance.

This is not 24/7 full-power model retraining.

It is low-priority knowledge/experience maintenance.

## Priority

```text
P0 interactive user request
P1 interactive tool work
P2 background memory maintenance
P3 optional heavy indexing/cleanup
```

P2/P3 work must yield immediately when resources become constrained.

## Jobs

- memory verification
- stale memory refresh
- duplicate detection
- memory compression
- embedding/index updates
- hot-cache promotion/demotion
- failed workflow analysis
- source freshness checks
- orphan cleanup

## Pause/resume

```text
Background job
   |
User request arrives
   |
throttle/pause
   |
Interactive work
   |
resume
```

## Candidate learning

Do not automatically trust every conversation.

Create a candidate -> verify -> promote pipeline.

## Resource governor

Monitor CPU/RAM/GPU and queue latency.

If interactive latency crosses the configured threshold, reduce or pause background work.
