# Testing Strategy

## Unit

- routing
- memory scoring
- TTL
- context assembly
- adapters
- permission policy
- API key hashing
- hardware detection

## Integration

- PostgreSQL
- pgvector
- Ollama
- browser
- retrieval
- background jobs

## E2E

Test the complete flow:

```text
intllm
 -> browser opens
 -> model ready
 -> user asks question
 -> memory lookup
 -> response stream
```

## Performance

Measure:

- time to first token
- total response latency
- Flash Brain lookup latency
- database query latency
- memory retrieval latency
- background worker impact

## Failure tests

- Ollama unavailable
- PostgreSQL unavailable
- internet unavailable
- browser crash
- model pull interrupted
- low disk space
- low RAM
- cancelled request
- malformed tool call
