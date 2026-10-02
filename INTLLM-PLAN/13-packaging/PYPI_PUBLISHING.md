# PyPI Publishing

**Status: Implemented (v1.0.2 Stage 1).**

The `intllm` Python distribution is published to PyPI by
`.github/workflows/pypi.yml`.

## Authentication — Trusted Publishing (OIDC)

No API token is stored in the repository. The workflow authenticates with PyPI
**Trusted Publishing**. Configure a publisher on PyPI with:

```text
Owner:       Alshahriar-07
Repository:  INTLLM
Workflow:    pypi.yml
Environment: pypi
```

A separate environment `testpypi` is used for the manual TestPyPI path.

## Triggers

* `release: published` — the normal path. `release.yml` builds and publishes the
  GitHub Release; publishing the release fires this workflow, which publishes the
  Python package.
* `workflow_dispatch` — manual run; the `target` input selects `testpypi` or
  `none` (build-only).

## Pipeline

The `build` job runs first and gates publishing:

1. Check out, `actions/setup-python@v5` (Python 3.12, pip cache).
2. Resolve the version from `backend/app/__init__.py` (single source of truth)
   and verify it matches the release tag (`vX.Y.Z`).
3. Install the backend with dev extras plus `build` and `twine`.
4. Run `pytest` against a real `pgvector/pgvector:pg16` service — tests are a
   release gate.
5. `python -m build --outdir dist backend` (PEP 517, isolated).
6. `twine check` plus a scripted content check (wheel contains `METADATA` and the
   `app` package; sdist contains `pyproject.toml`).
7. Install the wheel into a clean venv and run `intllm --version`.
8. Upload the distribution as an artifact.

`publish-pypi` / `publish-testpypi` download the artifact and publish with
`pypa/gh-action-pypi-publish`. Publishing never runs if build, tests or
validation fail.

## Package metadata

`backend/pyproject.toml` provides name, dynamic version, description, README,
license, authors, keywords, classifiers, project URLs, dependencies, optional
extras (`browser`, `gpu`, `dev`), the `intllm` / `intllm-api` console scripts and
setuptools package discovery (`app*`).

## Local dry run

```bash
pip install --upgrade build twine
python -m build --outdir dist backend
python -m twine check dist/*
```
