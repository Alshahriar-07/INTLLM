# Local Service Lifecycle

On `intllm`:

```text
startup
  -> lock single instance
  -> detect PostgreSQL
  -> detect Ollama
  -> start/guide required services
  -> database migration
  -> backend startup
  -> frontend availability
  -> open browser
```

On exit:

- stop only services started by INTLLM when safe
- do not kill user-owned Ollama/PostgreSQL processes
- release lock
- flush pending safe writes

Use PID/ownership markers so INTLLM knows what it started.
