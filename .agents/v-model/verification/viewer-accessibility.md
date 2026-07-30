# Viewer Keyboard and Focus Verification

Use the same independent selection, provenance, metadata, DOM-order, focus, and
accessibility-tree oracles as the pointer actions. Do not treat visual screenshots as
the keyboard or accessibility oracle.

## SYSV-023 — Verify native keyboard operation and focus lifecycle

- **Covers:** SYS-023
- **Method:** test
- **Procedure:** Open the empty trace and the asymmetric SYSV-020 through SYSV-022
  fixtures under SYSV-018 in fresh documents, including a nonempty trace before any
  event is selected. Inspect the DOM and browser accessibility tree for the skip link,
  zero-event or no-selection workspace target, nested event lists, event buttons,
  labelled SSA workspace and column regions, occurrence buttons, selected-state
  descriptions, polite status region, and absence of custom tree/grid roles. Use
  keyboard input only to follow the skip link and to traverse all visible event controls
  with `Tab` and `Shift+Tab`; record focus,
  selection, range anchor, rendered rows, columns, accessibility nodes, and status text
  after every focus move. On each event fixture, activate representative rows with
  Enter, Space, Shift+Enter, Shift+Space, and the existing Ctrl/Meta combinations, while
  guarding against a native click plus a second custom activation. Exercise separately
  a swallowed target, a swallowed anchor with surviving target, parent exclusion and
  descendant restoration, and an incomplete selected parent. While a descendant is
  hidden and after it is restored, inventory its DOM button, accessibility node, native
  tab stop, selected state, document order, and focus.
  Traverse every kind of SSA definition and reference in column-major order, including
  repeated occurrences and both roles of a shared handoff. Compare each accessible
  name with the exact captured occurrence interval and compare its description with
  independent occurrence, owner, and state-role data. Verify that the adjacent suffix
  is outside the name subtree. Activate metadata with
  Enter and Space; while it is open, Tab forward and backward through its temporary
  stop, keyboard-scroll an oversized inventory, press Escape from the trigger, focused
  region, and another control, toggle the trigger, replace it from another occurrence,
  remove its column through a keyboard event-row action, and trigger each SYS-022
  geometry-driven close while the region is focused.
  Inspect the overlay's role, occurrence/entity/owner/role label, key/value structure,
  `aria-expanded`, `aria-controls`, focus target, and detached-node state at every
  transition. From its focused temporary stop, trigger Escape and each geometry close;
  record focus, preview, page and workspace scroll positions, and whether the anchor is
  visible after focus settles. Tab from the anchor to an offscreen next control so the
  browser scrolls the workspace.
  Focus each SYSV-021 provenance case through keyboard navigation and compare its
  visual and accessible neighbor projection with the hover oracle, including each
  neighbor role and every related occurrence's stable entity ID, owner ID, occurrence
  ordinal, and rendered label in display order. Keep keyboard focus on `Y`, enter and
  leave pointer hover on `X`, refocus `Z` while the pointer remains parked, and end
  candidates in both orders. Give an occurrence pointer-induced focus without hover,
  then use Tab away; separately return it programmatic fallback focus after closing the
  focused overlay. Direct the first Enter or Space activation to each. While pointer and
  keyboard
  candidates alternately own or are suspended, remove their columns and perform both
  single-to-shared and shared-to-single ordered role-tuple transitions through isolated
  state control; also replace a candidate's DOM control with a new equal-key control.
  Reverse every transition without another pointer or focus entry.
  Include no-match, repeated, shared-column, identity-only handoff, selected-mutation,
  absent-after, and present-neighbor-with-zero-match cases.
- **Environment / configuration:** The declared headed Chrome for Testing
  `151.0.7922.47`, revision `r1654411`, `linux64` environment under SYSV-018, with real
  keyboard and pointer event sequences and browser accessibility-tree inspection.
- **Pass criterion:** The first focusable control is a working skip link. In the empty
  trace it reaches the explicit zero-event workspace and no event or occurrence button
  exists; in the nonempty no-selection trace it reaches the labelled empty SSA workspace
  without selecting an event or inventing an SSA occurrence. Event hierarchy is exposed
  through nested lists and native buttons in displayed depth-first order, with no
  `tree`, `treegrid`, roving focus, or independent descendant-disclosure control. Focus
  traversal alone changes no selection, anchor, row, or column.
  Enter/Space and their Shift/Ctrl/Meta combinations each produce exactly one transition
  equal to the corresponding SYSV-020 pointer oracle. Row descriptions give the exact
  event, hierarchy/completion, and selection state. Polite status text uses exactly the
  SYS-023 zero-, singleton-, or plural-selection field order and values.
  A surviving target retains focus; a swallowed target transfers focus to its unique
  selected ancestor; swallowing only the anchor leaves focus on the target. Hidden and
  later-restored descendants have no stale accessibility node, tab stop, selection, or
  focus: while hidden they expose no node or stop, and when restored exactly one button
  and corresponding node reappear unselected in original order without receiving focus.
  Every occurrence is one native button in column-major order with exact role, owner,
  and column description; its name equals its exact captured interval, a shared
  occurrence names both state roles, and its adjacent suffix adds neither a stop nor
  accessible-name text. Enter/Space reproduces SYSV-022 once. The read-only overlay's
  label has the exact occurrence label, stable entity and owner IDs, and ordered role
  tuple, and it exposes semantic key/value data and the correct control relationship
  without moving or trapping focus. Its sole temporary stop follows the anchor, can
  scroll every record, and disappears when closed. Tab is not a dismissal input, though
  an induced external scroll closes under SYS-022. A newly focused surviving outside
  control keeps focus; if the region itself was newly focused and then removed, focus
  returns to a visible surviving anchor. Escape follows the same precedence, and any
  focus-induced scroll causes no second state transition. Column removal leaves no
  detached focus or node.
  Keyboard provenance equals the exact SYSV-021 visual oracle. Its accessible
  description names each immediate neighbor role and every related occurrence's stable
  entity ID, owner ID, one-based neighbor-column ordinal, and rendered label in display
  order. It distinguishes a present neighbor with zero matches from an absent SSA state.
  Exactly one last-entered active candidate owns the preview; ending it resumes only the
  still-active candidate or clears, with no overlap or stale highlight. Pointer-induced
  or programmatic fallback focus alone creates no keyboard preview, Tab departure causes
  no transient promotion, and the first Enter/Space activation promotes before exactly
  one normal action. Removal or replacement of either an owning or suspended
  candidate's control, occurrence, or ordered role tuple discards it; neither reversing
  a column removal, reversing either role-tuple transition, nor recreating an equal-key
  control revives it.
- **Status:** blocked
- **Evidence:** None
- **Nonconformance:** No viewer implementation or durable browser/accessibility test
  exists.
