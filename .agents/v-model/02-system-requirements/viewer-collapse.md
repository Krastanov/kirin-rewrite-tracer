# Event Subtree Collapse Requirements

One disclosure control per non-leaf event row navigates a large hierarchy without
competing with SYS-020 selection. Keyboard/focus behavior and visual presentation are
specified by SYS-023 and SYS-024.

## SYS-025 — Collapse a non-leaf subtree that holds no selected event

- **Normative statement:** Each retained non-leaf event row shall carry exactly one
  native collapse control immediately before its event control, and no leaf row shall
  carry one. That control shall own one two-state disclosure over its event's child
  list: expanded, the initial state of every non-leaf event, or collapsed. Activating an
  enabled control shall replace only its own event's state; it shall change no frontier,
  range anchor, SSA column, highlight, overlay, accessible occurrence description, or
  canonical fact, and shall retain focus on the control.
  A collapsed event shall hide every strict descendant row transitively before
  presentation, and those rows shall expose no row, control, or manual or accessibility
  target exactly as SYS-020 parent dominance requires. Collapse shall only hide: a row
  shall be displayed if and only if no selected ancestor hides it under SYS-020 and no
  collapsed ancestor hides it, so no collapse state can reveal a row that parent
  dominance hides. A hidden row shall retain its own collapse state, and expanding an
  ancestor shall restore each descendant at its exact original hierarchical position
  with that retained state and without stale selection state.
  The control shall be enabled if and only if its event is non-leaf and no selected
  event lies in the subtree rooted at that event, counting the event itself. Otherwise
  it shall be natively disabled, stay outside sequential focus order, and reject
  pointer, keyboard, and programmatic activation without changing any state. Because a
  disabled control cannot change state, collapse shall never hide a selected event or
  the range anchor. A control whose own row is not displayed shall likewise reject
  activation.
  A SYS-020 Shift range shall snapshot exactly the rows displayed under both rules, so a
  collapsed subtree contributes only its collapsed root to the interval and its hidden
  descendants can neither join nor be swallowed by that range. Selecting a collapsed
  event shall leave it collapsed and disable its control; Clear selection shall leave
  every collapse state unchanged.
  Each control shall be one native button that exposes `aria-expanded` for its state and
  `aria-controls` for its child list, and whose accessible name is exactly
  `Collapse event E children.` when expanded or `Expand event E children.` when
  collapsed, with `; unavailable while its subtree contains a selected event` inserted
  before the final period while it is disabled. Its state shall also be identifiable
  without hue through a marker glyph kept outside its accessible-name subtree and
  through the native disabled presentation required by SYS-024. While enabled it shall
  occupy the SYS-023 sequential focus position immediately before its event control, and
  focusing it shall change neither selection nor range anchor.
- **Parents:** STK-002, STK-005
- **Acceptance criterion:** In the asymmetric depth-three SYS-020 tree, exactly the
  non-leaf events carry a collapse control, every control starts expanded and enabled,
  each `aria-controls` names the list holding exactly that event's subtree rows, and the
  sequential focus order places each enabled control immediately before its event
  control. Collapsing a depth-zero event hides every descendant at both depths, adds
  them to the announced hidden count, removes their accessibility nodes, leaves the
  frontier, columns, and facts untouched, and keeps focus on the control. Collapsing an
  inner event and then its ancestor, and expanding only the ancestor, restores the inner
  collapsed state rather than the whole subtree; expanding both restores the original
  order. Enter and Space reproduce the pointer transition exactly once.
  Selecting a descendant, or the event itself, disables that event's control, appends
  the unavailable clause to its accessible name, removes it from sequential focus order,
  and makes pointer and programmatic activation inert; Clear re-enables it. A control
  hidden inside a collapsed ancestor is also inert. An event collapsed before it is
  selected stays collapsed, keeps `aria-expanded` false, and reports the unavailable
  name. With a collapsed subtree present, a Shift range over the displayed rows selects
  the collapsed root without its hidden descendants, and Clear afterward empties the
  frontier while leaving that subtree collapsed and its hidden count announced.
- **Verification:** SYSV-026 (test)
- **Origin / risk:** Developer request, 2026-07-31; an always-enabled disclosure would
  contradict SYS-020 parent dominance, could hide the selected frontier or the range
  anchor, and could silently change which rows a Shift range covers.
- **Context:** [Event-selection options](../../context/event-selection.md) and
  [viewer accessibility options](../../context/viewer-accessibility.md)
