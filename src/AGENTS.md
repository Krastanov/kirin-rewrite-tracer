# Python Source Guidance

## Scope

This router applies to the `src/` code root and inherits the repository guidance.
Production package code lives only in `kirin_rewrite_tracer/`.

## Commands

- Lint source: `uv run ruff check src`
- Check formatting: `uv run ruff format --check src`
- Type-check source: `uv run mypy src`
- Run the corresponding tests: `uv run pytest test`

## Local rules

- Keep the package standalone; do not modify or import source from the sibling checkout
  by filesystem path.
- Keep Kirin- and Rich-specific behavior inside the pinned compatibility boundary. Open
  [the Kirin integration reference](../.agents/context/kirin-integration.md) before
  implementing that boundary.
- Preserve the six implemented root exports and add another only with its contract and
  tests.
- Store classic JavaScript and CSS viewer assets beneath
  `kirin_rewrite_tracer/assets/`; Hatch includes those file types in the wheel.
