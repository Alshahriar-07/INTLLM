# Contributing to INTLLM

Thanks for your interest in improving INTLLM. This project values honest,
working software over impressive-looking claims.

## Ground rules

1. **No fake or demo functionality.** Report real state honestly. If a
   dependency is missing, say so; never fabricate availability, model lists,
   sources or results.
2. **Preserve working functionality.** Prefer small, focused changes over broad
   rewrites.
3. **Keep secrets out.** No API keys, passwords, tokens or private URLs in code,
   tests, logs, documentation or artifacts.
4. **Match existing conventions.** Follow the structure and style of the module
   you are editing.

## Getting set up

See [DEVELOPMENT.md](DEVELOPMENT.md). In short:

```bash
npm install
python -m pip install -e "./backend[dev]"
```

## Before you open a pull request

Run the gates locally:

```bash
# Backend
cd backend
ruff check --config pyproject.toml app tests
python -m pytest -q

# Frontend
npm run lint
npm run build
```

- Add or update tests for behavioral changes.
- Update documentation when behavior, configuration, endpoints or artifacts
  change (README, API.md, AGENT.md, CONFIGURATION.md, CHANGELOG.md, …).
- Keep the changelog's `Unreleased`/next-version section current.

## Commit style

- Write clear, imperative commit subjects focused on the *why*.
- Keep changes scoped; avoid unrelated reformatting.

## Reporting bugs and requesting features

- Open an issue with the INTLLM version (`intllm --version`), platform, and
  reproduction steps.
- For security issues, **do not** open a public issue — see
  [SECURITY.md](SECURITY.md) §21.

## License

INTLLM is released under the **PolyForm Noncommercial License 1.0.0**
(see [LICENSE](LICENSE)). By contributing, you agree your contributions are
provided under the same license.
