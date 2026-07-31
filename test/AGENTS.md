# Test Guidance

## Scope

This router applies to the singular `test/` pytest root and inherits the repository
guidance.

## Commands

- Run all tests: `uv run pytest`
- Run one file: `uv run pytest test/<file>.py`
- Lint and type-check tests: `uv run ruff check test` and `uv run mypy test`

## Local rules

- Build expected values from fixture construction and independent observations, not from
  tracer helpers that implement the behavior under test.
- Keep source tests portable across CPython 3.10 through 3.13. Mark headed-Chrome tests
  with `pytest.mark.browser` when that harness is introduced.
- Keep generated browser profiles, downloads, screenshots, reports, and logs outside the
  repository.
