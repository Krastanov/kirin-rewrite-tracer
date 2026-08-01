# Unchanged Event Classification and Filter Requirements

The viewer derives one event change classification from retained canonical facts. One
document-local control can then remove confirmed no-op subtrees without treating an
incomplete or contradictory event as unchanged.

## SYS-026 — Classify events and optionally hide unchanged subtrees

- **Normative statement:** For presentation only, the view shall classify every event
  from its retained snapshots and result. An incomplete event, which has no after
  snapshot or result, shall be `incomplete`. A complete event shall be `unchanged` if
  its complete retained before and after snapshot payloads are semantically equal under
  SYS-020 and `result.has_done_something` is false; it shall be `changed` if those
  payloads are semantically different and `result.has_done_something` is true. The two
  remaining complete combinations shall be `inconsistent`. No incomplete or
  inconsistent event shall qualify as unchanged.
  Each event row shall expose its classification through a semantic data attribute.
  An unchanged row shall use the SYS-024 muted presentation while retaining the complete
  selected and focus cues. Each inconsistent row shall display the non-color-only text
  badge `Inconsistent change flag` and its event control's accessible description shall
  append exactly one applicable explanation: `Inconsistent change flag: retained before
  and after snapshots are semantically equal, but has_done_something is true.` or
  `Inconsistent change flag: retained before and after snapshots are semantically
  different, but has_done_something is false.`
  Beside `Clear selection`, the document shall contain one native toggle whose visible
  text is `Hide unchanged events` while off and `Show unchanged events` while on. It
  shall expose the same state through `aria-pressed`, control the event tree through
  `aria-controls`, start off in every newly opened document, persist only for that open
  document, and be natively disabled if no retained event is classified `unchanged`.
  Clear shall not change this toggle.
  While the toggle is on, every unchanged row and every strict descendant of an
  unchanged event shall be hidden. Filter hiding, SYS-020 parent dominance, and SYS-025
  collapse shall compose as a union: each rule can only hide, no rule can reveal a row
  hidden by another, and retained collapse state shall survive either filter transition.
  Hidden rows shall expose no pointer, keyboard, focus, or accessibility target.
  Turning the filter on shall atomically remove from the selection frontier every event
  hidden by the filter and rebuild the SSA workspace from all surviving frontier events
  in their displayed order. If the current anchor survives, it shall remain the anchor;
  otherwise the first surviving frontier event shall become the anchor. If no selected
  event survives, the frontier and anchor shall become empty and null and the workspace
  shall return to its explicit no-selection state. Turning the filter off shall restore
  filtered rows at their retained hierarchical positions, subject to the other two
  hiding rules, unselected and without restoring removed columns or other stale derived
  state.
  SYS-020 Shift selection shall snapshot the complete pre-action displayed event order
  after parent dominance, collapse, and this filter have all been applied. Thus every
  surviving changed, inconsistent, or incomplete event in the inclusive visible range
  shall remain eligible for the ordered frontier and before/after SSA columns, including
  exact-equal handoff sharing; filtered rows shall contribute neither a range position
  nor a column. The SYS-023 hidden count shall count the union of all three hiding rules
  exactly once per hidden row.
- **Parents:** STK-001, STK-002, STK-004, STK-005
- **Acceptance criterion:** Fixtures covering `unchanged`, `changed`, both directions of
  `inconsistent`, and `incomplete` expose the exact classification attributes; only
  confirmed unchanged rows use muted styling, and inconsistent rows expose the exact
  badge and applicable accessible explanation. The native filter toggle starts off,
  targets the tree, reports `aria-pressed` accurately, keeps focus through pointer,
  Enter, and Space activation, and is disabled for empty traces and traces without an
  unchanged event.
  Enabling it hides every unchanged row and the complete subtree of an unchanged
  parent, removes those nodes from focus and accessibility order, announces the exact
  union hidden count, and leaves inconsistent and incomplete rows visible. Disabling it
  restores retained order but no removed selection. A collapse retained beneath a
  filtered row is still collapsed after restoration, parent dominance still hides
  descendants, and neither rule reveals a row concealed by another.
  Filtering an unchanged singleton clears selection, anchor, columns, overlay,
  provenance state, and facts. Filtering a mixed range preserves every surviving event
  and ordered SSA pair, retains a surviving anchor, rebases a removed anchor to the first
  surviving event, and clears it only when the frontier becomes empty. Forward and
  reverse Shift ranges span exactly the displayed non-filtered order and preserve exact
  dual-role handoffs. Clear leaves the filter on and restores only rows not concealed by
  collapse or the filter. The inert embedded trace bytes and decoded canonical arrays
  remain unchanged throughout.
- **Verification:** SYSV-027 (test)
- **Origin / risk:** Developer request, 2026-08-01; snapshot equality or a rewrite-result
  flag alone can mislabel contradictory evidence, while filtering individual no-op rows
  without their descendants would detach the visible hierarchy and stale selection.
- **Context:** [Event-selection options](../../context/event-selection.md),
  [viewer accessibility options](../../context/viewer-accessibility.md), and
  [viewer styling options](../../context/viewer-styling.md)
