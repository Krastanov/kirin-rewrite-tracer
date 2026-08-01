# Stakeholder Outcomes

The developer actor, local debugging and test environment, and the first advanced
outcomes are confirmed.

## STK-001 — Inspect a rewrite's SSA effect without presentation or metadata loss

- **Normative statement:** A Kirin developer shall be able to inspect the SSA effect of a
  rewrite that completes successfully by obtaining the state immediately before and
  immediately after its execution, including each state's styled SSA presentation and
  owner-associated semantic metadata.
- **Parents:** None
- **Acceptance criterion:** Given developer-approved structural, style-distinct, and
  metadata-only Kirin rewrite scenarios with independently known states and printer
  output, after tracing each scenario the developer can retrieve an attributable
  before/after pair in the correct order, inspect every expected metadata value under
  the correct IR or SSA owner, observe every expected style distinction at the correct
  visible text interval, and, for the metadata-only scenario, identify its difference.
- **Verification:** ACC-001 (demonstration)
- **Origin / risk:** Confirmed developer interview and presentation- and
  metadata-fidelity confirmations, 2026-07-29; flattened or incomplete diagnostic output
  can conceal a rewrite's only effect.
- **Context:** None

### Operational scenarios

- A developer locally investigates which rewrite changed a Kirin program and inspects
  the state on both sides of that rewrite.
- A developer identifies a rewrite whose only observable effect is a change to SSA
  metadata.

## STK-002 — Inspect orchestration hierarchy

- **Normative statement:** A Kirin developer shall be able to inspect the relationship
  between supported orchestration-wrapper invocations and supported leaf rewrite
  occurrences.
- **Parents:** None
- **Acceptance criterion:** Given a developer-approved scenario with independently known
  wrapper and leaf relationships, after tracing the scenario the developer can identify
  which supported leaf occurrences belong to each supported wrapper occurrence.
- **Verification:** ACC-002 (demonstration)
- **Origin / risk:** Developer confirmation, 2026-07-29; incorrect hierarchy can
  misattribute rewrite effects.
- **Context:** None

### Operational scenario

- A developer inspects and analyzes nested rewrite activity.

## STK-003 — Inspect exact rewrite provenance and its invocation path

- **Normative statement:** A Kirin developer shall be able to inspect which entities in
  paired SSA states are the same live objects, which are related by a declared supported
  mutation operation, which supported operation completed a statement deletion, and
  which Python call path led to each supported rewrite and mutation. The developer shall
  be able to navigate each exact fact from either applicable endpoint without heuristic
  lineage being presented as fact.
- **Parents:** None
- **Acceptance criterion:** Given a developer-approved scenario with independently
  known surviving, replaced, use-retargeted, copied, cloned, transient, created,
  deleted, and visually similar but unrelated entities, the developer can identify
  every exact identity, selected-mutation relation, and supported deletion effect,
  navigate it from each applicable endpoint, inspect its rendered occurrence sets and
  invocation stack where applicable, see entities with no supported fact marked
  unmatched, and observe no unsupported relation or effect.
- **Verification:** ACC-003 (demonstration)
- **Origin / risk:** Developer confirmation, 2026-07-30; inferred lineage or missing
  invocation context can misdirect rewrite diagnosis.
- **Context:** None

### Operational scenarios

- A developer follows an entity through movement, replacement, use retargeting, or
  cloning across a rewrite.
- A developer navigates from a provenance operation to the Python path that invoked it.
- A developer navigates from a disappeared statement to the supported operation and
  call path that completed its deletion.
- A developer distinguishes “not related” from “no exact supported provenance fact was
  observed.”

## STK-004 — Inspect completed activity before an incomplete rewrite exit

- **Normative statement:** A Kirin developer shall be able to inspect a supported
  rewrite invocation that did not return a `RewriteResult`, including its input state,
  dynamic position, invocation path, and every selected mutation operation known to
  have completed before that invocation exited together with its exact relation or
  effect, without the tracer claiming an output state or changing the program's behavior.
- **Parents:** None
- **Acceptance criterion:** Given developer-approved scenarios in which a supported
  rewrite completes a selected mutation and then raises, a nested raising rewrite is
  caught by its parent, a raising rewrite propagates through its parent, and a rewrite
  explicitly returns `None`, the developer can inspect each affected invocation as
  incomplete, retain its completed selected operations under their original owners,
  and distinguish absence of an after snapshot from a successful no-op. The same
  exceptions and final IR are observed with and without tracing.
- **Verification:** ACC-004 (demonstration)
- **Origin / risk:** Developer confirmation, 2026-07-30; discarding all activity on an
  exceptional exit hides useful exact evidence, while manufacturing an output state or
  exception classification would overstate what the selected generic profiler observes.
- **Context:** None

### Operational scenarios

- A developer diagnoses a rewrite that mutates IR and then raises.
- A parent rewrite catches a child failure and continues; the child remains visible at
  its original position in the event tree.

## STK-005 — Inspect a captured trace from one standalone HTML artifact

- **Normative statement:** A Kirin developer shall be able to export any retained trace,
  whether complete or incomplete, as one self-contained interactive HTML file and later
  inspect its captured information using only a local browser, without running the
  tracer, Python, Kirin, a server, a network service, or an auxiliary export file.
- **Parents:** None
- **Acceptance criterion:** Given developer-approved complete and incomplete traces with
  independently known styled SSA, metadata, hierarchy, provenance, deletion effects,
  invocation stacks, and absent after states, after copying only each exported HTML file
  into a clean offline environment and stopping the producer, the developer can open it
  directly and use only the document's facilities to inspect every expected fact,
  association, and explicit absence.
- **Verification:** ACC-005 (demonstration)
- **Origin / risk:** Developer confirmation, 2026-07-30; a renderer that depends on the
  tracing environment or silently omits trace detail is difficult to share and can
  mislead offline diagnosis.
- **Context:** None

### Operational scenarios

- A developer inspects a trace after the tracing process and environment are gone.
- A developer sends one offline artifact to another developer for diagnosis.

## Confirmed initial exclusions

- Broader end-user or production operation is outside the initial product boundary.
- Nested tracer activation is unsupported and remains subject to explicit rejection
  under SYS-004.
- V1 assumes the process remains single-threaded throughout the trace context; the tracer
  need not detect a violation of this input assumption.
- V1 likewise assumes snapshot, printer, and metadata-representation hooks do not invoke
  public rewrites or specialized handlers; the tracer need not detect a violation.
- V1 explicitly rejects activation when the current thread already has an installed
  profile function. Once active, v1 assumes no code replaces its profile function and
  need not detect a violation.
- V1 retains a neutral incomplete event when a supported recorded rewrite frame exits
  without returning a `RewriteResult`. The generic profiler does not classify that exit
  as either an exception or an explicit nonconforming return.
- Exact deletion effects are initially limited to normally completed
  `Statement.delete` calls. Other entity deletion and detach paths have no effect of
  their own; any selected calls they dynamically invoke remain captured. No effect is
  inferred from snapshot disappearance.
- Kirin `SourceInfo` and other original-program source metadata remain outside the
  current snapshot inventory; invocation stacks and exact entity provenance are
  covered separately by SYS-012 through SYS-017.
