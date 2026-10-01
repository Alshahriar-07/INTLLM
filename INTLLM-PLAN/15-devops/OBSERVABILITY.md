# Observability

Provide a local diagnostics page.

## Metrics

- requests
- latency
- time to first token
- model inference duration
- Flash Brain hit rate
- memory retrieval latency
- internet retrieval latency
- tool latency
- background job queue
- errors

## Logging

Use structured logs.

Levels:

- DEBUG
- INFO
- WARNING
- ERROR

Never log:

- API keys
- passwords
- authorization headers
- sensitive browser credentials
