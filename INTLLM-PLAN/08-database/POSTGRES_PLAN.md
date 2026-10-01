# Local PostgreSQL Plan

PostgreSQL is the primary persistent local database.

## Extensions

- pgvector for semantic memory search.

Use other extensions only when there is a concrete requirement.

## Local deployment

Development can use Docker Compose.

Production Windows distribution should support a managed local PostgreSQL installation or a controlled bundled/service setup, depending on licensing and operational testing.

Do not make Docker a mandatory end-user dependency for the first Windows UX.

## Connection

Backend connects only to the local PostgreSQL instance by default.

Use a dedicated INTLLM database and least-privilege database role.

## Backups

Provide:

- manual export
- scheduled local backup option
- restore/verify flow

Backups must not upload anywhere by default.
