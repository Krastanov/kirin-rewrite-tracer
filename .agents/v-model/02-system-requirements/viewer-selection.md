# Event Selection and SSA Column Requirements

The event tree, deterministic contiguous selection, automatic descendant-row hiding,
parent-dominant logical event pairs, and exact-equal handoff columns are confirmed.
Subtree collapse is specified by SYS-025; keyboard/focus behavior and visual
presentation are specified by SYS-023 and SYS-024.

## SYS-020 — Present an event-tree and contiguous SSA workspace

- **Normative statement:** The view shall assign each retained event one node in a
  leading ordered parent-child tree. It shall model selection as an ancestor-free
  frontier plus a range anchor that is either null or identifies one selected, visible
  frontier event; that anchor shall be null before the first selection input. A plain
  primary click on an eligible visible event row shall replace the frontier with that
  event alone and set it as the anchor. Clicking the sole selected event shall keep it
  selected; clicking a selected member of a multi-event frontier shall reduce the
  selection to that singleton.
  A Shift-primary-click shall first snapshot the complete rendered event-row order
  immediately before the action. With a null anchor it shall behave as a plain click.
  Otherwise it shall replace the prior selection with the inclusive visible-row
  interval between anchor and target, in either direction. Before changing the
  presentation, the view shall normalize that candidate interval by removing every
  candidate having another candidate as an ancestor. Repeated Shift-clicks shall
  replace, not add to, the prior range and retain the anchor while it remains visible.
  If normalization selects an ancestor that hides the anchor, the anchor shall
  atomically rebase to the unique surviving selected ancestor. A target hidden by the
  same normalization shall receive no special preservation; its selected ancestor is
  its coarse representative. Restored descendants were absent from the pre-action order
  and shall remain unselected outside the just-computed range.
  Ctrl and Meta shall not alter the plain-versus-Shift choice: either without Shift shall
  follow plain-click behavior, and either combined with Shift shall follow Shift-click
  behavior. Pointer movement or drag without a click shall not change tracer selection.
  Selecting an event shall atomically deselect strict descendants, clear their derived
  state, and hide their rows transitively before presentation. Hidden descendants shall
  expose no row, enabled disclosure control, or manual or accessibility target; no
  disclosure state, including the independent SYS-025 collapse state, shall reveal them
  while the ancestor is selected. A later action that excludes that ancestor shall
  restore the original hierarchy and order, eligible but unselected, without stale
  state, except for rows the SYS-025 collapse state still hides. Selected events or
  coarse subtree units shall form one consecutive displayed tree range; hidden
  descendants shall create neither a gap nor a state.
  An always-available native `Clear selection` button shall atomically empty the
  frontier, set the anchor to null, clear every derived column, highlight, overlay, and
  descendant state, and restore every event row that the SYS-025 collapse state does not
  hide, unselected. Clear owns selection alone and shall leave that collapse state
  unchanged. Clear shall remain available with zero selection and repeated activation
  shall be idempotent. It shall not change the confirmed non-toggle behavior of
  event-row activation.
  To the right, each frontier event shall retain its logical styled `before` then
  `after`, or explicit absent-after, pair. At a boundary between consecutive selected
  events `A` and `B`, the view shall render `A.after` and `B.before` once as one
  dual-role shared column if and only if `A.after` exists and their complete retained
  snapshot payloads are exactly equal. Equality shall cover every retained field and
  association, including root, schema/configuration, text, styles, entities,
  occurrences, metadata, ownership, and multiplicity. It shall exclude only record
  identity and event/state association; provenance, effects, and stacks are not payload.
  Different style-table IDs or span segmentation shall compare equal only when every
  code point has equal effective style. While displayed, an always-visible textual
  column header shall identify both event IDs, the exact roles `A.after` and `B.before`,
  and mark the column as shared or collapsed by exact equality. Both logical snapshots
  and owner associations shall remain separately retained and addressable. Otherwise
  the two roles shall use separate columns. The view shall never share an event's own
  before and after roles, treat an absent after state as an empty snapshot, or
  transitively fuse adjacent handoffs; one shared column shall have exactly two state
  roles.
- **Parents:** STK-001, STK-002, STK-004, STK-005
- **Acceptance criterion:** Given an asymmetric visible order with unrelated event IDs,
  plain click selects exactly its target and establishes the anchor; Shift-click
  inclusively expands, contracts, and reverses from that anchor while replacing the old
  range. A first Shift-click behaves as plain click. Plain-clicking a selected singleton
  leaves it selected, and plain-clicking a member of a larger selection leaves only that
  member. Ctrl/Meta clicks never toggle or add, Ctrl/Meta+Shift matches Shift, and drag
  alone changes neither frontier nor anchor. When a range includes a parent and child,
  the parent wins before presentation. A swallowed anchor rebases to that parent and a
  subsequent Shift-click extends from the rebased anchor; a swallowed target has only
  the parent as its coarse representative. Excluding the parent restores every
  descendant at its original position, unselected and absent from the range just
  computed from the pre-action visible rows.
  In an asymmetric depth-three tree with complete, no-op, and incomplete events,
  initial hierarchy and order match independent data. Selecting a leaf then its
  ancestor removes every strict descendant row and target, clears descendant detail and
  columns, exposes no enabled disclosure mechanism, and leaves only the ancestor pair. A
  nondescendant sibling remains eligible. In a consecutive coarse range, separately
  retained exact-equal `A.after` and `B.before` payloads produce exactly one
  always-visible dual-labelled shared column while their two logical records and
  bindings remain intact. Exact text with any root, effective-style, entity, occurrence,
  metadata, schema, or capture-configuration difference remains in two columns;
  event-level provenance, effect, or stack differences alone do not prevent sharing.
  Equivalent normalized style encodings still share. A no-op middle event can produce
  two distinct two-role handoff columns but never one transitive multi-role column. An
  incomplete left event cannot share its absent after state; an incomplete right event
  may share its existing before state with an equal predecessor after state. No
  incomplete event acquires an after state. Activating Clear from singleton,
  multi-event, parent-dominant, and already-clear states yields an empty frontier and
  null anchor, restores every row collapse does not hide in original order, leaves the
  collapse state unchanged, and removes all derived state; selecting a row afterward
  starts from a null anchor while repeated Clear is inert.
- **Verification:** SYSV-020 (test)
- **Origin / risk:** Developer confirmations, 2026-07-30; post-action range coordinates,
  additive or toggling gestures, hidden anchors, exposed descendant controls, stale
  restoration, or inexact and unlabelled coalescing can make the same action select or
  attribute different rewrites.
- **Context:** [Event-selection options](../../context/event-selection.md) and
  [interactive trace viewer options](../../context/interactive-trace-viewer.md)
