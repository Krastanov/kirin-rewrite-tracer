# Kirin Rewrite Tracer

[![CI](https://github.com/Krastanov/kirin-rewrite-tracer/actions/workflows/ci.yml/badge.svg)](https://github.com/Krastanov/kirin-rewrite-tracer/actions/workflows/ci.yml)

`kirin-rewrite-tracer` records Kirin rewrite calls as a deeply immutable trace and
exports that trace as one autonomous, inert HTML viewer.

## Use

Install the locked development environment with `uv sync --python 3.13`, then:

```python
from pathlib import Path

from kirin_rewrite_tracer import export_html, trace_rewrites

with trace_rewrites() as recorder:
    result = rule.rewrite(node)

trace = recorder.trace
published = export_html(trace, Path("rewrite-trace.html"))
```

The export parent must already exist and the destination must not. An existing or raced
target raises `FileExistsError` without overwrite. Successful export returns the
published `Path`. Pass `analysis=<ssa-value mapping>` only when caller analysis metadata
should be captured.

A supported body exception freezes the valid trace before propagating the same exception
object. Keep the recorder bound outside the `with` statement to retrieve it:

```python
recorder = trace_rewrites()
try:
    with recorder:
        rule.rewrite(node)
except BaseException:
    if recorder.state == "FROZEN":
        trace = recorder.trace
    raise
```

Unsupported use raises `UnsupportedTraceError`, permanently invalidates the recorder,
and exposes no partial trace. `TraceRecorder` is one-shot; active trace access raises
`TraceStateError`.

The public root exports are `trace_rewrites`, `export_html`, `Trace`,
`TraceRecorder`, `TraceStateError`, and `UnsupportedTraceError`.

## Supported boundary

- CPython `>=3.10,<3.14`, Rich `15.0.0`, and Kirin commit
  `7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a`.
- One single-threaded, non-nested session with an initially empty profile slot and the
  five pinned Kirin mutation descriptors.
- During capture, traced code must not replace the active profile callback or descriptors
  or behaviorally inspect tracer-added frames/wrappers.
- Ordinary synchronous Python public rewrite entries. Executed generators, coroutines,
  async generators, cross-instance specialized dispatch, and selected-mutator bypasses
  are unsupported.
- Snapshot, printer, and invoked metadata-representation hooks must terminate, remain
  IR-pure, and not perform public rewrites, specialized dispatch, or selected mutations.
- Unobservable C/custom descriptors and never-executed deferred callables have no
  diagnostic claim.
- The sole viewer target is headed Chrome for Testing `151.0.7922.47`, provision
  revision `r1654411`, `linux64` on x86-64 Linux.
- Viewer evidence covers 100%/200% page zoom and finite fixtures at measured CSS
  viewports at least `640×480`. A viewport below 640 CSS pixels wide or below 480 CSS
  pixels high, other browsers/platforms, headless, mobile, and touch carry no v1 claim.

The viewer provides native event and occurrence controls, an always-available Clear
selection button, a per-non-leaf-event collapse control, selected-event canonical facts,
exact neighboring provenance, definition metadata, keyboard/focus handling, and the
fixed dark cascade.

A collapse control hides its event's whole subtree and never reveals a row that a
selected ancestor hides. It is enabled only while no selected event lies in its own
subtree, counting the event itself, so collapsing can never hide the selection or the
Shift-range anchor. Clear selection leaves collapse state untouched.

## Known nonconformances

- An unbound direct rewrite override called with an invalid `self` can be silently
  ignored, yielding a complete empty trace instead of `UnsupportedTraceError`.
- If publication creates the destination and then reports an error, the temporary file
  is removed but the destination can remain, contrary to the current failure contract.
- Very large valid snapshot text can exceed pinned Blink's horizontal layout extent,
  leaving a later control unreachable. Finite viewport tests do not prove universal
  trace-size reachability.

See the [V-model profile](.agents/v-model/index.md), [verification evidence](.agents/v-model/evidence/index.md),
and [acceptance handoff](.agents/v-model/evidence/acceptance-handoff.md). Developer
acceptance of ACC-001 through ACC-005 remains pending.

## Verify

```console
uv run pytest -m 'not browser'
uv run ruff check .
uv run ruff format --check .
uv run mypy src test
uv run pre-commit run --all-files
uv build
```

The pinned headed-browser command is documented in
[`test/browser-fixtures/README.md`](test/browser-fixtures/README.md).

Continuous integration runs every gate above on CPython 3.10 through 3.13, repeats the
suite against the installed wheel, and runs the pinned headed-browser suite on the
producer runtime. The repository-documentation linter lives in the sibling workspace and
is not part of continuous integration.
