# Neighboring-Column Provenance Viewer Requirements

## SYS-021 — Highlight exact provenance in neighboring SSA columns

- **Normative statement:** Hovering a rendered `SSAValue` occurrence shall highlight all
  and only related occurrences in each immediate displayed SSA neighbor, using exact
  identity or selected-mutation provenance applicable to those states. It shall not
  reach a nonneighbor or infer from text, name, type, position, structure, or appearance.
  Absent or unmatched endpoints shall invent no counterpart. Hover exit shall remove its
  pointer candidate and, when no independently active SYS-023 keyboard-focus candidate
  remains, clear the preview. In a selected event's own before/after pair, a retained one-hop
  selected-mutation relation shall apply if and only if its canonical source and
  destination are `SSAValue` entities, its canonical mutation operation is owned by the
  selected event or a strict descendant whose event-parent chain reaches the selected
  event, its source has a rendered occurrence in the selected event's before state, and
  its destination has a rendered occurrence in the selected event's after state.
  Hovering either endpoint shall use that same canonical relation bidirectionally
  without changing its direction, identifier, operation, or original event owner;
  creating a selected-event copy; merging canonical relations that share endpoints; or
  traversing two or more relations to synthesize another correspondence.
  Provenance applicability shall be evaluated for the logical state-role edge behind
  each displayed adjacency. Across an event's own `E.before` to `E.after` edge, including
  when either endpoint is a shared column, exact identity and only relations applicable
  to `E` under the preceding rule shall contribute. Across a separate, uncollapsed
  `A.after` to `B.before` handoff, exact same-entity identity shall be the only
  contributor; no mutation relation shall cross that edge regardless of its owner or
  rendered endpoints. A shared `A.after`/`B.before` column shall retain both roles:
  toward its left neighbor it shall use only `A`'s own event edge, and toward its right
  neighbor it shall use only `B`'s own event edge. Facts shall not leak to the other
  side, be reassigned to the shared column, or compose through it. An explicit
  absent-after indication shall be a hover barrier, not an SSA state: the view shall not
  treat SSA columns on opposite sides of that indication as neighbors.
- **Parents:** STK-003, STK-004, STK-005
- **Acceptance criterion:** Given three or more SSA columns with exact identity,
  one-to-many and many-to-one relations, repeated occurrences, absent endpoints, and
  similar unrelated values, each hover highlights only exact immediate neighbors. Given
  coarse-parent fixtures parameterized with one-hop `SSAValue` relation owners at
  selected-event and descendant depths one, two, and five, every qualifying fact
  highlights all endpoint occurrences in both hover directions while keeping its
  relation ID, operation, and owner. Facts sharing endpoints stay distinct.
  Ancestor-owned, sibling-owned, and non-`SSAValue` relations do not contribute. Same-ID
  survival highlights without relation metadata; bare operands of incomplete or
  zero-use operations do not. Missing endpoints, deletion effects, and two-edge paths
  invent no counterpart. At a separate handoff, hovering any occurrence of a surviving
  entity highlights all occurrences of that same ID across the boundary, while
  same-looking entities and mutation relations owned by either event, their descendants,
  or an ancestor contribute nothing. In a shared handoff column, hovering any repeated
  occurrence uses `A`-applicable facts only on the left and `B`-applicable facts only on
  the right; consecutive shared columns neither skip a neighbor nor create a transitive
  highlight. An absent-after barrier never connects its flanking SSA states. No
  nonneighbor is highlighted, and with no keyboard-focus candidate all transient
  highlighting disappears when hover ends.
- **Verification:** SYSV-021 (test)
- **Origin / risk:** Developer confirmations, 2026-07-30; heuristic, transitive, or
  reassigned highlighting would visually assert provenance not established by the trace.
- **Context:** [Interactive trace viewer options](../../context/interactive-trace-viewer.md)
