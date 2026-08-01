# Orchestration Tracing Options

- **Context need:** Explanation
- **Open when:** Designing or reviewing rewrite-call interception, event-tree recording,
  wrapper support, or restoration behavior.
- **Do not open when:** Working only on snapshot contents, rendering, export, or
  provenance after an event has already been captured.
- **Related specification IDs:** STK-002, STK-004, SYS-001, SYS-002, SYS-003, SYS-004,
  SYS-008, SYS-009, SYS-010, SYS-011, SYS-015
- **Review when:** The pinned Kirin rewrite dispatch, confirmed entry category, or Python
  tracing mechanism changes.

The [V-model](../v-model/02-system-requirements/index.md) defines one uniform event for
each supported wrapper or leaf call, including no-ops and neutral incomplete records
when a frame does not return a `RewriteResult`. This page records the selected filtering
trade study. SYS-002 makes exclusive ownership of the
current thread's Python profile slot externally normative; SYS-011 constrains the
detector to the documented cross-minor surface in the
[Python portability reference](python-profiling-portability.md). Callable forms outside
the confirmed ordinary synchronous category invalidate when their unsupported execution
is observable; deferred and unobservable forms remain explicit v1 input assumptions.

## Options considered

| Interception seam | Advantage | Limitation | Judgment |
| --- | --- | --- | --- |
| Patch only `RewriteRule.rewrite` | Tiny and easy to restore. | Misses every class that owns a direct `rewrite` override, including Kirin's orchestration wrappers. | Reject. |
| Recursively inspect subclasses and temporarily wrap each Python `rewrite` method owner | Direct call/return boundary; calls that resolve the method during the context can reject a foreign thread; restores exact class attributes. | Mutates classes process-wide and misses pre-bound methods and method owners created after activation. | Viable explicit-table fallback, but its silent blind spots need extra guards. |
| `sys.setprofile` filtered to `RewriteRule` frames | No Kirin class mutation; naturally sees inherited, direct, dynamically created, pre-bound, and unbound Python calls. | Requires exclusive ownership of the current-thread profile slot and suppresses recursive profiling inside capture hooks. | **Selected as the smallest v1 detector.** |
| `sys.settrace` | Adds exception events and line detail. | Requires a second global-style hook, is noisier and slower, and conflicts more readily with debuggers and coverage. | Reject for v1; the neutral incomplete record meets the confirmed need without asserting an exception classification. |
| Add an upstream Kirin hook | Clean stable boundary if accepted upstream. | Changes the sibling project and is no longer a quick standalone tracer. | Possible later integration, not v1. |

## Current minimal recommendation

Use a thread-local `sys.setprofile` callback. Before changing the slot, require
`sys.getprofile()` to be `None`; otherwise fail entry and leave the installed function
untouched. Install the tracer callback only after validation. On every exit, remove it
in `finally` only when the current function is still the tracer's exact callback, so
normal and exceptional exits both restore `None`. A different function indicates a
lifetime-assumption violation: best-effort handling may invalidate the trace but must
not clobber the replacement. Replacement followed by restoration before exit can remain
undetected. Do not chain arbitrary profile functions.

On a Python `call` event, read `self` and `node` from `frame.f_locals` through mapping
lookups only, then require them to be a `RewriteRule` and `IRNode`. Walk
`type(self).__mro__`, read each class namespace with `vars()` so descriptors are not
invoked, and accept the frame only when its `f_code` is identical to `__code__` on a
plain Python `rewrite` function found there. Use `inspect.isfunction()`,
`inspect.isgeneratorfunction()`, `inspect.iscoroutinefunction()`, and
`inspect.isasyncgenfunction()` on that plain function to exclude deferred-execution
forms; do not decode `co_flags`. This MRO-wide check records explicit
`super().rewrite(node)` or unbound-base calls as nested public invocations instead of
confusing them with specialized dispatch.

For an accepted call:

1. Allocate an event identifier and a sibling ordinal, using the active event stack for
   the parent.
2. Retain the pre-call root object, capture the before state, and push the event.
3. On a `return` callback carrying a `RewriteResult`, capture the after state from the
   same retained root, finalize the event as `complete`, and pop it.
4. On any other `return` callback, retain the event as `incomplete` with its before
   snapshot and entry-time hierarchy and stack, retain completed and incomplete selected
   mutation operations under their actual owners, omit an after or synthetic failure
   snapshot, mark the aggregate trace incomplete, and pop without throwing from the
   callback.

`sys.setprofile` reports both an explicit `None` return and exception unwinding as a
`return` event carrying `None`, with no exception event. The supported synchronous
category normally returns `RewriteResult`, so this is enough to detect that capture did
not complete. It is not enough to say why, especially if caller code later catches an
exception. The event therefore uses the neutral state `incomplete`, not `raised`; its
invocation stack is the entry path and is not an exception traceback. A parent that
catches the child exit can return normally and retain its own after state, while the
child stays incomplete. A propagated exit makes each recorded public frame incomplete.
An exception outside a public frame does not manufacture an event.

Event identifiers are opaque domain-prefixed monotonic values and sibling ordinals are
zero based. A non-`RewriteResult` public return remains neutral incomplete. An observable
malformed public frame or resumed generator, awaited coroutine, or iterated
async-generator invalidates the recorder. A profile hook cannot observe a deferred
callable never executed or a C/custom descriptor that creates no suitable Python frame;
those remain input assumptions with no v1 diagnostic claim.

Do not use `sys.call_tracing` or another recursive-profile technique. V1 deliberately
makes no guarantee about activity initiated from its own profile callback. Because
before/after capture is initiated there, SYS-002 instead requires snapshot, printer, and
metadata-representation hooks not to invoke public rewrites or specialized handlers.
This is an undetected input assumption; supporting such recursion would require another
interception seam.

SYS-002 now makes a process that remains single-threaded for the entire trace context a
hard input assumption whose violation need not be detected. Therefore the prototype
needs no all-thread profiler or global class-level thread guard. A multithreaded run has
no guaranteed trace or diagnostic and is not a supported degradation path.

## Why an explicit support check is still needed

Most Kirin leaf rules inherit base dispatch and need no class-specific logic. The pinned
tree also contains direct `rewrite` owners:

- `Walk`, `Fixpoint`, and `Chain`;
- `CompactifyRegion`;
- aggressive `Fold`; and
- `WalkDesugarBinop`.

`CFGCompactify` inherits base dispatch but constructs `CompactifyRegion` dynamically, so
it is a useful nested-support fixture. `ScfToCfRule` directly calls another rule
instance's specialized `rewrite_Statement` instead of its public `rewrite()` entry
point. V1 originally rejected that crossing rather than present the outer event as a
complete account of its owned activity. It now opens a nested event owned by the
delegated rule, satisfying the same concern by attribution instead of refusal: the
sub-rule owns its activity and mutations, and the outer event stays honest. Refusal is
retained only where no invocation is open, leaving no parent to attribute to.

The confirmed frame-shaped category naturally covers ordinary third-party direct
overrides, including one created after context entry, a pre-bound method, and an unbound
class-function call. A profile callback can watch plain synchronous Python specialized
`rewrite_Region`, `rewrite_Block`, and `rewrite_Statement` frames: a handler is internal
only when its `self` is identical to the innermost open invocation's rule; any other
`self` opens its own nested event rather than hiding owned child activity, so
equal-but-distinct rules still nest. The compatibility adapter should keep these
checks in one pinned module rather than scatter rule-specific branches through the event
model. Runtime types and return values, not optional annotations, determine
compatibility.
