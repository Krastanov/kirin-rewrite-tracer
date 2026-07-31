# Subsystem Integration Verification

## INTV-001 — Verify transactional recorder lifecycle

- **Covers:** SUB-001
- **Method:** test
- **Procedure:** Drive fresh recorders through normal, active-access, supported-exception,
  repeated-frozen, unsupported caught/uncaught, and later-exception cases. Mutate caller
  analysis after entry and weakly reference every live-only capture category.
- **Environment / configuration:** Isolated supported CPython processes under SUB-002.
- **Pass criterion:** Every state, trace/error/result identity, denial, analysis-copy,
  falsey-value, cleanup, and collectability result exactly matches SUB-001.
- **Status:** passing
- **Evidence:** [Source and wheel action audit](../evidence/source-and-wheel-verification.md#action-audit)
- **Nonconformance:** None

## INTV-002 — Verify compatibility preflight and rejection

- **Covers:** SUB-002
- **Method:** test
- **Procedure:** On CPython 3.10–3.13, vary runtime, Rich, PEP 610/clean-Git Kirin proof,
  revision/dirtiness, profile, nesting, and each raw descriptor. Execute every observable
  malformed, bypass, deferred-body, and unrepresentable path; leave assumption cases
  unexecuted/unobservable.
- **Environment / configuration:** Source and installed distributions with controlled
  dependencies, Git metadata, descriptors, and profile slot.
- **Pass criterion:** Only the exact supported configuration activates; every invalid
  preflight leaves no installation; each observable unsupported path invalidates without
  a trace; fingerprints and assumption cases establish no support claim.
- **Status:** failing
- **Evidence:** [Detector portability inspection and executable counterexample](../evidence/detector-portability-inspection.md#executable-invalid-self-counterexample)
- **Nonconformance:** The observable invalid-`self` direct-override path completes
  without invalidation and exposes a complete empty trace.

## INTV-003 — Verify immutable canonical trace integration

- **Covers:** SUB-003
- **Method:** test
- **Procedure:** Freeze valid all-domain traces; mutate every depth; inject each reference,
  cycle, ordinal, owner, outcome, and after-state error; force object-ID reuse; compare
  normalized equality near-misses; repeatedly rebuild all indexes.
- **Environment / configuration:** Pure model tests on every supported CPython minor.
- **Pass criterion:** Valid traces freeze/release deeply; every malformed graph fails;
  IDs never use process identity; external owners persist; equality and rebuilt reverse,
  line, identity, and unmatched queries match independent oracles.
- **Status:** implemented
- **Evidence:** [Source and wheel action audit](../evidence/source-and-wheel-verification.md#action-audit)
- **Nonconformance:** Forced object-ID reuse and every graph/equality/index injection are
  not all exercised as one complete integration procedure.

## INTV-004 — Verify pinned snapshot capture integration

- **Covers:** SUB-004
- **Method:** test
- **Procedure:** Capture multi-result, block, `scf.For`, function, nested-module,
  external, repeated, hidden-width, non-BMP, analysis-state, hostile-meta, control,
  interval-overlap, and output-bypass fixtures with independent printer/IR tags.
- **Environment / configuration:** Supported CPython matrix, pinned Kirin, Rich 15.0.0,
  and declared printer defaults.
- **Pass criterion:** One root execution yields exact Unicode, styles, roles, owners,
  metadata distinctions, and code-point runs; every unsupported path invalidates with no
  partial trace.
- **Status:** implemented
- **Evidence:** [Source and wheel action audit](../evidence/source-and-wheel-verification.md#action-audit)
- **Nonconformance:** The full instrumented capture-path inventory is not executed with
  independent printer/IR tags on every supported minor.

## INTV-005 — Verify mutation and stack transaction integration

- **Covers:** SUB-005
- **Method:** test
- **Procedure:** Exercise all five APIs directly/nested/outside events with zero-use,
  transient, reinsertion, incomplete-parent/completed-child, subclass classmethod,
  pre-bound bypass, per-step install failure, foreign replacement, and hostile-stack
  fixtures.
- **Environment / configuration:** Isolated CPython 3.10–3.13 processes with pinned raw
  descriptors.
- **Pass criterion:** Operations, facts, hierarchy, stacks, binding, and result/exception
  identity match independent logs; bypass invalidates; outside calls add no operation;
  rollback/restoration never clobbers; retained stacks keep no frame live.
- **Status:** passing
- **Evidence:** [Source and wheel action audit](../evidence/source-and-wheel-verification.md#action-audit)
- **Nonconformance:** None

## INTV-006 — Verify atomic no-overwrite publication

- **Covers:** SUB-006
- **Method:** test
- **Procedure:** Export empty/complete/incomplete traces; relocate and open offline.
  Exercise missing parent, existing/raced target, and failures at encoding, write, flush,
  close, and publication while inventorying files and source-trace hashes.
- **Environment / configuration:** Supported CPython filesystem tests and pinned headed
  Chrome with network denied.
- **Pass criterion:** Success returns one autonomous file without mutation/request;
  invalid targets and failures preserve existing bytes and leave no target or temporary
  file; hostile content remains inert.
- **Status:** failing
- **Evidence:** [Publication counterexample and pinned browser run](../evidence/browser-verification.md#known-nonconformances)
- **Nonconformance:** If final publication creates the destination and then raises, the
  export reports failure but leaves the target; this violates the no-target-on-failure
  pass criterion.

## INTV-007 — Verify canonical viewer projection

- **Covers:** SUB-007
- **Method:** test
- **Procedure:** Apply event/column/provenance/facts reducers to every click, modifier,
  range, swallow, Clear, equality near-miss, barrier, cardinality, descendant, shared-side,
  nonneighbor, unmatched, and two-edge fixture.
- **Environment / configuration:** Pure reducers and the pinned offline browser over the
  same immutable canonical fixtures.
- **Pass criterion:** Every frontier, anchor, row, column, edge, and highlight matches
  independent oracles; Clear restores zero state; selected facts contain exactly owned
  fields/absences and never copied descendant facts; canonical input is unchanged.
- **Status:** implemented
- **Evidence:** [Source/wheel](../evidence/source-and-wheel-verification.md#action-audit)
  and [browser](../evidence/browser-verification.md#action-audit) action audits
- **Nonconformance:** The complete reducer cross-product and every metadata-schema
  near-miss/interleaving are not covered by one clause-complete durable action.

## INTV-008 — Verify accessibility and fixed presentation

- **Covers:** SUB-008
- **Method:** test
- **Procedure:** Inspect native DOM/accessibility order, keyboard/pointer parity, Clear,
  fallback, overlays, candidates, announcements, computed styles, contrast, and Rich
  projection at both zooms and boundary/varied larger viewports; label smaller samples
  excluded.
- **Environment / configuration:** Pinned headed Chrome/Xvfb with accessibility-tree and
  offline request monitoring.
- **Pass criterion:** Native semantics, focus/state, cues/styles, and announcements match
  oracles; all supported layouts remain consecutive, unwrapped, reachable, and operable;
  no smaller-viewport result is represented as support.
- **Status:** failing
- **Evidence:** [Large-viewport analysis and pinned-Blink counterexample](../evidence/sysv-025-layout-invariant.md)
- **Nonconformance:** Valid unbounded snapshot text exceeds pinned Blink's scroll extent
  at both zooms, leaving a later nonzero control unreachable and inoperable.
