# Initial PostgreSQL Schema

Core tables:

```text
app_settings
models
conversations
messages
memory_items
memory_sources
flash_index
hot_cache_metadata
tool_runs
browser_sessions
api_keys
background_jobs
job_events
audit_events
diagnostics
```

## Important relationships

- conversation -> messages
- memory_item -> memory_sources
- memory_item -> flash_index
- model -> conversations
- background_job -> job_events
- api_key -> audit events

## Secrets

Never store raw API keys. Store a hash/fingerprint for verification and show the user the secret only at creation time if the product requires reusable keys.

External credentials should use an encrypted local secret store where possible.
