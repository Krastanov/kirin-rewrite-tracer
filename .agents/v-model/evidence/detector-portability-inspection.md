# Detector Portability Inspection

Inspection date: 2026-07-31. Production source identity:
`e8077564b5503b2b02bd51230657f25cad00cd85`.

## Inspected surface

The callback detector spans descriptor preflight in
[`_compat.py`](../../../src/kirin_rewrite_tracer/_compat.py), public-frame
classification in
[`_session.py`](../../../src/kirin_rewrite_tracer/_session.py), and saved-mutation
authorization in [`_mutation.py`](../../../src/kirin_rewrite_tracer/_mutation.py). It
uses:

- `sys.getprofile()`, `sys.setprofile()`, and documented `call`/`return` callback
  arguments ([Python 3.10](https://docs.python.org/3.10/library/sys.html#sys.setprofile),
  [Python 3.13](https://docs.python.org/3.13/library/sys.html#sys.setprofile));
- exact `frame.f_code` and immediate read-only `frame.f_locals.get()` for public
  `self`/`node` and saved-mutation receiver/class authorization
  ([3.10 data model](https://docs.python.org/3.10/reference/datamodel.html),
  [3.13 frame objects](https://docs.python.org/3.13/reference/datamodel.html#frame-objects));
- function `__code__`
  ([3.10](https://docs.python.org/3.10/reference/datamodel.html#user-defined-functions),
  [3.13](https://docs.python.org/3.13/reference/datamodel.html#user-defined-functions));
- `type(rule).__mro__`
  ([3.10](https://docs.python.org/3.10/library/stdtypes.html#class.__mro__),
  [3.13](https://docs.python.org/3.13/reference/datamodel.html#type.__mro__)) and read-only
  namespace [`vars()` in 3.10](https://docs.python.org/3.10/library/functions.html#vars)
  and [3.13](https://docs.python.org/3.13/library/functions.html#vars);
- raw `classmethod` and `staticmethod` descriptor `__wrapped__`
  ([3.10 `classmethod`](https://docs.python.org/3.10/library/functions.html#classmethod),
  [3.10 `staticmethod`](https://docs.python.org/3.10/library/functions.html#staticmethod),
  [3.13 `classmethod`](https://docs.python.org/3.13/library/functions.html#classmethod),
  [3.13 `staticmethod`](https://docs.python.org/3.13/library/functions.html#staticmethod));
- `inspect.isfunction()`, `isgeneratorfunction()`, `iscoroutinefunction()`, and
  `isasyncgenfunction()` ([3.10](https://docs.python.org/3.10/library/inspect.html#types-and-members),
  [3.13](https://docs.python.org/3.13/library/inspect.html#types-and-members)); and
- ordinary type/identity checks and a LIFO list of active frames.

Every classification-time `f_locals` access is read-only, immediate, independent of
mapping concrete type/identity, and not retained. No runtime result substitutes for
this 3.10/3.13 documentation inspection.

`_classify_frame` walks the concrete rule MRO, reads each namespace, unwraps a raw
`staticmethod`/`classmethod` candidate through documented `__wrapped__` only to reject
a matching nonplain descriptor, and accepts one plain function with the exact callback
code. `authorize_profile_call` separately matches an expected saved mutation code and
reads its declared receiver/class local once. Descriptor preflight and wrapper
installation use the same documented raw `classmethod.__wrapped__` surface. These are
the four raw-descriptor accesses in production.

Inspection of both classification paths searched for `sys.monitoring`,
`threading.setprofile_all_threads`, `frame.f_generator`, `f_lasti`, `dis`, opcode or
`co_code`, manual `co_flags`, writable `f_trace`, private/native frame access,
annotation/signature/source classification, `co_name`, `__subclasses__`, and
`sys.version_info` branches. It found none. Wrapper-only `sys._getframe()` calls provide
the caller frame to invocation-stack capture after classification; they do not classify
a rewrite or saved delegation. The source inventory and supported-minor matrix satisfy
SYSV-011. Stack evidence remains separately implemented under SYSV-014.

## Executable invalid-`self` counterexample

[`test_invalid_self_direct_override_is_silently_ignored_counterexample`](../../../test/test_detector_nonconformance.py)
defines an ordinary direct `RewriteRule.rewrite` override, then executes its unbound
function as `_DirectOverride.rewrite(object(), _CounterexampleNode())` inside a valid
session. Across CPython 3.10.14–3.13.11 it returns the expected neutral
`RewriteResult`, and the recorder freezes a complete trace with zero events.

The cause is exact: invalid `self` triggers rejection only when `frame.f_code` is one of
the four pinned base `RewriteRule` codes. A subclass direct override has another code,
so classification returns “not a rewrite” before class-MRO matching is possible.

This violates:

- SYSV-004: an observable malformed public frame is silently omitted;
- INTV-002: an observable unsupported path does not invalidate; and
- UNITV-004: an invalid non-`RewriteRule` receiver does not cause sticky invalidation.

Those actions are `failing`. SYSV-010 still passes its valid-entry procedure, while
SYS-010 is not fully conforming because it also maps to failing SYSV-004.

## Unsafe remedies deliberately excluded

Classifying by `co_name == "rewrite"` would misclassify unrelated calls, contradict the
existing exact-code/runtime-owner rule, and recreate a known false-positive category.
Scanning `RewriteRule.__subclasses__()` would enumerate global mutable class state, miss
some dynamic ownership cases, retain classes, and exceed the approved documented
surface. No such workaround was added. A future mini-V must choose a sound observable
contract or a safe detector mechanism.
