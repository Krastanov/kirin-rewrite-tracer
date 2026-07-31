# Viewer Keyboard and Focus Requirements

V1 uses native document controls, not a custom ARIA tree, grid, or dialog.

## SYS-023 — Operate the viewer by keyboard and preserve focus

- **Normative statement:** The event hierarchy shall render as nested ordered lists of
  native event-row buttons in displayed depth-first order, without `tree`, `treegrid`,
  or custom roving-focus roles. A first-focus skip link shall move keyboard focus past
  the event hierarchy to the labelled SSA workspace. An always-available native
  `Clear selection` button shall remain in sequential focus order, identify its action
  accessibly, invoke SYS-020 exactly once through native activation, and retain focus
  after clearing. `Tab` and `Shift+Tab` shall follow the visible native-control order.
  Merely focusing an event row shall change neither
  selection nor range anchor. `Enter` or `Space` on an event row shall perform the same
  plain selection transition as its primary click, while Shift combined with either
  key shall perform the same Shift-range transition; Ctrl and Meta shall retain the
  precedence defined by SYS-020. Each row's accessible description shall identify its
  event, hierarchy and completion status, and selected or unselected state. One polite
  status region shall announce one of these exact ordered schemas: `Selected: 0; hidden:
  H.`, `Selected: 1; event: E; hidden: H.`, or `Selected: N; first: E1; last: E2;
  hidden: H.`, where the values are the selected frontier count, displayed event IDs,
  and total descendants hidden by parent dominance.
  After event activation, focus shall remain on the target if it survives
  normalization. If a selected ancestor hides that target, focus shall move before
  presentation to the unique surviving selected ancestor. Hiding only the range anchor
  shall not redirect focus from a surviving target. Restored descendants shall never
  regain focus automatically. Hidden descendants shall be absent from the document's
  focus order and accessibility tree.
  Each eligible rendered SSA occurrence shall be one native button in labelled
  column-major document order. Its accessible name shall equal the exact captured text
  in that occurrence interval. Its accessible description shall identify its definition
  or reference role, exact occurrence owner, and every logical state role of its column;
  a shared column shall name both roles. The metadata suffix shall create no additional
  focus stop and shall remain outside the occurrence button's accessible-name subtree.
  `Enter` or `Space` on an occurrence shall perform exactly one SYS-022 occurrence-click
  transition.
  Focus reaching an occurrence through `Tab` or `Shift+Tab` shall request the same exact
  immediate-neighbor projection as SYS-021 hover and expose an accessible description
  containing each neighbor role and, for every related occurrence in display order, its
  stable trace entity ID, owner ID, one-based ordinal within that neighbor column's
  displayed occurrence sequence, and rendered label. It shall distinguish a present
  neighbor with zero exact matches from an absent neighboring SSA state.
  The view shall retain at most one provenance preview. The most recently entered
  eligible pointer-hover or keyboard-focus candidate shall own it; when that candidate
  ends, the most recent still-active candidate shall resume, and when no candidate
  remains the preview shall clear. Pointer-induced or programmatic fallback focus alone
  shall not create a keyboard candidate, but the first `Enter` or `Space` activation
  directed to that focused occurrence shall promote it before applying the key's action.
  A candidate shall require continuous hover or focus on the same rendered control.
  Before presenting a recomputed workspace, the view shall discard every active or
  suspended candidate whose control was removed or whose exact occurrence or ordered
  column-role tuple no longer exists. Recreating an equal control, occurrence, or tuple
  shall not revive that candidate.
  The metadata overlay shall be a nonmodal, read-only region using semantic key/value
  markup, not a tooltip or dialog. Its accessible label shall name its active
  occurrence's captured label, stable entity and owner IDs, and ordered column-role
  tuple. Its occurrence button shall expose `aria-expanded` and `aria-controls`. While
  open, the region shall expose one temporary `tabindex="0"` stop immediately after its
  anchor in sequential focus order so keyboard scrolling can reach an oversized
  inventory. Opening, and closing while focus is outside the region, shall not
  programmatically move or trap focus; the normal focus behavior of an activated outside
  control shall still occur. `Tab` shall not itself dismiss the overlay, although a
  resulting page or workspace scroll shall close it under SYS-022. `Escape` shall close
  it while leaving focus on its current surviving control. Any close transition removing
  the focused region shall return focus to its surviving anchor and scroll that anchor
  into view if necessary; the resulting scroll shall cause no second transition.
  Selection-driven column removal shall leave focus on the activating event row or its
  surviving coarse ancestor, never on a detached occurrence.
  The selected-event facts display shall be a labelled region whose no-selection state
  and canonical field labels remain exposed to assistive technology without creating
  copies of descendant-owned facts.
- **Parents:** STK-001, STK-002, STK-003, STK-004, STK-005
- **Acceptance criterion:** Given an asymmetric depth-three event hierarchy and the
  SYSV-020 fixtures, the document exposes nested lists and native buttons but no custom
  tree/grid role. The skip link reaches the labelled SSA workspace; in an empty trace it
  reaches the explicit zero-event workspace and no phantom event or occurrence button
  exists. Tabbing onto any event changes no selection, anchor, row, or column;
  Enter/Space and their Shift
  variants reproduce the corresponding pointer transition exactly once. When a
  target is swallowed, focus lands on its selected ancestor; when only the anchor is
  swallowed, focus stays on the surviving target; later restoration moves no focus.
  Hidden descendants have no focus or accessibility node. Accessible row descriptions
  report the oracle event state, and the status region exactly matches the applicable
  zero-, singleton-, or plural-selection schema.
  Every definition and reference is a native occurrence button in column-major order
  whose name is its exact captured occurrence text and whose description has exact owner
  and column roles, while suffixes add no focus stop or accessible-name text.
  Keyboard activation reproduces every SYSV-022 overlay transition once. The overlay is
  a read-only region labelled with exact occurrence, entity, owner, and role identity;
  focus stays on the trigger when opened; and its temporary stop follows the trigger and
  can keyboard-scroll oversized content. Tab neither traps focus nor directly dismisses
  it, but any resulting external scroll follows SYS-022. A newly focused surviving
  outside control keeps focus; if the focused region is removed, the surviving anchor is
  instead focused and visible without another transition or provenance candidate.
  Escape follows the same surviving-focus precedence.
  Across the complete SYSV-021 identity, relation, shared/separate-handoff, and
  absent-state fixtures, keyboard focus produces the same exact visual occurrence set
  and an ordered accessible description containing stable entity, owner, and occurrence
  identity plus rendered labels; zero matches and an absent state remain distinct. With
  simultaneous pointer and keyboard candidates, the last-entered candidate alone owns
  the preview and ending it deterministically resumes the still-active candidate or
  clears. Enter/Space promotes pointer- or fallback-focused occurrences; Tab departure
  does not. Column removal, same-key control replacement, and both single/shared
  role-tuple transitions discard affected active and suspended candidates, and reversal
  or recreation revives none. Clear is reachable and natively activatable in every
  selection state, clears exactly once, retains focus on itself, announces the
  zero-selection schema, and leaves the labelled facts region in its explicit
  no-selection state.
- **Verification:** SYSV-023 (test)
- **Context:** [Viewer accessibility options](../../context/viewer-accessibility.md)
