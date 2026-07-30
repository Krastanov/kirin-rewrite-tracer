# Rewrite Compatibility Requirements

V1 has a shape-based public-entry support category. The pinned Kirin overrides are
compatibility fixtures, not a production allowlist. Its detector is constrained to
documented, minor-version-generic Python interfaces, while handling of other callable
forms and the exact supported interpreter range remain unspecified.

## SYS-002 — Bound the v1 support envelope

- **Normative statement:** The v1 product shall support tracing only against Kirin commit
  `7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a` with Rich 15.0.0, using the pinned Kirin
  printer's dark theme, indentation marks, no selected inline hint or printer analysis,
  and Rich default highlighter. Caller analysis admitted by SYS-005 shall be treated only
  as snapshot metadata and shall not alter that rendering configuration. V1 shall support
  one active, non-nested trace only when `sys.getprofile()` is `None` at trace-context
  entry and shall explicitly reject entry otherwise without replacing the installed
  profile function. On every context exit that satisfies the input assumptions it shall
  restore `sys.getprofile()` to `None`. After successful entry, two lifetime properties
  are input assumptions: the process remains single-threaded and no code replaces the
  tracer's active profile function through exit. The absence of any public `rewrite()`
  or specialized `rewrite_Region`,
  `rewrite_Block`, or `rewrite_Statement` invocation from snapshot, printer, or
  metadata-representation hooks, and the absence of a SYS-012 selected mutation call
  from those hooks, are also input assumptions. Metadata `Printable.print_str()` and
  `repr()` hooks terminate and remain observationally pure with respect to the traced
  IR. Code executing during the context neither replaces the selected mutation
  descriptors nor branches on their identity or on tracer-added call frames. The
  product is not required to detect an input-assumption violation.
- **Parents:** STK-001, STK-002, STK-003
- **Acceptance criterion:** Given the pinned Kirin and Rich revisions, declared printer
  configuration whose snapshot and printer hooks and every invoked
  metadata-representation hook satisfy the no-rewrite and no-selected-mutation
  assumptions, optional
  caller-analysis metadata whose invoked `Printable.print_str()` and `repr()` hooks also
  terminate and are observationally pure, `sys.getprofile()` equal to `None`, one trace
  context, no behavioral inspection or replacement of selected mutation descriptors or
  tracer-added frames, and a process satisfying the lifetime assumptions, tracing can
  run; both a
  normal exit and an exit caused by a body exception restore the profile slot to `None`.
  Entry with an installed profile function explicitly fails before activation and leaves
  that function installed. Another Kirin or Rich revision, non-default theme,
  indentation, inline hint, printer analysis, highlighter, or nested activation is
  outside the supported configuration; a run violating an input assumption has no
  guaranteed tracer behavior or diagnostic.
- **Verification:** SYSV-002 (test)
- **Origin / risk:** Confirmed developer interviews, 2026-07-29 and 2026-07-30; narrow
  v1 compatibility is preferred over guessed behavior.
- **Context:** [Kirin integration reference](../../context/kirin-integration.md)

## SYS-004 — Reject unsupported tracing use

- **Normative statement:** The product shall explicitly signal failure for every rule,
  tracing configuration, required snapshot-value representation category, or
  presentation path that it declares unsupported, instead of silently omitting activity
  or information or presenting an incomplete trace as complete. This obligation does
  not apply to violations of the input assumptions explicitly declared in SYS-002.
- **Parents:** STK-001, STK-002
- **Acceptance criterion:** Given every declared unsupported category other than a
  SYS-002 input-assumption violation, including each declared unsupported required-value
  representation and presentation path, tracing explicitly signals failure, omits no
  information from a trace reported as successful, and does not report any partial trace
  as complete.
- **Verification:** SYSV-004 (test)
- **Origin / risk:** Confirmed developer interview, 2026-07-29; silent incompleteness
  creates misleading diagnostics.
- **Context:** [Kirin integration reference](../../context/kirin-integration.md)

## SYS-010 — Support ordinary synchronous public rewrite entries

- **Normative statement:** Within SYS-002, v1 shall support every invocation whose
  executing code belongs to a plain Python function stored as `rewrite` on a class in
  `type(self).__mro__`, that code is not a generator, coroutine, or async-generator,
  the call frame binds `self` to a pinned Kirin `RewriteRule` and `node` to a pinned Kirin
  `IRNode`. A normal return carrying a pinned Kirin `RewriteResult` shall complete under
  SYS-008; every other exit shall follow SYS-015. Each nested public `rewrite()` frame,
  including explicit same-instance superclass delegation, is a separate invocation. A
  `rewrite_Region`, `rewrite_Block`, or `rewrite_Statement` frame is internal dispatch
  and shall not create another event only when its `self` is the exact `self` of the
  innermost active public rewrite frame. An ordinary synchronous Python
  specialized-handler call with any other `self` is unsupported under SYS-004 and shall
  not leave the enclosing event or trace presented as complete.
- **Parents:** STK-001, STK-002
- **Acceptance criterion:** The inherited base dispatcher on a region, block, and
  statement; an ordinary direct override; explicit same-instance superclass delegation;
  and each of the six direct override owners at the pinned revision (`Walk`, `Fixpoint`,
  `Chain`, `CompactifyRegion`, aggressive `Fold`, and `WalkDesugarBinop`) are observed
  with one public event per executing public frame. Same-instance specialized dispatch
  creates no extra event. A synthetic cross-instance specialized-handler call and the
  pinned `ScfToCfRule` paths that delegate directly to `ForRule` and `IfElseRule`
  explicitly fail and produce no trace presented as complete.
- **Verification:** SYSV-010 (test), SYSV-004 (test)
- **Origin / risk:** Confirmed developer interview, 2026-07-30; shape-based support keeps
  the quick tracer useful for ordinary project rules without class-specific production
  branches.
- **Context:** [Kirin integration reference](../../context/kirin-integration.md) and
  [orchestration tracing options](../../context/orchestration-tracing.md)

## SYS-011 — Keep rewrite detection minor-version-generic

- **Normative statement:** The v1 rewrite detector shall depend only on profiling and
  Python-object interfaces documented in both Python 3.10, the minimum runtime declared
  by the pinned Kirin revision, and Python 3.13. It shall not require bytecode or opcode
  layout, interpreter-private frame or code state, an execution-monitoring interface
  introduced after Python 3.10, mutation or concrete type or identity of frame locals,
  or detector behavior selected by Python minor version. Initial execution verification
  may be limited to CPython 3.13.11; that limitation shall neither pin product support to
  3.13 nor be presented as evidence for an untested interpreter or version.
- **Parents:** STK-001, STK-002
- **Acceptance criterion:** Inspection finds that the version-sensitive parts of profile
  ownership and frame classification use only `sys.getprofile()`, `sys.setprofile()`,
  their documented `call` and `return` event contract, class MRO and namespace
  inspection, the documented predicates for plain Python functions and their generator,
  coroutine, and async-generator forms, function `__code__`, frame `f_code`, read-only
  mapping lookups from frame `f_locals`, and ordinary runtime type and identity checks.
  The detector does not use `sys.monitoring`, bytecode or opcode inspection, `f_lasti`,
  version-specific frame additions, undocumented frame or code attributes, native frame
  access, writes to `f_locals`, an assumption that `f_locals` is a `dict`, or a Python
  minor-version branch to choose detection behavior. Any CPython 3.13.11 execution
  evidence is labeled as single-environment evidence.
- **Verification:** SYSV-011 (inspection)
- **Origin / risk:** Confirmed developer interview, 2026-07-30; a 3.13-only initial test
  environment is acceptable, but minor-version-specific detector machinery is not.
- **Context:** [Python profiling portability](../../context/python-profiling-portability.md)
