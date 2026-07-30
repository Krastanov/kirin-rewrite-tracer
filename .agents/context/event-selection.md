# Event Tree Selection

- **Context need:** Explanation
- **Open when:** Designing, implementing, or reviewing event-row clicks, contiguous
  range selection, parent dominance, descendant hiding, or selection restoration.
- **Do not open when:** Working only on SSA-column equality, provenance hover, metadata
  interaction, export composition, or trace capture.
- **Related specification IDs:** SYS-020
- **Review when:** Selection gestures, range-anchor behavior, dominance, restoration,
  or selection accessibility changes.

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

A plain click is replacement, not a toggle: clicking the selected singleton keeps it
selected, while clicking one member of a larger frontier collapses to that member.
Repeated Shift-clicks retain the current anchor and replace rather than union with the
previous range. Ctrl and Meta do not alter the plain-versus-Shift choice; Shift still
selects the range when either is also held.

For Shift, snapshot all rendered event rows immediately before the action, take the
inclusive interval regardless of direction, then remove every candidate with another
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
overlays, and other detail state. No disclosure control, pointer target, keyboard target,
or accessibility target exposes descendants while that parent is selected. The
retained event tree itself remains unchanged.

When a later selection excludes the parent, its descendants return at their exact
hierarchical positions, eligible but unselected and without stale state. Because a
Shift range uses pre-action visible rows, descendants restored by that action cannot
silently join the range just computed. A selected subtree consequently behaves as one
coarse unit and creates neither a visible range gap nor descendant columns.

Visible-but-inert descendants were rejected because they require disabled pointer,
keyboard, and accessibility semantics. Independent disclosure adds another state
machine and permits mixed detail levels. Ctrl/Cmd toggling and drag selection add
disjoint or geometry-dependent cases without serving the consecutive-column model.
The native-button keyboard mapping and exact focus fallback are separated in the
[viewer accessibility model](viewer-accessibility.md); the selected-row cue belongs to
the [viewer cascade](viewer-styling.md).
