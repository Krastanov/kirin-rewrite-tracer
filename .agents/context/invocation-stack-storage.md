# Structured Invocation-Stack Storage

- **Context need:** Explanation
- **Open when:** Designing, implementing, or reviewing invocation-stack capture,
  serialization, lifetime, path handling, or presentation.
- **Do not open when:** Working only on entity relationships, rendered ownership, or
  rewrite classification without storing code locations.
- **Related specification IDs:** STK-003, STK-004, SYS-011, SYS-012, SYS-014, SYS-015,
  SYS-017
- **Review when:** The Python compatibility floor or canonical frame fields change.

SYS-014 requires queryable observed invocation paths for rewrite events and selected
mutation operations without retaining Python execution state. A stack is evidence of
which code ran on the path, not proof of semantic causation.

## Options considered

| Capture form | Limitation | Judgment |
| --- | --- | --- |
| `inspect.stack()` records | Retain live frames and can form cycles; their representation changed in Python 3.11. | Reject. |
| Formatted traceback text | Mixes capture with presentation and source lookup; difficult to query or redact. | Reject. |
| Stored `FrameSummary` objects | Carry lazy source behavior and a version-growing surface. | Reject as canonical storage. |
| Project DTO copied from `traceback` summaries | Keeps three stable fields, no live frames, and no formatting dependency. | **Selected.** |

Use the documented Python 3.10/3.13 intersection:

```text
traceback.StackSummary.extract(
    traceback.walk_stack(frame_or_none),
    lookup_lines=False,
    capture_locals=False,
)
```

Immediately reverse the yielded inner-to-outer summary, copy only `filename`, `lineno`,
and `name` into `FrameLocation`, then discard summaries and frames. Keep the full
available stack; arbitrary depth limits belong only in presentation.

For mutation wrappers, omit capture and wrapper frames by exact known code identity so
the final retained frame is the direct caller. For a profile-detected rewrite entry,
start from the supplied rewrite frame so the final frame is the executing public
`rewrite`. Do not broadly filter Kirin or orchestration frames: the internal
`Statement.replace_by` caller followed by a rule callsite is useful exact context.
Exporters may collapse frames visually without changing storage.

Do not capture locals: capture invokes their `repr()` and its error behavior differs
across versions. Do not access `FrameSummary.line`: it can trigger file or loader I/O,
strips source text, and may be unavailable. Source display can resolve the stored
filename and line number later as non-authoritative enrichment. Columns, qualified code
names, bytecode positions, and newer monitoring APIs add no needed base behavior.

The canonical DTO is:

```text
RewriteEvent[..., invocation_stack_id]
InvocationStack[id, frames[]]
FrameLocation[filename, lineno, function]
```

Store the runtime filename string unchanged. Whether a future persisted or interactive
export redacts or rewrites paths is a presentation-policy decision; it must not mutate
the in-memory canonical trace. Equal stacks may be interned later if measurement shows
that storage matters.

An event stack records the invocation path to its public rewrite frame. A mutation stack
records the path to its direct non-tracer caller. An identity projection has no invented
mutation operation or operation stack; its containing event stack remains available.
The stack retained on an incomplete event is still the path observed at invocation
entry. It is not an exception traceback, does not identify an exception handler or raise
site, and must not be presented as one. A completed deletion effect follows its mutation
operation to that operation's invocation stack.
Kirin `SourceInfo` describes original program or IR source and is not a Python
invocation stack.

## Anchors

- [`StackSummary.extract` in Python 3.10](https://docs.python.org/3.10/library/traceback.html#traceback.StackSummary.extract)
  and [Python 3.13](https://docs.python.org/3.13/library/traceback.html#traceback.StackSummary.extract)
- [`walk_stack` in Python 3.10](https://docs.python.org/3.10/library/traceback.html#traceback.walk_stack)
  and [Python 3.13](https://docs.python.org/3.13/library/traceback.html#traceback.walk_stack)
- [`inspect` live-frame warning in Python 3.10](https://docs.python.org/3.10/library/inspect.html#the-interpreter-stack)
  and [Python 3.13](https://docs.python.org/3.13/library/inspect.html#the-interpreter-stack)
