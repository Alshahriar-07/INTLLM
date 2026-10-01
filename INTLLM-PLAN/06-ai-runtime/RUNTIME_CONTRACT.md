# INTLLM Runtime Contract

A model running under INTLLM receives a stable environment contract.

Conceptually:

- You are running inside INTLLM.
- Relevant memory may be available.
- Live retrieval can be requested when information is missing or stale.
- Tool results are authoritative only when actually returned by the runtime.
- Never invent tool execution.
- Prefer verified current information when freshness matters.
- Reusable validated knowledge can become a memory candidate.

The contract should be versioned so future model adapters can remain compatible.
