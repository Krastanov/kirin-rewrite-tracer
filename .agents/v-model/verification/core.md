# Core Verification and Acceptance Actions

## ACC-001 — Demonstrate rewrite-effect inspection

- **Covers:** STK-001
- **Method:** demonstration
- **Procedure:** In the confirmed operational environment, trace developer-approved
  deterministic structural, style-distinct, and metadata-only rewrite scenarios,
  retrieve their recorded pairs, and compare their SSA, styled presentation, complete
  declared metadata inventory, owner associations, ordering, and attribution with
  independently known values.
- **Environment / configuration:** Local Python debugging or test process using Kirin
  commit `7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a`, Rich 15.0.0, and the declared default
  rendering configuration within the SYS-002 support envelope.
- **Pass criterion:** The acceptance authority retrieves attributable ordered pairs
  matching the known states, can inspect every expected metadata value on its correct
  side and owner, observes every expected style association on the correct text, and can
  identify the metadata-only difference.
- **Status:** implemented
- **Evidence:** [Acceptance handoff](../evidence/acceptance-handoff.md#approved-fixtures-and-runners)
- **Nonconformance:** Developer review remains pending.

## SYSV-001 — Verify paired state capture

- **Covers:** SYS-001
- **Method:** test
- **Procedure:** Exercise every declared-supported trace event category with
  deterministic fixtures that collectively contain changed and no-op wrapper and leaf
  occurrences. Compare each captured pair and its attribution against independently
  established input and result states.
- **Environment / configuration:** Local Python test process using Kirin commit
  `7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a` within the SYS-002 support envelope, with
  one non-nested trace in an isolated process that remains single-threaded.
- **Pass criterion:** For every exercised supported category, the trace contains an
  attributable ordered pair whose first state equals the fixture input and whose second
  state equals the rewrite result; no-op pairs contain two equal copies of the
  independently known unchanged state.
- **Status:** implemented
- **Evidence:** [Source/wheel audit](../evidence/source-and-wheel-verification.md#action-audit)
- **Nonconformance:** Nested pairs lack independent full-payload oracles.

## SYSV-002 — Verify the v1 support envelope

- **Covers:** SYS-002
- **Method:** test
- **Procedure:** Across CPython 3.10–3.13, run the proved Kirin/Rich pins, declared
  printer defaults, pure capture/representation hooks, terminating pure caller
  representations, empty profile slot, one nonnested single-threaded process, lifetime
  assumptions, and five raw descriptors. Observe profile ownership for normal and body
  exception exits, then attempt entry with a sentinel profile. Prove Kirin separately
  through PEP 610 and clean exact Git. Vary out-of-range runtime, revision, dirtiness,
  missing provenance, Rich, every descriptor, theme, indentation, inline hint, printer
  analysis, highlighter, and nesting.
- **Environment / configuration:** Isolated single-threaded CPython 3.10, 3.11, 3.12,
  and 3.13 source and installed-distribution processes with controlled PEP 610 and local
  Git provenance, Rich 15.0.0, and supported and unsupported configurations.
- **Pass criterion:** The supported configuration can run tracing, owns the profile slot
  only during each context, and restores it to `None` after both normal and exceptional
  exit. Entry with the sentinel installed fails before activation and leaves the same
  sentinel installed. Every other varied configuration is classified outside the
  support envelope before activation; fingerprints alone never prove the Kirin commit.
  No diagnostic behavior is asserted for a violated input assumption, and cleanup does
  not clobber a foreign profile or descriptor replacement.
- **Status:** implemented
- **Evidence:** [Source/wheel audit](../evidence/source-and-wheel-verification.md#action-audit)
- **Nonconformance:** The complete configuration variation is not durable.

## SYSV-003 — Verify observational transparency

- **Covers:** SYS-003
- **Method:** test
- **Procedure:** Run equivalent successful, mutating, no-op, nested-wrapper, and raising
  rewrite fixtures with and without tracing, then compare results, propagated
  exceptions, final statement order and parents, SSA-use targets, metadata, and
  normalized styled snapshots.
- **Environment / configuration:** Local Python test process using Kirin commit
  `7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a` within the SYS-002 support envelope.
- **Pass criterion:** Every successful traced fixture returns the same result object as
  its untraced counterpart; every raising fixture propagates the same preconstructed
  exception object; and every final statement order, parent, SSA-use target, metadata
  record, and normalized styled snapshot matches its explicit oracle.
- **Status:** implemented
- **Evidence:** [Source/wheel audit](../evidence/source-and-wheel-verification.md#action-audit)
- **Nonconformance:** No one fixture compares every transparency clause.

## SYSV-004 — Verify unsupported-use rejection

- **Covers:** SYS-004, SYS-006, SYS-007, SYS-010
- **Method:** test
- **Procedure:** Exercise all declared unsupported rules, configurations,
  representation/style-meta values, and output paths, including unformable type labels,
  both text paths failing, an occupied profile, and an unsupported child. Run synthetic
  and pinned `ScfToCfRule` cross-instance specialized bypasses on valid printable
  `For`/`IfElse` nodes; keep hostile representation values outside root rendering.
  Verify trace/export denial, caught-normal and later-exception identity, malformed
  public frames, and resumed generator/coroutine/async-generator bodies. Construct but
  do not execute equivalent deferred callables.
- **Environment / configuration:** Local Python test process using controlled unsupported
  rules, configurations, metadata values, and presentation paths around the pinned Kirin
  checkout; supported portions of each fixture remain within the SYS-002 input
  assumptions.
- **Pass criterion:** Every exercised category explicitly signals failure, no required
  activity or snapshot information is silently omitted, and no partial trace or export
  is exposed. Caught unsupported use reappears on normal exit as the same error object;
  the later body exception instead propagates by identity. Observable nonordinary frames
  invalidate, while never-executed deferred callables establish no rejection claim.
- **Status:** failing
- **Evidence:** [Detector counterexample](../evidence/detector-portability-inspection.md#executable-invalid-self-counterexample)
- **Nonconformance:** An invalid-`self` direct override freezes a complete empty trace.

## SYSV-010 — Verify ordinary public-entry compatibility

- **Covers:** SYS-010
- **Method:** test
- **Procedure:** Maintain an independent public-entry and specialized-handler log.
  Invoke one inherited probe rule on a region, block, and statement; an ordinary direct
  override; and an override that delegates explicitly to `super().rewrite(node)`.
  Separately invoke a direct override declared after trace activation, a method bound
  before activation, and an unbound class function.
  Exercise the pinned `Walk`, `Fixpoint`, `Chain`, `CompactifyRegion`, aggressive
  `Fold`, and `WalkDesugarBinop` deterministic fixtures with inherited sentinels as
  defined by the Kirin integration reference. Verify same-instance specialized dispatch
  through base `rewrite()` creates no handler event and classify from runtime frames and
  values, never annotations.
- **Environment / configuration:** Isolated CPython 3.10 through 3.13 test processes that
  remain single-threaded, using the SYS-002 revisions and configuration. The vmath case
  runs unskipped
  through the sibling `kirin/` environment prepared with `uv sync --extra vmath`, unless
  the tracer later declares an equivalent pinned test dependency.
- **Pass criterion:** Every logged public rewrite frame creates exactly one event with
  the correct concrete rule type and dynamic parent, including both frames in the
  superclass-delegation case; no specialized-handler frame creates an event; every call
  returns normally with the expected `RewriteResult` runtime type and fields; and no
  other event appears.
- **Status:** passing
- **Evidence:** [Source/wheel audit](../evidence/source-and-wheel-verification.md#action-audit)
- **Nonconformance:** None
