# Component Verification Actions

## UNITV-001 — Verify ID allocation and deep freeze

- **Covers:** CMP-001
- **Method:** test
- **Procedure:** Allocate every domain around object-ID reuse; freeze valid graphs; inject
  each broken reference, cycle, ordinal, owner, outcome, and after-state error; mutate
  every depth and weakly reference registry-only objects.
- **Environment / configuration:** Pure CPython 3.10–3.13 tests.
- **Pass criterion:** IDs have exact monotonic prefixes and no `id()`; malformed graphs
  fail; valid output is deeply immutable and releases registry objects.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None

## UNITV-002 — Verify style, metadata, and equality normalization

- **Covers:** CMP-002
- **Method:** test
- **Procedure:** Normalize every allowed nested/falsey/ordered value and metadata state;
  reject cycles, controls, invalid keys, unsafe numbers, nonfinite floats, and objects;
  compare alternate style encodings and one-field snapshot near-misses.
- **Environment / configuration:** Pure tests with transient Rich 15.0.0 styles.
- **Pass criterion:** Supported types/order/states remain exact, invalid values fail,
  effective-style equivalents compare equal, and every semantic difference does not.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None

## UNITV-003 — Verify owner-aware pinned printing

- **Covers:** CMP-003
- **Method:** test
- **Procedure:** Instrument multi-result, block, `scf.For`, function, module, external,
  repeated, hidden-width, non-BMP, control, overlap, and bypass cases and count root
  execution.
- **Environment / configuration:** Pinned Kirin/Rich on every supported CPython minor.
- **Pass criterion:** One execution yields exact tagged text/roles/owners/code-point
  intervals; external owners register; unsupported controls/overlaps/bypasses fail.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None

## UNITV-004 — Verify strict profiler LIFO reduction

- **Covers:** CMP-004
- **Method:** test
- **Procedure:** Feed valid nested/root/complete/incomplete callback streams, then inject
  missing/wrong locals, code, receiver, session, order, and duplicate returns.
- **Environment / configuration:** Documented callback shapes on CPython 3.10–3.13.
- **Pass criterion:** Valid streams produce the exact tree and empty stack; every
  malformed stream causes one sticky invalidation, no partial trace, and no misnesting.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None

## UNITV-005 — Verify one-shot mutation delegation tokens

- **Covers:** CMP-005
- **Method:** test
- **Procedure:** Invoke all five wrappers direct/inherited/nested/outside/subclass and
  inject missing, duplicate, wrong-code/receiver/class, reused, pre-bound, exception,
  partial-install, and foreign-replacement cases.
- **Environment / configuration:** Pinned raw descriptors in isolated supported CPython.
- **Pass criterion:** Ordinary calls consume once and preserve binding/result/exception;
  outside calls add no operation; anomalies invalidate; rollback never clobbers.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None

## UNITV-006 — Verify frame-free portable stacks

- **Covers:** CMP-006
- **Method:** test
- **Procedure:** Capture shallow/deep event/mutation chains with marked callsites, failing
  source lookup, hostile local `repr`, lifetime sentinels, and incomplete records.
- **Environment / configuration:** Identical fixtures on CPython 3.10, 3.11, 3.12, 3.13.
- **Pass criterion:** Exact outer-first three-field frames have no arbitrary truncation,
  source/local access, traceback claim, or retained lifetime sentinel.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None

## UNITV-007 — Verify disposable provenance indexes

- **Covers:** CMP-007
- **Method:** test
- **Procedure:** Query identity, arbitrary-cardinality, repeated, transient, deletion,
  incomplete, absent, multiline, and unrelated facts, then repeatedly discard/rebuild.
- **Environment / configuration:** Pure immutable trace fixtures.
- **Pass criterion:** All endpoint/operation/event/line/unmatched queries match canonical
  IDs before/after rebuild with no inverse, heuristic, pair, or mutation.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None

## UNITV-008 — Verify inert primitive encoding

- **Covers:** CMP-008
- **Method:** test
- **Procedure:** Encode hostile raw-text/markup/handler/URL/CSS/Unicode/`__proto__`
  strings, non-BMP runs, every Rich input, and invalid primitives; inspect CSP, DOM,
  styles, console, execution sentinel, and requests.
- **Environment / configuration:** Source/built assets in pinned offline headed Chrome.
- **Pass criterion:** Supported values remain exact inert data and code-point-safe;
  invalid values fail; no trace value becomes active content or request.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None

## UNITV-009 — Verify pure selection and column reduction

- **Covers:** CMP-009
- **Method:** test
- **Procedure:** Table-drive initial Shift, non-toggle plain/modifier/range,
  expand/contract, swallowed/restored, Clear, complete/incomplete, equal/near-miss, and
  no-op-middle cases over frozen inputs.
- **Environment / configuration:** Pure deterministic reducer tests.
- **Pass criterion:** Frontier/anchor/rows/roles match pre-action oracles; Clear is
  empty/null; sharing is exact, two-role, nontransitive, and never crosses absent after.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None

## UNITV-010 — Verify overlay, candidate, and focus reduction

- **Covers:** CMP-010
- **Method:** test
- **Procedure:** Interleave click, Escape, scroll, resize, removal, role transition,
  Clear, recreation, pointer/keyboard candidates, and focused-region fallback.
- **Environment / configuration:** Pure exact-identity interaction fixtures.
- **Pass criterion:** Each input yields at most one overlay/preview, exact candidate
  precedence and focus including Clear, and no detached or revived stale state.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None
