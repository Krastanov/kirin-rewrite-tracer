# Provenance Verification and Acceptance Actions

Pass only with durable evidence covering every criterion; omit transient logs.

## ACC-003 — Demonstrate exact rewrite provenance

- **Covers:** STK-003
- **Method:** demonstration
- **Procedure:** Trace a developer-approved normally returning scenario containing
  surviving, replaced, retargeted, copied, cloned, created, deleted, and visually
  similar unrelated entities. Inspect the identity and selected-mutation provenance,
  deletion effects, rendered occurrence and line sets, operation hierarchy, bidirectional
  navigation, and invocation stacks against the independently known object and call
  relationships.
- **Environment / configuration:** Local Python debugging or test process using Kirin
  commit `7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a` within the SYS-002 support envelope.
- **Pass criterion:** The acceptance authority can distinguish same-object survival from
  every supported mutation relation, inspect the code path for each rewrite event and
  selected operation, follow exact relations through transient entities in either
  direction, identify the supported operation that completed a statement deletion, and
  see unselected or unrelated endpoints remain unmatched without a confidence score,
  duplicated inverse fact, or inferred line pairing.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None

## SYSV-012 — Verify exact identity and selected-mutation provenance

- **Covers:** SYS-012
- **Method:** test
- **Procedure:** Maintain an identity and selected-API call oracle independent of the
  tracer. Exercise a moved surviving statement and SSA value; direct
  `Statement.replace_by`; `SSAValue.replace_by` where the source remains live, where it
  has zero uses, and where multiple sources target one value; `Statement.from_stmt`; and
  recursive
  `Region.clone` with blocks, block arguments, statements, results, and intermediate
  entities absent from both event snapshots. Exercise direct `Statement.delete`,
  replacement cleanup through `DeletedSSAValue`, a selected call that completes a nested
  selected operation before its exception is caught by the rewrite, direct attribute
  mutation, and unrelated entities with identical printed text and metadata. Separately
  invoke a selected method bound before trace activation.
- **Environment / configuration:** Isolated single-threaded CPython 3.13.11 test
  processes using the SYS-002 revisions and configuration. This is initial
  single-environment evidence, not a product runtime pin.
- **Pass criterion:** Entity identifiers follow object identity, never retain raw
  `id()` values as canonical IDs, and do not confuse object-ID reuse. Every selected
  operation appears once in exact entry order, belongs to the innermost event and correct
  parent operation, and has the independently known completion outcome. Completed calls
  contain only their exact relations or effects; an incomplete
  outer call has no own relation or completed effect but retains completed nested
  operations. Recursive clone and copy operations do not duplicate relations;
  operation-only entities and the zero-use operation are retained; the zero-use
  operation has no retargeting relation; and neither cleanup targets, incomplete calls,
  direct mutation, nor similarity creates lineage. The pre-bound bypass explicitly
  fails and leaves no trace presented as complete.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None

## SYSV-013 — Verify exact rendered provenance projection

- **Covers:** SYS-013
- **Method:** test
- **Procedure:** Render a fixture with multiline nested regions and blocks, statement
  result prefixes, repeated SSA definitions and references, moved identity, replacements,
  clones, operation-only entities, completed statement deletion, deletion followed by
  reinsertion of the same statement, an incomplete rewrite event, identical unrelated
  text, and unowned punctuation. Establish expected entity intervals and roles
  independently from fixture construction and instrumented pinned-printer calls. Compare
  retained intervals and the line sets projected for every identity projection,
  mutation relation, and deletion effect.
- **Environment / configuration:** Local CPython 3.13.11 test process using Kirin commit
  `7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a`, Rich 15.0.0, and the SYS-002 rendering
  configuration.
- **Pass criterion:** Every half-open interval, role, and intersected one-based line
  number equals its oracle, including ownership of newline code points; overlapping
  owners are preserved; entities absent from a snapshot or rendering have explicit
  empty occurrence sets; deletion effects retain their exact affected-entity occurrences
  in each available snapshot and an absent product endpoint; the reinserted object has
  same-ID after occurrences; every projection in an incomplete event has an empty
  after-occurrence set rather than a later trace state; and no individual line pair or
  relationship is added from textual, stylistic, positional, type, name, metadata, or
  structural similarity.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None

## SYSV-014 — Verify invocation-stack fidelity and lifetime

- **Covers:** SYS-014
- **Method:** test
- **Procedure:** In a dedicated one-file subprocess with a controlled module entry,
  invoke supported rewrites and all selected mutation APIs through a deterministic chain
  of driver, orchestration, rewrite, and helper functions, including a nested mutation.
  Include an incomplete rewrite and an incomplete selected mutation.
  Derive expected filenames, line numbers, and function names from the fixture's code
  objects and marked call sites. During capture, replace source-line lookup with a
  failing sentinel and place a frame-local object with a raising `repr()`. After
  releasing the trace, force collection and observe a weak reference to a separate
  frame-local lifetime sentinel.
- **Environment / configuration:** Isolated single-threaded CPython 3.13.11 test process
  using the SYS-002 revisions and configuration. This is initial single-environment
  evidence, not a product runtime pin.
- **Pass criterion:** Every event and mutation references the exact full ordered frame
  sequence and only the three declared fields; nested operations retain useful Kirin
  caller frames; incomplete records retain invocation paths but no exception traceback
  claim; tracer frames are absent; source lookup and hostile local `repr()` are never
  invoked; and the lifetime sentinel is collectible, demonstrating that canonical
  storage retains no live frame or traceback graph.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None

## SYSV-016 — Verify single-copy bidirectional provenance navigation

- **Covers:** SYS-016
- **Method:** test
- **Procedure:** Build an independent oracle for moved identity, one-to-one replacement,
  one-to-many clone, many-to-one use retargeting, transient operation-only entities, and
  completed statement deletion. Query each applicable identity, relation, or effect from
  every endpoint. Discard and rebuild all in-memory lookup indexes from the retained
  canonical facts, then repeat the queries.
- **Environment / configuration:** Isolated single-threaded CPython 3.13.11 test process
  using the SYS-002 revisions and configuration. This is initial single-environment
  evidence, not a product runtime pin.
- **Pass criterion:** The same live object has one trace entity identifier across
  snapshots. Source and destination queries return the same canonical relation
  identifiers; entity and operation queries return the same deletion-effect identifiers;
  no inverse relation is retained as an independent canonical fact; and rebuilding
  derived
  indexes preserves every result.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None

## SYSV-017 — Verify supported statement-deletion effects

- **Covers:** SYS-017
- **Method:** test
- **Procedure:** Independently log direct `Statement.delete` in a dead-code-style
  rewrite, the nested `Statement.delete` inside `Statement.replace_by`, deletion followed
  by reinsertion of the exact same statement object, and a `Statement.delete` call that
  exits after partial mutation. Also remove statements with direct `detach`, and remove
  empty and statement-containing blocks and regions through their own delete and detach
  APIs. Compare effects, operation nesting, event ownership, entity identities, and
  invocation stacks with the oracle.
- **Environment / configuration:** Isolated single-threaded CPython 3.13.11 test process
  using the SYS-002 revisions and configuration. This is initial single-environment
  evidence, not a product runtime pin.
- **Pass criterion:** Each normally completed `Statement.delete` call produces exactly
  one `statement_delete_completed` effect linked to its statement and operation. Nested
  replacement cleanup remains beneath its replacement operation and every effect leads
  through operation and event to the exact invocation stack. Reinsertion preserves the
  statement's entity identifier and the historical operation effect. The incomplete
  delete retains only an incomplete operation shell and completed child facts, if any.
  Direct detach and empty-container removal produce no effect; nonempty block or region
  deletion produces effects only for the selected `Statement.delete` calls it actually
  invokes, never for the container entity itself; and snapshot disappearance alone
  never creates an effect.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None
