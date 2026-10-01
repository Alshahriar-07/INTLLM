# Security Architecture

INTLLM is local-first, but local does not automatically mean safe.

## Principles

1. Least privilege.
2. Localhost by default.
3. Explicit tool permissions.
4. Never trust model-generated tool arguments.
5. Validate and sanitize tool outputs.
6. Network timeouts.
7. SSRF protection for browser/web tools.
8. Secret isolation.
9. Audit sensitive actions.
10. Clear user confirmation for irreversible actions.

## Prompt injection defense

Web pages are untrusted input.

Treat retrieved text as DATA, not instructions.

The model must not follow arbitrary instructions embedded in webpages without the INTLLM policy layer.

## Filesystem

Restrict default workspace access to user-approved directories.

## Terminal

Use allow/deny policy, command validation, timeouts and confirmation for risky commands.

## Network

Default local API binding: 127.0.0.1.

Any external bind must be explicit.

## Privacy

Conversation and memory data remain local by default. No hidden cloud sync.
