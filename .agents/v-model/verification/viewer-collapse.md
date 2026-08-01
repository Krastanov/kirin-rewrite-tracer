# Event Subtree Collapse Verification

Reuse the asymmetric SYSV-020 tree fixture and its independent hierarchy and
displayed-row oracles.

## SYSV-026 — Verify the selection-subordinate collapse control

- **Covers:** SYS-025
- **Method:** test
- **Procedure:** Reuse the asymmetric SYSV-020 depth-three fixture under SYSV-018.
  Inventory every event row's controls, the collapse buttons' document order, their
  initial `aria-expanded`, disabled, marker, and accessible-name values, the rows each
  `aria-controls` target contains, and the sequential focus order, comparing all of them
  with independent parent/child, leaf, and displayed-row data. Install a mutation
  observer on the SSA column container.
  From no selection, collapse the depth-zero ancestor and record rows, announced status,
  accessibility nodes, sequential order, focused control, columns, and facts. Expand it,
  collapse the inner event, collapse the ancestor as well, expand only the ancestor, and
  finally expand the inner event, recording the collapse set and displayed rows after
  each step. Repeat one collapse and one expansion with `Enter` and with `Space` from
  keyboard focus while counting activations.
  Then select a grandchild and inspect each ancestor's and each unrelated branch's
  control state, accessible name, sequential presence, and computed disabled
  presentation; attempt pointer and direct programmatic activation of the disabled
  controls and of a control hidden inside a collapsed ancestor. Select the collapsible
  event itself, then Clear, comparing control state after each. Separately collapse a
  branch first and then select its collapsed root.
  Finally, with one branch collapsed, plain-click a preceding row, Shift-click a
  following row, and compare frontier, anchor, rows, status, and columns with an oracle
  that takes the inclusive interval over rows displayed under parent dominance and
  collapse. Repeat the nested-state sequence across both SYS-026 filter transitions.
  Activate Clear afterward and re-inspect the collapse set and rows.
- **Environment / configuration:** The declared headed Chrome for Testing environment
  with the same offline controls as SYSV-018, primary pointer click, Shift-click, and
  native `Enter`/`Space` keyboard activation.
- **Pass criterion:** Exactly the non-leaf events carry one collapse button, leaves carry
  none, each `aria-controls` names the list holding exactly that event's subtree rows,
  and every enabled button is the tab stop immediately before its event button.
  Collapsing hides every strict descendant at every depth, removes their accessibility
  nodes and tab stops, adds them to the announced hidden count, keeps focus on the
  control, and produces no SSA column mutation, column-role change, or facts change.
  Nested state is retained: expanding only the ancestor leaves the inner event
  collapsed, and expanding both restores the original order. Each `Enter` or `Space`
  reproduces the pointer transition exactly once.
  While any event in a subtree is selected, that subtree's controls are natively
  disabled, name themselves with the unavailable clause, leave sequential focus order,
  compute muted text with a dashed border, and change nothing under pointer or
  programmatic activation; a control hidden inside a collapsed ancestor is equally
  inert. Clear re-enables them. An event collapsed before selection stays collapsed with
  `aria-expanded` false and the unavailable name.
  Filtering never clears retained collapse state or makes it reveal a row hidden by
  another rule. The Shift range covers only displayed rows, so a collapsed root joins
  the frontier without its hidden descendants and the anchor stays displayed. Clear then empties the
  frontier and anchor, leaves the collapse set unchanged, keeps those rows hidden, and
  still announces them in the hidden count. No page network request, CSP violation, or
  console entry occurs.
- **Status:** implemented
- **Evidence:** [Pinned browser action audit](../evidence/browser-verification.md#action-audit)
- **Nonconformance:** The disabled, nesting, and range cases use the depth-three
  selection fixture only, so deeper branches and the incomplete-parent branch are not
  each exercised.
