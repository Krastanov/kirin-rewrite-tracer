# SSA Metadata Viewer Verification

Use asymmetric browser fixtures with independent snapshot, occurrence, metadata,
lifecycle, and geometry oracles.

## SYSV-022 — Verify SSA-value metadata suffixes and click overlays

- **Covers:** SYS-022
- **Method:** test
- **Procedure:** Display before and after states with named and unnamed result,
  block-argument, and multi-result definitions; repeated local and externally defined
  references; an operation-endpoint reference; identical-looking owners with different
  metadata; and one survivor whose type changes between snapshots. Use asymmetric hints
  and partial caller analysis containing truthy, falsey, empty, and `None` entries while
  omitting one owner. Include type records with printable text differing from `repr`, a
  failing printable path with distinct successful `repr` fallback, equal text from
  different Python classes, empty text, internal whitespace, and hostile text. Put
  different hostile key/value text in overlay-only metadata of the external reference.
  Include long unbroken and multiline inventory values exceeding both overlay bounds,
  and place eligible anchors near every viewport edge in the supported `640 × 480` CSS
  viewport.
  Freeze independent per-snapshot/entity oracles through direct IR inspection and the
  SYSV-007 path, then mutate the live survivor to sentinel type metadata before export.
  Include a SYSV-020 exact-equal dual-role handoff with definitions and repeated
  references, retaining independent oracles for both logical snapshot bindings. Inspect
  every role, suffix, color, and original interval; hover and click every occurrence; and
  inspect overlay placement, dimensions, overflow reachability, ownership, records,
  DOM, execution sentinel, and request log. Scroll the oversized overlay internally,
  then separately reopen it before scrolling the workspace, scrolling the page, and
  resizing the viewport. With two same-entity occurrences, another owner's occurrence,
  and anchors in
  removable columns, after each input and its DOM-mutation delivery, but before the next
  presentation opportunity or input, record open-overlay count, exact anchor, content
  owner, and displayed columns. Run this sequence: start closed; click each distinct
  occurrence; click the active occurrence; reopen; click a nested metadata record inside
  the overlay; click blank SSA content; reopen and press `Escape` twice; reopen, then
  remove and later restore its column. Repeat occurrence activation through a nested
  styled child of its identifier, and while open click a tree control whose independent
  oracle requires a selection and column change. On the exact-equal handoff, first select
  only `A`, open an overlay on an `A.after` occurrence, then add `B` so the occurrence is
  rendered in a shared `A.after`/`B.before` column. Drive this selection transition
  through browser-test state control that emits no pointer, keyboard, `Escape`, outside
  dismissal, or column-removal input. Open the overlay again in the shared column and
  use the same isolated control to remove `B`, returning it to single-role form, then add
  `B` again. Record the role tuple, anchor, and overlay state before and after every
  transition.
- **Environment / configuration:** The declared headed Chrome for Testing environment
  under the offline and hostile-content controls of SYSV-018 and SYSV-019.
- **Pass criterion:** Exactly one suffix is associated with each definition and none
  with any reference. Its sole trace-derived payload equals the exact snapshot-specific
  type-text oracle without normalization or truncation, uses the declared metadata color
  role, exposes no other retained field, and changes no captured character or interval.
  Empty type text stays empty while its fixed delimiter remains visibly marked; no
  suffix or overlay contains the later live sentinel. Hover opens nothing. From closed
  state, every definition and reference opens an overlay anchored to it containing all
  and only the complete inventory for its exact snapshot and entity owner. It is eight
  pixels above when that measured box fits and otherwise eight pixels below, its inline
  position is clamped to eight-pixel viewport margins, it never covers the anchor, and
  its complete box remains in the viewport at or below the declared maximum dimensions.
  Internal scrolling reaches every oversized record and leaves the overlay open;
  workspace/page scrolling and viewport resizing close and clear it before another
  presentation. Equal-looking owners never cross-associate and omitted analysis stays
  absent. At every lifecycle
  checkpoint zero or one overlay is open. A different exact occurrence, including one
  for the same entity, atomically becomes the sole anchor with matching content; the
  active occurrence toggles closed. Inside clicks preserve it; outside clicks and
  `Escape` close it without blocking the outside action; repeated `Escape` is inert.
  Each nested-identifier click causes exactly one lifecycle transition, a nested overlay
  click preserves the overlay, and the tree click both dismisses it and produces the
  expected selection and columns. Column removal leaves no overlay, anchor, or stale
  content, and restoration does not reopen it. Hostile suffix and overlay content create
  no interpreted element, attribute, style, or URL, execute nothing, and initiate no
  request. Each shared handoff occurrence and definition suffix renders once, its one
  anchor remains associated with both exact state roles, its common metadata inventory
  renders once, and neither retained logical binding is discarded or reassigned. Both
  single-to-shared and shared-to-single transitions close and clear the anchor before
  presenting the new workspace even though content, entity, and occurrence are equal.
  This occurs without another dismissal input. Neither the immediate nor a later reverse
  transition migrates or reopens the overlay.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None
