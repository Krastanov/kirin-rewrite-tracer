# Provenance Requirements

The base provenance model is deliberately partial and exact. It combines trace-scoped
object identity with a small pinned mutation API; it does not infer lineage from text,
position, names, types, or structural similarity.

## SYS-012 — Preserve exact entity provenance

- **Normative statement:** For every event retained under SYS-008 or SYS-015, the
  product shall assign one trace-unique entity identifier to each pinned Kirin `Region`,
  `Block`, `Statement`, and `SSAValue` object reachable from either snapshot or
  referenced by a retained provenance operation. The same live object shall retain the
  same identifier throughout the trace. In addition to this identity basis, the product
  shall retain an ordered mutation-operation shell from entry for every call, during
  that event, through the pinned implementations of `Statement.replace_by`,
  `SSAValue.replace_by`, `Statement.from_stmt`, `Region.clone`, and `Statement.delete`
  while tracing is active. Each operation shall identify its API, owning innermost
  rewrite event, dynamic parent operation if any, source and destination entity operands
  known at that point, invocation stack, and outcome `completed` or `incomplete`. A
  normally returning relation-producing selected call shall retain the exact relations
  it produces; a normally returning `Statement.delete` call shall retain the effect
  required by SYS-017. Relations shall mean only: statement replacement; retargeting of
  the source SSA value's then-current uses; statement and index-corresponding result
  copying; and region, direct block, and index-corresponding direct block-argument
  cloning. A normally
  returning `SSAValue.replace_by` call with no pre-call uses shall retain its operation
  and endpoints but produce no use-retargeting relation. `DeletedSSAValue` destinations
  shall not be represented as lineage. A selected call that exits exceptionally shall
  retain its shell as `incomplete` but produce no relation or completed deletion effect
  of its own; any nested selected operations that already completed shall remain
  retained under their actual dynamic parent and owning event. Entry into a saved
  selected implementation without its installed interception wrapper is unsupported
  under SYS-004. The product shall emit no provenance fact without exact identity or
  selected-operation evidence, shall not derive one from text, style, metadata, source
  location, position, type, name, or structural similarity, and shall mark an entity
  with no supported identity projection, mutation relation, or effect as unmatched
  without enumerating unrelated entity pairs.
- **Parents:** STK-003, STK-004
- **Acceptance criterion:** Given an asymmetric fixture containing a surviving moved
  object; successful uses of all five selected APIs, including nested cloning and
  many-to-one and zero-use SSA replacement; operation-only intermediate clone entities;
  a `Statement.replace_by` cleanup path; a selected call whose exception is caught by
  its rewrite; direct field mutation; and visually identical but unrelated entities,
  the trace preserves stable identity only for the same objects, records each completed
  selected call once with its exact operation hierarchy and relations or effect, retains
  each incomplete call shell and its completed descendants, retains needed intermediate
  entities, creates no `DeletedSSAValue` or incomplete-call lineage, and leaves direct
  mutations unexplained and merely similar entities unrelated. A selected implementation
  invoked through a method bound before tracing explicitly invalidates the trace instead
  of silently omitting its operation.
- **Verification:** SYSV-012 (test)
- **Origin / risk:** Developer confirmation, 2026-07-30; heuristic or silently partial
  lineage would make a diagnostic trace assert facts Kirin did not establish.
- **Context:** [Exact provenance capture options](../../context/provenance-capture.md)

## SYS-013 — Project exact entity provenance onto rendered SSA

- **Normative statement:** Each snapshot shall retain every exactly observed rendered
  occurrence of a trace entity as a half-open Unicode code-point interval, its snapshot,
  and one of three roles: `container` owns the full interval emitted while printing a
  `Region`, `Block`, or `Statement`, including nested output; `definition` owns the
  printed identifier of a result or block argument at its definition; and `reference`
  owns the printed identifier of an SSA value at an operand or successor-argument use.
  Intervals may overlap, and emitted text not attributable to a tracked entity shall
  remain unowned. For each identity projection or mutation relation in an
  event, the product shall expose the source entity's occurrences in that event's before
  snapshot, the destination entity's occurrences in its after snapshot, and the
  one-based rendered line numbers intersected by those intervals, with each `"\n"`
  belonging to its preceding line. An entity absent from the applicable snapshot or
  without a rendered occurrence shall remain an explicit empty endpoint. The product
  shall not invent an individual line-to-line pairing within those sets or relate
  unowned or merely similar text. For a completed deletion effect under SYS-017, the
  product shall expose the affected entity's occurrences independently in the owning
  event's before and after snapshots and shall expose a distinct, explicitly absent
  destination or product endpoint for the unary effect. If the same object is reinserted
  before the after snapshot, its same-ID after occurrences shall remain visible without
  becoming an effect destination. An event without an after snapshot under SYS-015
  shall expose an explicit empty after-occurrence set for every projection and shall not
  substitute the eventual trace state.
- **Parents:** STK-003, STK-004
- **Acceptance criterion:** Given asymmetric multiline and nested SSA snapshots with
  moved survivors, replacements, cloned and transient entities, repeated identical
  text, multiple definition and reference occurrences, unowned punctuation, and
  created and deleted entities, retained intervals match an independent ownership
  oracle. Every projected line set is exactly the set obtained by intersecting those
  intervals with rendered lines; incomplete events and absent endpoints have explicit
  empty sets; completed deletion effects have the exact affected-entity occurrences on
  each existing snapshot and an absent product endpoint; delete-then-reinsert preserves
  same-ID after occurrences; and no extra line relationship arises from repeated text
  or layout.
- **Verification:** SYSV-013 (test)
- **Origin / risk:** Developer confirmation, 2026-07-30; an all-to-all or similarity
  based line mapping would overstate the exact entity evidence.
- **Context:** [Exact provenance capture options](../../context/provenance-capture.md),
  [provenance graph and deletion storage](../../context/provenance-graph-storage.md), and
  [snapshot representation options](../../context/snapshot-representation.md)

## SYS-014 — Retain structured invocation code stacks

- **Normative statement:** Every supported rewrite event and every mutation operation
  retained under SYS-012 shall reference a structured invocation stack. Each frame shall
  contain exactly the runtime filename string, runtime line-number integer, and function
  name,
  ordered from the outermost recorded caller to the executing public `rewrite` frame for
  an event or to the direct non-tracer caller for a mutation. Capture shall retain the
  full available Python stack without an arbitrary depth limit and omit only
  tracer-owned capture and wrapper frames identified by exact code identity. Canonical
  storage shall not retain live frames, traceback objects, locals or their
  representations, source-line text, columns, bytecode positions, or
  version-specific additions. An identity projection has no invented mutation operation
  or operation stack; its containing rewrite event's stack remains separately
  inspectable. An incomplete event or operation shall retain the invocation path captured
  at entry and shall not present it as an exception traceback or raise-site stack.
- **Parents:** STK-003, STK-004
- **Acceptance criterion:** Given a deterministic outer-driver, orchestration, rewrite,
  helper, and nested selected-mutation call chain, the event and operation stacks
  contain exactly the independently established filename, line-number, and function-name
  sequence in the declared order, including Kirin helper frames and excluding only
  tracer frames. Capture does not access source lines or call `repr()` on locals, and no
  retained stack keeps a frame-local sentinel alive after the trace is released.
- **Verification:** SYSV-014 (test)
- **Origin / risk:** Developer confirmation and API investigation, 2026-07-30; retaining
  live frames risks memory leaks, while formatted or version-specific stacks are brittle
  and difficult to query.
- **Context:** [Structured invocation-stack storage](../../context/invocation-stack-storage.md)
