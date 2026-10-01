# Model Runtime and Adapter Design

## Goal

Any compatible local model should gain INTLLM's environment without modifying model weights.

## Flow

```text
INTLLM Runtime
 -> Model Adapter
 -> Ollama
 -> Local Model
```

## Adapter responsibilities

- model discovery
- capability detection
- context limits
- streaming
- tool-call format
- structured output
- error handling
- retry
- cancellation

## Ollama adapter

Initial implementation target.

Expected operations:

- list models
- pull model
- delete model
- inspect model
- generate/chat
- stream response
- health check

## Context builder

Build context from:

1. system policy
2. user message
3. relevant memory
4. verified live sources
5. tool results
6. conversation history

Use token budgets. Do not dump the whole Secondary Brain into context.

## Important

The system prompt is not a security boundary. Tool permissions must be enforced by INTLLM.
