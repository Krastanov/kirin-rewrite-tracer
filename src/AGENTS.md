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
- Keep Kirin- and Rich-specific behavior inside a pinned compatibility boundary when it
  is introduced. Open
  [the Kirin integration reference](../.agents/context/kirin-integration.md) before
  implementing that boundary.
- Do not export capture API placeholders. Add root exports only with their implemented
  contracts and tests.
- Store future classic JavaScript and CSS viewer assets beneath
  `kirin_rewrite_tracer/assets/`; Hatch includes those file types in the wheel.
