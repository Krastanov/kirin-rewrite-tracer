# Event Selection and SSA Column Verification

Use asymmetric browser fixtures with independent tree, snapshot, and interaction-state
oracles. This action remains blocked until the viewer and test exist.

## SYSV-020 — Verify event-tree selection and SSA columns

- **Covers:** SYS-020
- **Method:** test
- **Procedure:** Under SYSV-018, render unrelated event IDs in visible order
  `R9, C4, G8, C1, S7, D2, T0`, with `C4` below `R9`, `G8` below `C4`, and `D2` below
  `S7`. Distribute complete, no-op, caught-incomplete, and incomplete-parent cases
  across the tree. Give every event non-shareable tagged snapshots and give descendants
  metadata, provenance, effects, and stacks absent from their parents. Compare the
  initial tree with independent event-ID, parent, sibling-order, and completion-state
  data. Start the interaction oracle with a null anchor and issue no prior selection
  input. First Shift-click `T0`; then plain-click `G8`, Shift-click `D2`, and Shift-click
  `C1`.
  Reset with plain `G8`, Shift-click `C4`, then Shift-click `S7`. Independently exercise
  forward and reverse expansion, contraction, and return to the anchor. Build a
  multi-event selection, plain-click one selected member, and click that resulting
  singleton again. From a multi-event frontier anchored at `G8`, Ctrl-click unselected
  `T0` twice. Reset with plain `G8`, Ctrl+Shift-click `D2`, then Shift-click `C1`.
  Repeat both sequences with Meta in place of Ctrl. Dispatch pointer movement and drag
  without a click, then Shift-click. After each action compare the frontier, anchor, and
  rendered rows with an oracle that snapshots pre-action visible order, takes the
  inclusive anchor-target interval, normalizes parent dominance, and updates visibility
  only afterward.
  With child metadata and provenance detail active, select its parent; inventory rows
  and pointer, keyboard, selection, and accessibility targets; and look for an
  independent descendant-disclosure control. Exclude the parent through a subsequent
  selection and compare restoration with the original hierarchy and order. Repeat at
  child/grandchild depth and with the incomplete parent.
  Then exercise complete/no-op/complete with two equal handoffs, an incomplete
  predecessor, and a complete predecessor followed by an incomplete successor with an
  equal before state. Compare columns with an independent semantic snapshot oracle.
  Parameterize one-field differences in root binding, text, effective style, entity,
  occurrence role/interval/multiplicity, metadata presence/value/status, schema, and
  capture configuration. Also vary only event-level provenance, effect, or stack
  records, and encode one equal effective-style sequence with different normalized
  style layouts. Inspect embedded trace records after each view.
- **Environment / configuration:** The declared headed Chrome for Testing environment,
  with controls for primary pointer click, Shift-, Ctrl-, Meta-, and combined-modifier
  clicks and click-free pointer drag; the same offline controls as SYSV-018.
- **Pass criterion:** Initially every event appears once with correct hierarchy, order,
  and status in one tree column left of every SSA column. The first Shift-click selects
  only `T0`. Plain `G8`, Shift `D2` yields frontier `G8, C1, S7`: the candidate interval
  was `G8, C1, S7, D2`, but selected `S7` hides `D2`. The next Shift `C1` replaces that
  frontier with `G8, C1`; `D2` is restored unselected and does not enter the just-computed
  range. Forward, reverse, expanding, contracting, and anchor-return cases all use the
  same inclusive pre-action order and retained anchor.
  Plain `G8`, Shift `C4` leaves only `C4`, hides `G8`, and rebases the anchor to `C4`;
  Shift `S7` then selects `C4, C1, S7`, proving the anchor was neither cleared nor kept
  hidden. A swallowed target is represented only by its selected ancestor.
  Plain-clicking a selected member leaves it as the singleton and repeating the click
  never empties the selection. Ctrl/Meta-clicking `T0` yields singleton `T0` anchored at
  `T0`, and repeating it stays nonempty. Ctrl/Meta+Shift from `G8` through `D2` yields
  exactly `G8, C1, S7` anchored at `G8`; the following Shift `C1` proves that anchor was
  retained. Drag alone changes neither selection nor anchor.
  Selecting an ancestor atomically removes selected descendants and hides every strict
  descendant row at every depth before presentation; no descendant control,
  interaction/accessibility target, or disclosure mechanism remains. Descendant
  columns, highlights, and overlays clear. Only the parent's before then
  after-or-absent pair appears, and child-only content stays absent. Excluding the parent
  restores every row at its exact original position, eligible but unselected and without
  stale state. An incomplete parent has only its before state and explicit absent-after
  indication.
  Each exactly equal handoff appears once with an always-visible header naming both
  event IDs, exact roles, and shared-by-equality status, while both logical bindings
  remain retained. Every payload near-miss stays separate; equivalent effective-style
  normalization and event-level-only differences do not block sharing. The no-op middle
  event retains two distinct two-role handoff columns. An absent predecessor after-state
  never shares, while an incomplete successor's existing before-state may share with an
  equal predecessor after-state.
- **Status:** blocked
- **Evidence:** None
- **Nonconformance:** No viewer implementation or durable test exists.
