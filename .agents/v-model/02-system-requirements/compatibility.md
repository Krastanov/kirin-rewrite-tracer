# Rewrite Compatibility Requirements

V1 has a shape-based public-entry support category. The pinned Kirin overrides are
compatibility fixtures, not a production allowlist. Its detector is constrained to
documented, minor-version-generic Python interfaces. V1 supports CPython
`>=3.10,<3.14`; observable unsupported callable execution invalidates the session, while
unobservable and never-executed callable forms remain explicit input assumptions.

## SYS-002 — Bound the v1 support envelope

- **Normative statement:** The v1 product shall support tracing only on CPython
  `>=3.10,<3.14` against Kirin commit
  `7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a` with Rich exactly 15.0.0. The Kirin
  revision shall be proved through PEP 610 VCS provenance for the installed distribution
  or a clean local Git checkout at that exact commit; source or API fingerprints shall
  not be treated as commit proof. Before activation, the product shall require the five
  expected raw descriptors for `Statement.replace_by`, `SSAValue.replace_by`,
  `Statement.from_stmt`, `Region.clone`, and `Statement.delete`, using the pinned Kirin
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
  product is not required to detect an input-assumption violation. Cleanup shall remove
  the profile callback or restore a descriptor only when it is still the exact
  tracer-installed object and shall never clobber a foreign replacement.
- **Parents:** STK-001, STK-002, STK-003
- **Acceptance criterion:** On CPython 3.10–3.13, the proved pinned revisions,
  descriptors, empty profile slot, non-nested context, declared printer configuration,
  optional analysis, pure representation hooks, and lifetime assumptions permit normal
  and body-exception runs and restore an owned slot. Every varied runtime, provenance,
  revision, descriptor, profile, nesting, or printer input fails before activation.
  Fingerprints never prove a commit, and cleanup never overwrites foreign state.
- **Verification:** SYSV-002 (test)
- **Context:** [Kirin integration reference](../../context/kirin-integration.md)

## SYS-004 — Reject unsupported tracing use

- **Normative statement:** The product shall explicitly signal failure for every rule,
  tracing configuration, required snapshot-value representation category, or
  presentation path that it declares unsupported, instead of silently omitting activity
  or information. Unsupported use shall atomically invalidate the active recorder,
  immediately raise one stable unsupported-use error, and expose no partial trace or
  export. Catching that error inside the trace body shall not make the session valid:
  otherwise-normal context exit shall raise the same error object again. If a distinct
  body exception occurs after unsupported use was already signalled, that later exception
  shall remain the propagated object. This obligation does not apply to violations of
  the input assumptions explicitly declared in SYS-002.
- **Parents:** STK-001, STK-002
- **Acceptance criterion:** Given every declared unsupported category other than a
  SYS-002 input-assumption violation, including each declared unsupported required-value
  representation and presentation path, tracing explicitly signals failure and exposes
  no trace or export. Caught unsupported use reappears by identity on otherwise-normal
  exit, a later distinct exception propagates by identity, and repeated recorder access
  cannot recover partial state.
- **Verification:** SYSV-004 (test)
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
  not leave a trace. An observable public frame whose owner, descriptor, `self`, `node`,
  or executing code does not satisfy this shape, and observable execution of generator,
  coroutine, or async-generator rewrite code, is likewise unsupported. A deferred
  callable never executed and a C or custom descriptor that produces no classifiable
  Python frame is an input assumption with no v1 support claim or required diagnostic.
- **Parents:** STK-001, STK-002
- **Acceptance criterion:** The inherited base dispatcher on a region, block, and
  statement; an ordinary direct override; explicit same-instance superclass delegation;
  and each of the six direct override owners at the pinned revision (`Walk`, `Fixpoint`,
  `Chain`, `CompactifyRegion`, aggressive `Fold`, and `WalkDesugarBinop`) are observed
  with one public event per executing public frame. Same-instance specialized dispatch
  creates no extra event. A synthetic cross-instance specialized-handler call and the
  pinned `ScfToCfRule` paths that delegate directly to `ForRule` and `IfElseRule`
  fail without a trace. Observable malformed and executed deferred bodies invalidate;
  construction without execution establishes no diagnostic claim.
- **Verification:** SYSV-010 (test), SYSV-004 (test)
- **Context:** [Kirin integration reference](../../context/kirin-integration.md) and
  [orchestration tracing options](../../context/orchestration-tracing.md)

## SYS-011 — Keep rewrite detection minor-version-generic

- **Normative statement:** The v1 rewrite detector shall depend only on profiling and
  Python-object interfaces documented in both Python 3.10, the minimum runtime declared
  by the pinned Kirin revision, and Python 3.13. It shall not require bytecode or opcode
  layout, interpreter-private frame or code state, an execution-monitoring interface
  introduced after Python 3.10, mutation or concrete type or identity of frame locals,
  or detector behavior selected by Python minor version. Product support is limited to
  CPython 3.10 through 3.13; evidence for one minor shall not be presented as evidence
  for another.
- **Parents:** STK-001, STK-002
- **Acceptance criterion:** Inspection finds only documented profile calls/events,
  MRO/namespace and plain-function predicates, function/frame code, read-only mapping
  lookups, and ordinary type/identity checks. It finds no monitoring, bytecode, private
  frame, native, local-write/concrete-map, or minor-version branch. Source and installed
  suites exercise that detector on CPython 3.10–3.13.
- **Verification:** SYSV-011 (inspection)
- **Context:** [Python profiling portability](../../context/python-profiling-portability.md)
