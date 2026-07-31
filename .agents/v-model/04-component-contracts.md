# Component Contracts

## CMP-001 — Allocate IDs and freeze validated facts

- **Normative statement:** Allocate zero-based monotonic IDs with stable domain prefixes,
  retain strong object identity only while building, validate every reference, owner,
  ordinal, parent cycle, outcome, and complete/incomplete after-state rule, then freeze
  recursively and release the live registry.
- **Parents:** SUB-003
- **Acceptance criterion:** Allocation yields `event-0`, `entity-0`, and noncolliding
  domains without persisted `id()`; every isolated malformed case fails; valid output is
  deeply immutable and registry-only sentinels are collectible.
- **Verification:** UNITV-001 (test)

## CMP-002 — Normalize styles, metadata, and equality

- **Normative statement:** Freeze Rich styles and metadata immediately, distinguish
  `None` from explicit false, preserve ordered typed maps, and reject cycles, controls,
  non-string keys, unsafe integers, nonfinite floats, and unsupported values. Preserve
  absent-name, omitted-analysis, supplied-falsey, qualified-type, exact-text, and
  printable/`repr` states. Snapshot equality expands style IDs to code-point
  associations, coalesces equal adjacent associations, and excludes only record and
  event/state binding identity.
- **Parents:** SUB-003, SUB-004
- **Acceptance criterion:** Supported values preserve type/order/state; unsupported
  values fail; equivalent style encodings compare equal and every semantic near-miss
  compares unequal.
- **Verification:** UNITV-002 (test)

## CMP-003 — Attribute one pinned printer execution

- **Normative statement:** Observe one outer root execution, delegate every emission,
  retain only guarded outer-sink `Console.out`, and reject visible bypass. Preserve
  tagged SSA/block IDs and aligned result spans through hidden measurement. Mark pinned
  result, block-argument, `scf.For`, function-ID, root, region, block, statement, and
  nested-container intervals; register external defining owners; reject controls and
  overlapping interactive roles.
- **Parents:** SUB-004
- **Acceptance criterion:** Multi-result, block, loop, function, module, external,
  repeated, hidden-width, non-BMP, control, overlap, and bypass fixtures exactly match
  independent tags or fail, with one root evaluation.
- **Verification:** UNITV-003 (test)

## CMP-004 — Reduce profiler callbacks in strict LIFO order

- **Normative statement:** Accept only exact active-session callbacks; classify through
  the permitted documented surface; push after before-capture; and finalize/pop only the
  matching innermost event. `RewriteResult` completes; every other public return is
  neutral incomplete. Malformed, mismatched, out-of-order, cross-instance, or unsupported
  callbacks atomically invalidate through the session's one stored
  `UnsupportedTraceError`, without constructing a second callback error.
- **Parents:** SUB-001, SUB-002
- **Acceptance criterion:** Valid nested/super/root/no-op/incomplete streams produce the
  exact tree; every malformed stream produces one sticky invalidation and no partial
  trace or misnesting.
- **Verification:** UNITV-004 (test)

## CMP-005 — Authorize one saved mutation delegation

- **Normative statement:** Each wrapper creates one nonreusable expected-call token
  around exact saved delegation; the profiler consumes it on one matching code and
  receiver/class entry. Absence, reuse, mismatch, or pre-bound bypass invalidates.
  Preserve instance and dynamic `Statement.from_stmt` classmethod binding; outside-event
  calls delegate without operations.
- **Parents:** SUB-002, SUB-005
- **Acceptance criterion:** All five descriptors pass direct/inherited/nested/outside/
  subclass/exception cases once; token anomalies invalidate; partial installation and
  reverse cleanup restore only exact wrappers.
- **Verification:** UNITV-005 (test)

## CMP-006 — Copy stacks without retaining frames

- **Normative statement:** Traverse the full documented stack outermost first, copy only
  filename, integer line, and function, and omit only exact tracer code identities.
  Perform no source lookup, local capture/`repr`, traceback classification, arbitrary
  truncation, or retention of frames, tracebacks, summaries, or locals.
- **Parents:** SUB-005
- **Acceptance criterion:** CPython 3.10–3.13 chains match code/callsite oracles at tested
  depth; hostile locals/source are untouched; incomplete stacks are not tracebacks; and
  frame-local sentinels are collectible.
- **Verification:** UNITV-006 (test)

## CMP-007 — Rebuild provenance and presentation indexes

- **Normative statement:** Derive event children, occurrences, one-based lines,
  relation/effect endpoint queries, operations by event, identity matches, and unmatched
  status solely from canonical facts. Reverse lookup returns the same directed fact;
  discard/rebuild neither mutates facts nor changes results.
- **Parents:** SUB-003, SUB-005, SUB-007
- **Acceptance criterion:** Identity, arbitrary-cardinality, repeated, transient,
  deletion, incomplete, absent, and unrelated cases match independent results across
  rebuilds with no inverse copy, heuristic match, or line pairing.
- **Verification:** UNITV-007 (test)

## CMP-008 — Encode trace primitives as inert document data

- **Normative statement:** Accept explicit validated primitives, preserve ordered maps
  without prototype-bearing merges, reject unsupported/nonfinite values, and escape raw
  text before embedding. Use text nodes, nonce CSP, one classic script, one cascade plus
  validated Rich classes, and Python-derived code-point runs. No trace string becomes
  markup, selector, declaration, URL, handler, or code.
- **Parents:** SUB-006
- **Acceptance criterion:** Hostile strings/keys, non-BMP intervals, styles, and invalid
  primitives remain exact inert content or fail; CSP, DOM, console, request, and
  execution sentinels observe no interpreted trace content or request.
- **Verification:** UNITV-008 (test)

## CMP-009 — Reduce selection and columns purely

- **Normative statement:** From canonical events and `(frontier, anchor)`, produce the
  next ancestor-free ordered state without mutation, using pre-action rows for Shift and
  later parent dominance. Clear returns empty/null. Columns preserve logical roles,
  share exactly equal `A.after`/`B.before`, treat absent after as a barrier, and never
  share own-event states or compose handoffs.
- **Parents:** SUB-007
- **Acceptance criterion:** Table-driven click/modifier/range/swallow/restore/Clear and
  complete/incomplete/equality/near-miss cases match immutable expected states.
- **Verification:** UNITV-009 (test)

## CMP-010 — Reduce overlays, candidates, and focus

- **Normative statement:** Retain at most one exact overlay anchor and most-recent active
  provenance candidate; apply prescribed replacement/dismissal precedence; invalidate
  active/suspended state when control, occurrence, or role tuple disappears. Return
  focus to a surviving anchor only for focused-region removal, preserve newly focused
  outside controls and Clear focus, and never revive recreated equal state.
- **Parents:** SUB-007, SUB-008
- **Acceptance criterion:** Click, Escape, scroll, resize, removal, role transition,
  candidate arbitration, detached focus, Clear, and recreation sequences yield one
  settled state, exact focus, and no stale state.
- **Verification:** UNITV-010 (test)
