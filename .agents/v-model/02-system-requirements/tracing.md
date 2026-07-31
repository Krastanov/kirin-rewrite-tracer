# Trace Event Requirements

The uniform event model, hierarchy, neutral incomplete-event behavior, and normalized
snapshot comparison are confirmed. This comparison is not a general IR diff.

## SYS-001 — Capture paired rewrite states

- **Normative statement:** While tracing is active, the product shall retain an ordered
  pair of SSA states, one observed immediately before and one immediately after, for each
  rewrite occurrence that it reports as successfully traced.
- **Parents:** STK-001
- **Acceptance criterion:** Given deterministic supported wrapper and leaf occurrences
  with independently known changed and unchanged SSA outcomes, tracing them produces an
  attributable before/after pair per occurrence, ordered correctly and equal to the
  known input and result; each normally returning no-op has two equal states matching
  the independently known unchanged state. Snapshot equality compares the complete
  normalized retained payload, excluding only snapshot-record identity and event/state
  binding and treating equal effective per-code-point styles as equal.
- **Verification:** SYSV-001 (test)
- **Origin / risk:** Confirmed developer interview, 2026-07-29; diagnostic fidelity risk.
- **Context:** [Kirin integration reference](../../context/kirin-integration.md)

## SYS-003 — Preserve rewrite behavior while tracing

- **Normative statement:** Within the declared support envelope, tracing shall not change
  a rewrite's returned result object, propagated exception object, or resulting final IR
  relative to the same execution without tracing.
- **Parents:** STK-001, STK-004
- **Acceptance criterion:** Given equivalent deterministic successful, mutating, and
  raising fixtures, traced and untraced executions return the same result object or
  propagate the same exception object, and have identical explicit final statement
  order, parent associations, SSA-use target identities, metadata, and normalized styled
  snapshots.
- **Verification:** SYSV-003 (test)
- **Origin / risk:** Confirmed developer interview, 2026-07-29; instrumentation-induced
  behavior would invalidate diagnostic conclusions.
- **Context:** [Kirin integration reference](../../context/kirin-integration.md)

## SYS-008 — Record supported normal rewrite invocations uniformly

- **Normative statement:** For each otherwise-supported public rewrite invocation
  detected under SYS-010 whose profile return carries a `RewriteResult`, the product
  shall retain exactly one event, whether the concrete rule is an orchestration wrapper
  or leaf and regardless of its returned `RewriteResult.has_done_something` value. The
  event shall expose completion state `complete`, the concrete runtime rule type, and
  the before/after pair required by SYS-001 through the same event shape, even when
  another event in the trace is incomplete.
- **Parents:** STK-001, STK-002, STK-004
- **Acceptance criterion:** Given asymmetric nested supported-rule fixtures with
  independently known wrapper and leaf invocations, distinct concrete rule types, and
  changed and no-op outcomes for wrappers and leaves, plus a normally returning parent
  that catches an incomplete child, each `RewriteResult` return has exactly one
  same-shaped complete event, including every no-op and the caught-child parent, with
  the correct concrete type and before/after pair and no extra event.
- **Verification:** SYSV-008 (test), SYSV-015 (test)
- **Origin / risk:** Developer confirmation, 2026-07-29; wrapper-only, leaf-only, or
  change-only filtering would hide relevant orchestration activity.
- **Context:** [Orchestration tracing options](../../context/orchestration-tracing.md)

## SYS-009 — Preserve dynamic event hierarchy and sibling order

- **Normative statement:** Every event created under SYS-008 or SYS-015 shall expose an
  identifier unique within its trace, a parent identifier that references its nearest
  dynamically enclosing recorded invocation or is absent when no such invocation
  exists, and a sibling ordinal distinct within its parent group whose strict ordering
  matches entry order. All parentless root events form one parent group for this
  purpose.
- **Parents:** STK-002, STK-004
- **Acceptance criterion:** Given an asymmetric supported scenario with multiple root
  invocations, nested wrappers, repeated concrete rule types, and multiple children
  beneath one parent, every identifier is unique, every non-absent parent references the
  independently known nearest enclosing event, only root events lack a parent, and
  sorting siblings by ordinal reproduces the independently observed entry order.
- **Verification:** SYSV-008 (test), SYSV-015 (test)
- **Origin / risk:** Developer confirmation, 2026-07-29; lost nesting or order can
  misattribute a leaf effect to the wrong wrapper occurrence.
- **Context:** [Orchestration tracing options](../../context/orchestration-tracing.md)

## SYS-015 — Retain incomplete rewrite events and completed provenance

- **Normative statement:** When an otherwise-supported public rewrite frame detected
  under SYS-010 exits without a `RewriteResult`, the product shall retain its event with
  completion state
  `incomplete`, its pre-call root and before snapshot, its SYS-009 hierarchy fields, its
  SYS-014 invocation stack, and all selected mutation operations that completed or
  remained incomplete under it, including every exact relation or completed effect
  attached to a completed operation. It shall retain no after snapshot or synthetic
  failure snapshot for that event and shall mark the aggregate trace incomplete. A
  normally returning ancestor that catches such an exit shall complete under SYS-008;
  the incomplete descendant shall remain under its original parent. When the exit
  propagates through multiple recorded public frames, each exiting frame shall be
  incomplete. The product
  shall not claim whether the neutral exit was caused by an exception or an explicit
  non-`RewriteResult` return, shall not create an event for an exception outside a
  supported public rewrite frame, and shall not roll back, copy to an ancestor, or
  reassign a retained mutation operation. Tracing shall not replace or suppress the
  original return or exception and shall preserve final IR as required by SYS-003.
- **Parents:** STK-004
- **Acceptance criterion:** Given independently logged fixtures in which a child
  completes selected mutations and then raises a preconstructed exception that its
  parent catches before completing another mutation and returning normally; the same
  child exception instead propagates through its parent; and a rule explicitly returns
  `None`, every affected event has the correct neutral completion state, original
  hierarchy, before state, invocation stack, and operation ownership. Complete ancestors
  retain after states; incomplete events do not. Every trace containing an incomplete
  event is marked incomplete, and traced behavior matches the untraced fixtures.
  Only the presence of an incomplete event makes aggregate event-derived completeness
  incomplete; an exception outside every supported public frame creates no event and
  does not by itself change aggregate completeness.
- **Verification:** SYSV-015 (test)
- **Origin / risk:** Developer confirmation and generic-profile investigation,
  2026-07-30; completed diagnostic evidence should survive failure without relying on
  profiler semantics that cannot distinguish an explicit `None` from exception unwind.
- **Context:** [Orchestration tracing options](../../context/orchestration-tracing.md)
