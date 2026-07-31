# Neighboring-Column Provenance Viewer Verification

Use fixtures with independent provenance and geometry oracles. This action remains
planned until its viewer and durable test exist.

## SYSV-021 — Verify exact neighboring-column provenance highlighting

- **Covers:** SYS-021
- **Method:** test
- **Procedure:** Construct an ancestor-free selected range whose event-local pairs
  provide at least three SSA columns and independently tagged identity, one-to-many,
  many-to-one, repeated-occurrence, transient, created, deleted, unmatched, and
  identical-looking-unrelated values. Place exact endpoints both in immediate neighbor
  columns and beyond them. Hover each tagged occurrence, record highlighted occurrences
  in the immediate left and right SSA columns, then end the hover. Select complete
  coarse-parent fixtures whose selected events and descendants at depths one, two, and
  five own distinct one-hop one-to-many and many-to-one `SSAValue` relations with
  endpoints rendered in the selected parent's before and after states. Include two
  qualifying facts with the same endpoints but different relation identifiers and
  operations; ancestor-owned and sibling-owned relations whose endpoints also occur; a
  non-`SSAValue` relation whose container intervals overlap SSA occurrences; a one-hop
  relation with one endpoint absent; a same-ID survivor with no mutation relation; an
  incomplete mutation-operation shell and a completed zero-use `SSAValue.replace_by`;
  a relation whose source occurs only after and destination only before; a two-edge path
  `A -> X -> B`; and a unary deletion effect. Hover both directions, inspect every
  contributing relation's identifier, direction, operation, and event owner, and verify
  no selected-parent copy or endpoint-based canonical merge was created. Repeat with a
  caught incomplete descendant whose completed relation has both endpoints in its
  complete ancestor's snapshots, and with an incomplete selected event whose retained
  relation has no rendered after endpoint. Follow that event by a same-ID occurrence in
  another event's before state and hover the occurrences flanking the absent-after
  indication. Add a separate uncollapsed `A.after | B.before` handoff containing
  repeated occurrences of one surviving entity, a same-looking different entity, and
  cross-boundary relations owned by `A`, `B`, their descendants, and an ancestor. Add a
  shared `A.after`/`B.before` column whose repeated middle entity is related through an
  `A`-applicable fact to the left and a `B`-applicable fact to the right. Repeat in a
  three-event pipeline with two shared columns and in a mixed chain with one separate
  and one shared handoff. Hover every occurrence in both directions.
- **Environment / configuration:** The declared headed Chrome for Testing environment
  with pointer hover under the offline controls of SYSV-018.
- **Pass criterion:** Each hover highlights all and only occurrences in each immediate
  neighbor whose entity is supported by the applicable exact identity or selected
  relation oracle. No nonneighbor or merely similar value is highlighted, and missing
  states or endpoints invent no counterpart. Every qualifying one-hop relation owned by
  the selected event or a descendant at any depth highlights all rendered endpoints in
  both directions while retaining canonical direction, ID, operation, and owner; no
  selected-event copy appears. Qualifying facts with shared endpoints remain distinct
  canonical records even when their occurrence highlights coincide. Ancestor-owned,
  sibling-owned, and non-`SSAValue` relations contribute no SSA highlight. The same-ID
  survivor highlights bidirectionally through identity but contributes no relation
  identifier, direction, operation, or owner. Unsupported operands and the
  reversed-state relation contribute nothing. The completed relation under the caught
  incomplete descendant qualifies without reclassifying that event. A missing endpoint,
  unary effect, or `A -> X -> B` path invents no counterpart. The incomplete event
  neither borrows a later occurrence nor permits hover across its absent-after barrier.
  Across the separate handoff, every occurrence of the surviving same ID highlights
  every occurrence of that ID in the immediate other column, and no mutation relation
  or similar-looking entity contributes. In the shared column, each occurrence uses
  only `A`'s applicable identity and relations toward the left and only `B`'s toward the
  right. Neither relation leaks, changes owner, skips a neighbor, or composes through
  either shared column, and every pointer-owned highlight clears when hover ends in the
  no-keyboard-candidate fixture.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None
