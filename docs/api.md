# API reference

The package intentionally exposes six names at its root.

## `trace_rewrites`

```python
trace_rewrites(*, analysis: Mapping[SSAValue, object] | None = None) -> TraceRecorder
```

Creates a fresh, one-shot recorder. Use it as a context manager around public Kirin
rewrite calls. Pass an SSA-value mapping only when analysis metadata should be captured.

## `TraceRecorder`

```python
recorder = TraceRecorder(analysis=None)
```

The lifecycle states are `CREATED`, `ACTIVE`, `FROZEN`, and `INVALID`. A successful
session moves from `CREATED` through `ACTIVE` to `FROZEN`; activation failure or
unsupported execution moves it to `INVALID`. `recorder.state` returns that name, while
`recorder.trace` returns the immutable trace only in the `FROZEN` state. A recorder
cannot be reused or nested.

## `export_html`

```python
export_html(trace: Trace, destination: str | PathLike[str]) -> Path
```

Atomically publishes a self-contained HTML viewer and returns its path. The parent must
already exist. The function raises `FileExistsError` instead of replacing a destination.

## `Trace`

The frozen trace contains canonical tuples for `events`, `snapshots`, `occurrences`,
`operations`, `relations`, `effects`, `metadata`, and their supporting entities, styles,
stacks, and capture configurations. `trace.complete` distinguishes normal completion
from a trace frozen after user code raised.

`trace.index()` builds disposable lookup indexes, and
`trace.snapshots_semantically_equal(left_id, right_id)` compares two snapshots while
ignoring representational differences that do not change their meaning.

## Exceptions

`TraceStateError`
: Raised when a recorder is entered more than once or its trace is requested before a
  valid trace has frozen.

`UnsupportedTraceError`
: Raised when execution leaves the supported tracing boundary. The recorder becomes
  `INVALID`, and no partial trace is exposed.
