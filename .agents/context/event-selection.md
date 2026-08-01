# Event Tree Selection

- **Context need:** Explanation
- **Open when:** Designing, implementing, or reviewing event-row clicks, contiguous
  range selection, parent dominance, descendant hiding, subtree collapse, unchanged
  filtering, or selection restoration.
- **Do not open when:** Working only on SSA-column equality, provenance hover, metadata
  interaction, export composition, or trace capture.
- **Related specification IDs:** SYS-020, SYS-025, SYS-026
- **Review when:** Selection gestures, range-anchor behavior, dominance, collapse
  eligibility, unchanged filtering, restoration, or selection accessibility changes.

The confirmed view keeps the retained event hierarchy as a tree in its first column. A
flat list loses wrapper structure, while an arbitrary set of checked events permits
disjoint columns with unclear handoffs. V1 therefore uses one deterministic contiguous
selection reducer.

## Small selection reducer

The disposable view state is `(frontier, anchor)`. `frontier` is an ancestor-free set of
selected visible events. `anchor` starts null and otherwise names one selected visible
frontier event.

| Input | Replacement frontier | New anchor |
| --- | --- | --- |
| Plain primary click on `T` | `{T}` | `T` |
| Shift-click `T` with a null anchor | `{T}` | `T` |
| Shift-click `T` with anchor `A` | Inclusive `A..T` interval in pre-action visible order, normalized for parent dominance | Retain `A`, or rebase it to its surviving selected ancestor |
| Ctrl/Meta-click | Same as plain click unless Shift is also held | Same as the corresponding plain or Shift action |
| Pointer movement or drag without click | Unchanged | Unchanged |
| Native Clear selection | Empty | Null |
| Native collapse toggle | Unchanged | Unchanged |
| Native unchanged filter | Remove concealed frontier events | Retain if it survives; otherwise first survivor or null |

A plain click is replacement, not a toggle: clicking the selected singleton keeps it
selected, while clicking one member of a larger frontier collapses to that member.
Repeated Shift-clicks retain the current anchor and replace rather than union with the
previous range. Ctrl and Meta do not alter the plain-versus-Shift choice; Shift still
selects the range when either is also held.
Clear is always available and is the explicit route back to zero selection. It restores
all rows and removes every column, hover, overlay, and descendant-derived state while
leaving focus on its native button. It does not change the non-toggle row rule.

The collapse toggle appears in this table only to record that it is not a selection
input; its own rules are below.

For Shift, snapshot all rendered event rows immediately before the action after every
active hiding rule, take the inclusive interval regardless of direction, then remove
every candidate with another
candidate as an ancestor. Only after that normalization may rendering hide descendants
and build columns. This order avoids changing the coordinates while computing the
range. If a selected ancestor swallows the anchor, rebase to that unique surviving
ancestor; keeping an invisible anchor would require hidden interaction state, while
clearing it would make the next Shift-click unexpectedly act like a first click. A
swallowed target needs no second identity in the selection: its selected ancestor is
the coarse representative.

## Parent dominance and restoration

A selected parent removes every strict descendant row before presentation, not merely
the descendant's selection styling. It also removes descendant columns, highlights,
overlays, and other detail state. No pointer target, keyboard target, accessibility
target, or *enabled* disclosure control exposes descendants while that parent is
selected. The retained event tree itself remains unchanged.

When a later selection excludes the parent, its descendants return at their exact
hierarchical positions, eligible but unselected and without stale state. Because a
Shift range uses pre-action visible rows, descendants restored by that action cannot
silently join the range just computed. A selected subtree consequently behaves as one
coarse unit and creates neither a visible range gap nor descendant columns.

Visible-but-inert descendants were rejected because they require disabled pointer,
keyboard, and accessibility semantics. Ctrl/Cmd toggling and drag selection add
disjoint or geometry-dependent cases without serving the consecutive-column model.
The native-button keyboard mapping and exact focus fallback are separated in the
[viewer accessibility model](viewer-accessibility.md); the selected-row cue belongs to
the [viewer cascade](viewer-styling.md).

## Subordinate subtree collapse

SYS-025 adds one disclosure control per non-leaf row for navigating a large hierarchy.
An unconstrained disclosure was rejected earlier because a second state machine can
contradict parent dominance, hide the selected frontier, hide the range anchor, or
silently change which rows a Shift range covers. Three properties remove each of those
failures, so collapse stays subordinate to selection rather than competing with it:

1. **Collapse only ever hides.** A row is displayed exactly when no selected ancestor,
   collapsed ancestor, or unchanged-filtered ancestor hides it. Because the three rules
   compose as a union, no collapse state can reveal a row that another rule hides, and
   SYS-020's "no disclosure state reveals a hidden descendant" clause still holds.
2. **The control is enabled only when its whole subtree, including the event itself,
   holds no selected event.** A disabled native button leaves the tab order and rejects
   pointer, keyboard, and programmatic activation, so no collapse transition can hide a
   frontier member. Since the anchor is always a frontier member, it cannot be hidden
   either, and the `(frontier, anchor)` invariants are preserved by construction rather
   than by repair.
3. **Collapse owns nothing else.** A transition changes no frontier, anchor, column,
   highlight, overlay, or canonical fact, so it repaints only the event hierarchy.
   Clear owns selection and leaves collapse alone; collapse owns disclosure and leaves
   selection alone.

Collapse state is per event, retained while its row is hidden, and reapplied when an
ancestor expands, which is the ordinary expectation for a hierarchy and avoids a hidden
reset rule. It is view state for one open document, not persisted UI state.

The mixed-detail concern that motivated the earlier rejection remains bounded: a
collapsed subtree contributes only its collapsed root to a Shift range, so the coarse
unit a user sees is exactly the coarse unit the reducer uses.

## Document-local unchanged filtering

Snapshot equality and `has_done_something` each provide only one signal. Classify a
complete event as unchanged only when exact retained snapshot semantics agree and the
result flag is false; classify it as changed only when both signals affirm change. A
signal disagreement is inconsistent, not a no-op, and an incomplete event has no output
signal to classify as unchanged. The viewer marks those four states without changing
the canonical event model.

One native toggle hides each confirmed unchanged row and its entire subtree. Hiding only
the row would detach its children from the visible hierarchy, so filter, collapse, and
parent dominance all use the same monotonically hiding union. Collapse state is retained
under a filtered branch.

Filtering is the only hiding transition allowed to reconcile selection. Remove every
concealed frontier event, retain a surviving anchor, otherwise rebase to the first
surviving frontier event, and clear both when nothing survives. Removed selections are
not restored with the rows. The toggle remains disposable state for one open document;
Clear owns only selection and leaves it unchanged.
