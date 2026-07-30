# SSA Metadata Viewer Requirements

The type-only, definition-only suffix and single-overlay click, dismissal, removal, and
column-role transition lifecycle are confirmed. Keyboard/focus behavior and the exact
suffix presentation are specified by SYS-023 and SYS-024.

## SYS-022 — Disclose SSA-value metadata through suffixes and click overlays

- **Normative statement:** Each rendered SSA-value occurrence retained with role
  `definition` under SYS-013 shall carry exactly one compact metadata suffix outside the
  captured SSA characters and occurrence interval. Its sole trace-derived payload shall
  be the exact representation text selected under SYS-007 for that SSA entity's `type`
  retained under SYS-005 in that snapshot; no name, hint, caller-analysis entry, Python
  type label, representation status, provenance, or derived summary shall appear in the
  suffix. Each suffix shall include a fixed, non-trace-derived delimiter and use a
  visibly distinct metadata color role. When retained type text is empty, the delimiter
  shall remain visibly marked without substituting type text. A `reference` occurrence
  shall carry no suffix. Clicking a rendered `definition` or `reference` occurrence that
  is not the active anchor shall expose, in an overlay anchored to it, all and only
  the complete SYS-005/SYS-007 inventory for that exact snapshot-and-SSA-entity pair:
  name or name absence, type, every hint, and every explicitly supplied caller-analysis
  entry with their retained representation fields. The overlay shall use an eight-pixel
  gap and prefer placement immediately above its occurrence, fall below only when its
  measured box would not fit above, and clamp its inline position to eight-pixel
  viewport margins without covering the occurrence. It shall have maximum width
  `min(36rem, calc(100vw - 1rem))`, maximum height
  `min(20rem, calc(50vh - 2rem))`, and internal overflow scrolling so its complete box
  stays within the supported viewport. Any viewport resize or scroll originating
  outside the overlay shall close it and clear its anchor before the next presentation;
  scrolling the overlay's own inventory shall not. The view shall initialize with no
  metadata overlay open and shall expose at most one. Its active anchor is the exact
  rendered occurrence, not merely its SSA entity. Clicking the active occurrence shall
  close it; clicking a different eligible occurrence shall atomically replace its anchor
  and owner-correct content without exposing two overlays. An eligible-occurrence click
  shall take precedence over outside dismissal. A click within the overlay shall leave
  it open; a click within neither the overlay nor an eligible occurrence shall close it
  without suppressing the clicked target's action. `Escape` shall close an open overlay
  and otherwise leave this state unchanged. Removing the anchor's SSA column shall close
  the overlay and clear its anchor in the same workspace transition; restoring that
  column shall not reopen it. A displayed column's exact lifecycle identity shall include
  its ordered tuple of logical state-role bindings. Changing that tuple shall count as
  removing the old column, including a transition between single-role `A.after` and
  dual-role `A.after`/`B.before`: the overlay and anchor shall clear before the new
  workspace is presented and shall not migrate to an otherwise equal occurrence.
  Recreating either role tuple later shall not reopen it. Pointer hover alone shall not
  open it. Suffix and overlay content shall preserve owner association and remain inert
  under SYS-019. In a dual-role handoff column under SYS-020, each common occurrence and
  its definition suffix shall render once. Its single anchor shall retain both equal
  logical snapshot/entity bindings, and its overlay shall expose their common inventory
  once without choosing, merging, or reassigning either binding.
- **Parents:** STK-001, STK-004, STK-005
- **Acceptance criterion:** Given result and block-argument definitions, repeated and
  externally defined references, identical rendered names with different owners, a
  snapshot-specific type change, asymmetric hints and falsey analysis, printable and
  `repr` representations, empty and hostile type text, and hostile overlay-only metadata,
  every definition has one colored suffix whose only trace-derived payload is its exact
  snapshot-specific type text, no reference has a suffix, and an empty payload remains
  empty beside its visible fixed delimiter. Captured SSA text and occurrence intervals
  are unchanged. Hovering opens no overlay. Given two occurrences of one entity, another
  owner's occurrence, and an anchor column removable by selection, the sequence closed,
  first click, other same-entity occurrence, other owner, active-anchor click, reopen,
  inside click, outside click, reopen, `Escape`, reopen, remove column, and restore column
  always leaves zero or one correctly anchored overlay. Replacement changes anchor and
  content together; same-anchor, outside, `Escape`, and removal close it; inside click
  preserves it; and neither restoration nor repeated `Escape` revives stale state. Every
  opened overlay contains all and only its complete owner-specific inventory without
  reassociation, execution, interpreted markup or style, or a resource request. A shared
  handoff occurrence has one suffix and one anchor associated with both state roles, and
  shows the exactly equal inventory once while both logical bindings remain intact.
  Changing an anchored column from single to shared or shared to single closes and clears
  the overlay before presentation despite equal content and entity identity; reversing
  either transition does not migrate or revive it. Edge-positioned anchors and an
  inventory exceeding the overlay bounds keep the entire overlay box visible, preserve
  the eight-pixel anchor gap, and make every record reachable by internal scrolling.
  Internal scrolling preserves the disclosure, while workspace/page scrolling or a
  viewport resize closes it without leaving a stale anchor.
- **Verification:** SYSV-022 (test)
- **Origin / risk:** Developer confirmation, 2026-07-30; detached, migrated, or
  hover-only metadata can be lost, obscured, or associated with the wrong visually
  identical SSA value.
- **Context:** [Interactive trace viewer options](../../context/interactive-trace-viewer.md)
