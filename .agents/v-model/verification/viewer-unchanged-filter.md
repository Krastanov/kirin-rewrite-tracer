# Unchanged Event Classification and Filter Verification

Use independent snapshot-equality, result-flag, hierarchy, selection, accessibility,
and computed-style oracles over the same inert exported payload.

## SYSV-027 — Verify unchanged classification and subtree filtering

- **Covers:** SYS-026
- **Method:** test
- **Procedure:** Under SYSV-018, export a trace containing confirmed changed and
  unchanged events, both inconsistent signal directions, an incomplete event, and an
  unchanged non-leaf with a changed child. Independently compare snapshot semantics and
  `has_done_something`, then inspect every row attribute, visible label, accessible
  description, computed style, and ordinary style attribute. Inspect the filter's
  native type, initial/disabled state, text, `aria-pressed`, `aria-controls`, sequential
  position, focus, and activation count for pointer, Enter, and Space. Repeat with an
  empty trace and a complete trace having no unchanged events.
  Toggle filtering in fresh documents and after nested collapse, parent-dominant
  selection, unchanged singleton selection, a mixed range with a surviving anchor, a
  mixed range whose anchor is removed, and a fully removed frontier. At each transition
  record visible and hidden rows, collapse set, frontier, anchor, status, focus,
  columns, facts, metadata overlay, provenance marks, accessibility nodes, embedded
  payload text, and a serialization of decoded canonical data. Disable the filter again
  and inspect restored rows and retained collapse. While filtering is on, compute
  forward and reverse Shift ranges over the independent pre-action displayed order,
  including equal neighboring handoffs and an incomplete event. Activate Clear while
  filtering remains on. Monitor requests, CSP violations, and console output.
- **Environment / configuration:** The declared headed Chrome for Testing environment
  with the offline controls of SYSV-018, browser accessibility-tree inspection, native
  keyboard and pointer activation, and exact sRGB computed styles.
- **Pass criterion:** All four classifications follow the two-signal truth table;
  incomplete is never unchanged. Confirmed unchanged rows alone compute the muted
  presentation while selected and focus cues remain exact, no row has inline
  presentation, and each inconsistent direction has the exact visible badge and
  applicable accessible sentence. The filter is one native document-local toggle with
  exact labels, relationships, pressed/disabled state, keyboard parity, and retained
  focus.
  Its enabled state hides each unchanged event and complete descendant subtree from DOM
  presentation, focus order, and accessibility tree while preserving inconsistent and
  incomplete rows. Hidden counts equal the three-rule union; collapse and parent
  dominance compose without revealing and collapse state survives restoration.
  Selection reconciliation removes every concealed event, retains all surviving ordered
  pairs and a surviving anchor, otherwise rebases to the first survivor or clears to
  null. Restored rows are unselected. Forward and reverse Shift ranges contain exactly
  the pre-action displayed rows and their expected ordered before/after columns,
  including exact two-role handoffs. Clear does not change the filter. Payload text and
  canonical arrays never change; no request, CSP violation, or console error occurs.
- **Status:** implemented
- **Evidence:** `test/test_viewer_unchanged.py`
- **Nonconformance:** The implementation fixture covers the declared pinned browser but
  is not yet included in a new durable pinned-browser audit artifact.
