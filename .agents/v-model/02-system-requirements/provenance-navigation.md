# Provenance Navigation and Deletion Requirements

The provenance graph stores one authoritative copy of each exact relation or effect.
Deletion is an operation effect rather than a fabricated destination entity.

## SYS-016 — Navigate exact provenance from either endpoint

- **Normative statement:** Every retained source-to-destination mutation relation shall
  have one canonical orientation and one trace-unique relation identifier. Lookup by its
  source entity and lookup by its destination entity shall both return that same
  relation identifier; the product shall not retain a second inverse relation as an
  independent canonical fact. Identity shall remain the single trace entity identifier
  shared by the same live object across snapshots and shall be navigable from each of
  its occurrences. Every deletion effect retained under SYS-017 shall likewise have one
  identifier and be navigable both from its affected entity and from its mutation
  operation. In-memory lookup indexes or presentation links may be derived and rebuilt
  from these canonical facts.
- **Parents:** STK-003
- **Acceptance criterion:** Given identity, one-to-one, one-to-many, many-to-one,
  transient, and deletion cases, navigation from every applicable endpoint returns the
  independently known canonical entity, relation, or effect identifiers. Forward and
  reverse queries agree on each fact, no independently mutable inverse fact exists, and
  an index rebuild preserves all query results.
- **Verification:** SYSV-016 (test)
- **Origin / risk:** Developer question and design review, 2026-07-30; predecessor-only
  metadata loses deletion consumers, while duplicated forward and backward facts can
  disagree.
- **Context:** [Provenance graph and deletion storage](../../context/provenance-graph-storage.md)

## SYS-017 — Retain exact supported statement-deletion effects

- **Normative statement:** For every normally completed selected
  `Statement.delete(safe=...)` call within a retained rewrite event, the product shall
  retain exactly one `statement_delete_completed` entity effect linked to that mutation
  operation and the affected statement entity. The effect records that call occurrence,
  not a permanent state of the Python object: later reinsertion of the same statement
  shall retain the same entity identifier and shall not erase the effect. A nested
  deletion called by `Statement.replace_by` shall remain a child operation, so its
  operation, owning rewrite event, and SYS-014 invocation stack identify the code path
  that caused it. An incomplete `Statement.delete` operation shall have no completed
  deletion effect of its own. Snapshot disappearance alone, `Statement.detach`,
  `Block` or `Region` deletion or detachment, and other unselected removal paths shall
  not produce an effect for the directly removed statement, block, or region entity.
  Any selected `Statement.delete` calls dynamically invoked by an unselected container
  operation shall still retain their own statement effects. Every otherwise unexplained
  disappearance shall remain explicitly unexplained by supported provenance.
- **Parents:** STK-003, STK-004
- **Acceptance criterion:** Given direct dead-code deletion, replacement's nested
  deletion, deletion followed by reinsertion of the same object, an incomplete
  statement deletion, direct statement detachment, and empty and nonempty block and
  region removals, each completed `Statement.delete` call has exactly one attributable
  effect with the correct statement, operation hierarchy, event, and invocation stack.
  The reinserted object keeps its identity, the incomplete operation has no completed
  effect, empty container removal produces no effect, populated container removal
  retains effects only for dynamically invoked selected statement deletions, and no
  snapshot-only or unselected entity removal acquires an invented effect of its own.
- **Verification:** SYSV-017 (test)
- **Origin / risk:** Developer question and pinned Kirin API investigation, 2026-07-30;
  absence from an after snapshot does not prove which operation removed an entity, and
  Kirin permits a deleted statement object to be reinserted.
- **Context:** [Provenance graph and deletion storage](../../context/provenance-graph-storage.md)
