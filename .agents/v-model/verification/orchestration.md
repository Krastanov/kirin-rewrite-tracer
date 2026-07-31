# Orchestration Verification and Acceptance Actions

Mark an action `passing` only when durable evidence exercises every pass-criterion
clause; do not paste transient logs.

## ACC-002 — Demonstrate orchestration inspection

- **Covers:** STK-002
- **Method:** demonstration
- **Procedure:** Trace a developer-approved normally returning scenario containing
  supported nested wrappers, leaves, and a no-op, then inspect its uniform event tree and
  compare rule types, relationships, and sibling order with the independently known
  invocation structure.
- **Environment / configuration:** Local Python debugging or test process using Kirin
  commit `7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a` and the support envelope in SYS-002.
- **Pass criterion:** The acceptance authority identifies every supported wrapper and
  leaf occurrence, including the no-op, and determines the correct nearest wrapper and
  relative call position for every nested occurrence.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None

## SYSV-008 — Verify the uniform ordered event tree

- **Covers:** SYS-008, SYS-009
- **Method:** test
- **Procedure:** Exercise every declared-supported wrapper and leaf entry category with
  deterministic fixtures that collectively contain changed and no-op wrapper and leaf
  occurrences while maintaining an independent entry log. Include the asymmetric
  composition `Fixpoint(Walk(Chain(state-changing leaf, always-no-op leaf)))` over one
  block and one statement: its changing run has an independently derived 15-event tree,
  and its already-changed run makes every wrapper a no-op. Also invoke multiple roots in
  one trace. Compare the complete event set, uniform fields, snapshots, identifiers,
  parent references, and sibling ordinals with the fixture and entry log.
- **Environment / configuration:** CPython 3.10 through 3.13 source and
  installed-distribution test processes using Kirin commit
  `7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a`, Rich 15.0.0, the SYS-002 printer
  configuration, and one non-nested trace in a process that remains single-threaded
  within the complete SYS-002 support envelope.
- **Pass criterion:** Exactly one same-shaped event exists for every independently logged
  invocation and no other event; each has completion state `complete`; concrete types
  and before/after states match known values; changing and no-op events exist for
  wrappers and leaves; IDs are unique; only roots lack parents; every parent is the
  nearest enclosing event; and ordinals are distinct within each parent group and
  strictly reproduce entry order, including for parentless roots and repeated concrete
  types.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None

## ACC-004 — Demonstrate incomplete rewrite inspection

- **Covers:** STK-004
- **Method:** demonstration
- **Procedure:** Trace a developer-approved scenario in which a child rewrite completes
  a successful `Statement.delete` and another selected mutation and then raises; its
  parent catches that exception, completes another mutation, and returns normally.
  Inspect the retained event tree, states, operations, relations, deletion effects,
  invocation stacks, and trace-completeness marker beside the untraced result.
- **Environment / configuration:** Local Python debugging or test process using Kirin
  commit `7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a` within the SYS-002 support envelope.
- **Pass criterion:** The acceptance authority sees the child at its original hierarchy
  position with neutral `incomplete` status, a before state and no after state, and every
  completed selected mutation and its exact relation or effect under its original
  operation owner. The parent remains complete with its own before/after pair, the
  aggregate trace is incomplete, and the traced result and final IR match the untraced
  execution.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None

## SYSV-015 — Verify incomplete event retention

- **Covers:** SYS-008, SYS-009, SYS-015
- **Method:** test
- **Procedure:** Use an independent entry and selected-mutation log. First, have a child
  rewrite complete a selected relation-producing mutation and a successful
  `Statement.delete`, then raise a preconstructed sentinel exception; have its parent
  catch that exception, complete another selected mutation, and return a
  `RewriteResult`. Next, propagate the same child failure through its parent. Also run a
  rewrite that explicitly returns `None`, a selected composite mutation that completes a
  nested selected operation before raising, and an exception raised outside every public
  rewrite frame. Compare equivalent traced and untraced executions.
- **Environment / configuration:** Isolated single-threaded CPython 3.10 through 3.13
  processes using the SYS-002 revisions and configuration.
- **Pass criterion:** Each public frame whose profile return does not carry a
  `RewriteResult` is retained as neutrally `incomplete`, with its entry-time ID, parent,
  ordinal, invocation stack, root, before state, and no after or synthetic failure
  state. In the caught case the parent is complete and the child remains incomplete; in
  the propagated case both frames are incomplete. Completed selected operations remain
  once under their innermost events and actual parent operations, with every exact
  relation and the completed statement-deletion effect still attached; an outer selected
  call that raises retains an incomplete shell with no own relation or completed effect
  and does not discard its completed children. The explicit-`None` case is represented
  identically without an exception claim. Every trace containing an incomplete event is
  incomplete; the outside-only exception creates no event and does not by itself change
  event-derived completeness. The propagated exception is the preconstructed sentinel
  by identity, the caught parent's `RewriteResult` fields equal the fixture constants,
  and final statement order, parent links, and SSA-use target identities equal the
  fixture's explicit oracle.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None
