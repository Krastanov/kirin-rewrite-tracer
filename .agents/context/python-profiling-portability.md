# Python Profiling Portability

- **Context need:** Reference
- **Open when:** Implementing or reviewing profile-slot ownership, rewrite-frame
  classification, or Python-version compatibility.
- **Do not open when:** Working only on event semantics, snapshots, rendering, export,
  or provenance after an event has been detected.
- **Related specification IDs:** SYS-002, SYS-010, SYS-011, SYS-014, SYS-015
- **Review when:** Kirin's declared Python floor, the initial test runtime, or a detector
  API changes.

SYS-011 requires the detector to use a documented surface shared by Python 3.10, the
pinned Kirin revision's declared floor, and Python 3.13. This is a dependency constraint,
not a claim that every Python implementation or minor version has been verified.

## Options considered

| Stance | Advantage | Limitation | Judgment |
| --- | --- | --- | --- |
| Pin to CPython 3.13 internals | Allows any implementation trick. | Turns one convenient test runtime into a brittle product constraint. | Reject. |
| Use the documented 3.10/3.13 intersection | Needs no per-minor adapter and matches Kirin's declared floor. | Does not prove a formal runtime range or alternate-interpreter behavior. | **Selected.** |
| Add per-version backends or `sys.monitoring` | Could expose richer events on newer runtimes. | Adds branches and another detector before a use case requires them. | Defer. |

## Permitted detector surface

Keep the version-sensitive detector code to:

- `sys.getprofile()`, `sys.setprofile()`, and documented `call` and `return` arguments;
- `type(self).__mro__` and read-only class namespace inspection with `vars()`;
- `inspect.isfunction()`, `inspect.isgeneratorfunction()`,
  `inspect.iscoroutinefunction()`, and `inspect.isasyncgenfunction()` on plain
  functions;
- function `__code__`, read-only frame `f_code`, and immediate mapping reads from
  `f_locals`; and
- ordinary runtime type, string, and identity checks plus a LIFO event stack.

Treat `frame.f_locals` as a transient mapping. Python 3.13 may expose optimized locals
through a write-through proxy, whereas Python 3.10 described a dictionary. Read `self`
and `node` immediately; never require a `dict`, compare or retain mapping identity, or
mutate it.

Do not use `sys.monitoring`, `threading.setprofile_all_threads`, `frame.f_generator`,
`f_lasti`, `dis`, opcodes, `co_code`, manual `co_flags`, writable `f_trace` attributes,
private frame APIs, native frame access, signature or annotation inference, source
locations, recursive profiling, or `sys.version_info` branches in the detector. Reject
a callable form that the permitted surface cannot classify.

The documented profile surface does not provide an exception event. A Python `return`
profile callback with argument `None` can represent either explicit `None` or exception
unwind. SYS-015 intentionally treats both as a neutral incomplete public event and does
not add `sys.settrace`, traceback inspection, bytecode, or a version branch to classify
them.

SYS-014's invocation-stack capture is separate from detector classification. After a frame
has been classified, the provenance adapter may copy the documented
`traceback.walk_stack()` and `StackSummary.extract()` fields declared there. Those
locations must not influence whether a frame is a rewrite event, and the adapter must
not retain frames or inspect bytecode, locals, or source text. This does not weaken the
detector's source-location prohibition.

## Evidence discipline

Initial execution tests use the available CPython 3.13.11 environment. Label them as
single-environment evidence, not a 3.13 product pin or evidence for unexecuted versions.
The exact interpreter/version support range remains a separate decision.

## Anchors

- [Pinned Kirin Python declaration](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/pyproject.toml#L13)
- [`sys.getprofile()` and `sys.setprofile()` in Python 3.10](https://docs.python.org/3.10/library/sys.html#sys.setprofile)
  and [Python 3.13](https://docs.python.org/3.13/library/sys.html#sys.setprofile)
- [Python 3.10 function and frame attributes](https://docs.python.org/3.10/reference/datamodel.html)
  and [Python 3.13 frame attributes](https://docs.python.org/3.13/reference/datamodel.html#frame-objects)
- [`inspect` predicates in Python 3.10](https://docs.python.org/3.10/library/inspect.html#types-and-members)
  and [Python 3.13](https://docs.python.org/3.13/library/inspect.html#types-and-members)
- [`sys.monitoring`, added in Python 3.12](https://docs.python.org/3.13/library/sys.monitoring.html)
