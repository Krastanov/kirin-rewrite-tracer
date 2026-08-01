# Subsystem and Interface Contracts

These are logical boundaries, not package or file topology.

## SUB-001 — Own one transactional tracing session

- **Normative statement:** The public session shall expose `trace_rewrites`,
  `TraceRecorder`, `TraceStateError`, and `UnsupportedTraceError`. Each recorder is
  one-shot: `CREATED → ACTIVE → FROZEN` or `CREATED/ACTIVE → INVALID`. Active trace
  access raises `TraceStateError`; frozen access always returns the same immutable trace.
  A supported body exception freezes before propagating by identity. Unsupported use
  stores and raises one error, atomically denies trace/export, re-raises that object after
  a caught error and normal body exit, but never replaces a later body exception. Entry
  shallow-copies analysis; every terminal state releases live capture objects.
- **Parents:** SYS-002, SYS-003, SYS-004, SYS-008, SYS-015
- **Acceptance criterion:** Normal, exceptional, caught-unsupported, later-exception,
  repeated-access, analysis-mutation, falsey-analysis, and weak-reference fixtures match
  every state, object-identity, denial, and release rule.
- **Verification:** INTV-001 (test)

## SUB-002 — Preflight the pinned compatibility boundary

- **Normative statement:** Before activation, require CPython `>=3.10,<3.14`, Rich
  15.0.0, no active/nested session, an empty profile slot, the five expected raw
  descriptors, and exact Kirin commit
  `7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a` proved by PEP 610 VCS provenance or a
  clean exact Git checkout, never fingerprints. Observable malformed public frames,
  specialized dispatch observed with no open recorded invocation, unauthorized
  saved-mutator entry, executed
  generator/coroutine/async-generator rewrites, and unrepresentable capture invalidate.
  Unexecuted deferred and unobservable C/custom descriptors are input assumptions.
- **Parents:** SYS-002, SYS-004, SYS-010, SYS-011, SYS-012
- **Acceptance criterion:** The CPython 3.10–3.13 matrix accepts only the exact supported
  configuration, rejects every varied preflight before installation, invalidates each
  observable unsupported execution without a trace, and makes no claim for assumption
  cases.
- **Verification:** INTV-002 (test)

## SUB-003 — Freeze one canonical trace fact model

- **Normative statement:** A completed session shall detach into deeply immutable
  records, tuples, and validated scalars with opaque domain-prefixed monotonic IDs and no
  persisted `id()`. Each fact has one canonical owner/copy. Entities retain kind,
  qualified type, and an SSA defining-owner ID, including external owners. Whole-trace
  validation rejects broken references, cycles, ordinals, ownership, and illegal state
  combinations. Disposable indexes rebuild reverse, line, identity, and unmatched
  queries. Snapshot equality compares every normalized payload field except record and
  event/state binding identity, expanding and coalescing equal effective styles; it is
  not a general IR diff.
- **Parents:** SYS-001, SYS-005, SYS-006, SYS-007, SYS-008, SYS-009, SYS-012, SYS-013,
  SYS-014, SYS-015, SYS-016, SYS-017
- **Acceptance criterion:** Valid empty, complete, and incomplete traces freeze deeply;
  malformed traces fail; object-ID reuse does not merge entities; index rebuilds preserve
  results; normalized-style equivalents compare equal and every semantic near-miss does
  not.
- **Verification:** INTV-003 (test)

## SUB-004 — Capture renderer-neutral owner-aware snapshots

- **Normative statement:** Capture shall evaluate pinned root output once; retain exact
  Unicode, Rich 15.0.0 effective styles, occurrences, metadata, owners, and configuration;
  and discard live renderer objects. It guards the outer `Console.out` sink, excludes
  hidden measurement while preserving aligned tagged IDs, distinguishes result,
  block-argument and `scf.For` definitions, and scopes root/region/block/statement/nested
  containers. Metadata distinguishes absent names, omitted analysis, and supplied falsey
  analysis and records qualified type, exact text, and printable/`repr` path. Controls,
  unsafe/cyclic style metadata, unsupported keys, and overlapping interactive intervals
  invalidate. Python derives Unicode code-point-safe render runs.
- **Parents:** SYS-001, SYS-004, SYS-005, SYS-006, SYS-007, SYS-013
- **Acceptance criterion:** Multi-result, block, loop, function, nested-module, external,
  repeated-label, hidden-width, hostile, bypass, and non-BMP fixtures exactly match
  independent text/style/owner/metadata/run oracles or invalidate without partial trace.
- **Verification:** INTV-004 (test)

## SUB-005 — Record exact mutations and invocation stacks

- **Normative statement:** Transactional wrappers for the five raw descriptors shall
  preserve dynamic binding and record ordered operation shells, parents, operands,
  outcomes, exact relations/effects, and stacks. Each delegation authorizes one matching
  saved-code entry; unauthorized entry invalidates, while calls outside an event only
  delegate. Partial install and reverse cleanup restore only exact tracer objects and
  never clobber foreign replacements. Stacks copy only filename, line, and function,
  outermost first, omit exact tracer code identities, have no arbitrary limit, and retain
  no frames, tracebacks, locals, source, or representations.
- **Parents:** SYS-003, SYS-004, SYS-012, SYS-014, SYS-015, SYS-016, SYS-017
- **Acceptance criterion:** All five APIs, nesting, zero-use, transient, reinsertion,
  incomplete-child, outside-event, rollback, bypass, restoration, and lifetime fixtures
  match independent operation and stack oracles while preserving result/exception
  identity.
- **Verification:** INTV-005 (test)

## SUB-006 — Publish one inert autonomous HTML artifact

- **Normative statement:** `export_html(trace, destination)` shall return the published
  path, require a valid immutable trace, existing parent, and nonexistent target, and
  raise `FileExistsError` rather than overwrite. Same-directory atomic no-clobber
  publication leaves no temporary artifact on failure and never mutates the trace. The
  one file contains only inert validated primitives and every required resource and
  initiates no auxiliary/network request.
- **Parents:** SYS-004, SYS-018, SYS-019
- **Acceptance criterion:** New-target exports relocate and operate offline unchanged;
  missing-parent, existing/raced-target, and injected I/O failures preserve existing
  bytes and leave no target or temporary artifact; hostile strings remain inert.
- **Verification:** INTV-006 (test)

## SUB-007 — Derive viewer projection from canonical facts

- **Normative statement:** Pure derived state shall implement the parent-dominant
  non-toggle frontier and pre-action Shift ranges; always-available Clear empties
  frontier/anchor, clears derived state, and restores rows. One independent collapse
  state hides non-leaf subtrees, composes with parent dominance as a union that never
  reveals, and admits a transition only for a displayed non-leaf event whose subtree
  holds no selected event. Columns preserve logical
  roles, exact two-role handoffs, absent barriers, and nontransitive equality. Provenance
  uses rebuilt indexes, exact identity/one-hop edge policy, both directions, side-isolated
  shared columns, and unmatched endpoints. The always-visible selected-event facts
  region exposes every owned field/absence without copying descendant facts to a parent.
- **Parents:** SYS-019, SYS-020, SYS-021, SYS-022, SYS-025
- **Acceptance criterion:** All click/range/Clear, collapse-eligibility, equality,
  barrier, neighbor, shared, unmatched, and ownership fixtures match independent
  reducers; zero selection names no event and each selection exposes exactly its
  canonical inventory.
- **Verification:** INTV-007 (test)

## SUB-008 — Preserve accessibility, focus, and fixed presentation

- **Normative statement:** Native event, occurrence, collapse, skip, and Clear controls;
  labelled workspace and facts; polite status; and one nonmodal metadata region shall
  share reducers across pointer/keyboard input. Clear and collapse keep focus; removal
  uses deterministic
  fallback and discards stale overlay/provenance state. A natively disabled collapse
  control leaves sequential focus order and rejects every activation. One fixed cascade
  preserves SYS-024 contrast, non-color cues, Rich projection, and consecutive no-wrap
  scrolling. V1 supports measured CSS viewports at least `640 × 480` at 100%/200% zoom
  and makes no claim below either dimension.
- **Parents:** SYS-020, SYS-022, SYS-023, SYS-024, SYS-025
- **Acceptance criterion:** Native-order, parity, Clear, collapse-eligibility, fallback,
  overlay/candidate, style/contrast, boundary, and varied larger-viewport oracles pass
  without detached state, wrapping, clipping, reordering, or below-floor support claims.
- **Verification:** INTV-008 (test)
