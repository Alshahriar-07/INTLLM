# Development Workflow

## Branches

- `main`: stable
- `develop`: integration
- feature branches: focused work

## Commits

Prefer:

- `feat:`
- `fix:`
- `refactor:`
- `test:`
- `docs:`
- `build:`
- `chore:`

## CI gates

Every merge should run:

1. formatting
2. linting
3. type checks
4. unit tests
5. integration tests
6. frontend build
7. API contract checks

Release additionally runs packaging and smoke tests.
