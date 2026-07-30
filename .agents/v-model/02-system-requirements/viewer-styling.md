# Viewer Styling Requirements

V1 has one fixed dark presentation. Viewer chrome uses a semantic cascade; captured SSA
styles remain faithful and separate.

## SYS-024 — Use a fixed accessible dark presentation and shared cascade

- **Normative statement:** The exported viewer shall use this fixed sRGB palette for
  viewer-authored presentation: canvas `#0B1020`, surface `#111827`, raised surface
  `#1F2937`, primary text `#F3F4F6`, muted text `#CBD5E1`, border `#94A3B8`, selected
  background `#1E3A5F`, selected marker `#93C5FD`, metadata `#7DD3FC`, provenance
  `#FBBF24`, and keyboard focus `#F472B6`. Normal-size viewer-authored text shall have
  at least 4.5:1 contrast against each declared background on which it appears. The
  border shall have at least 3:1 contrast against canvas, surface, and raised surface;
  the selected marker against both selected background and surrounding surface; the
  provenance ring against the fixed occurrence surface; and the focus outline against
  canvas, surface, raised surface, and selected background. The selected fill shall be
  supplemental rather than the sole selected-state indicator. Captured span colors and
  backgrounds shall not define cue adjacency or be recolored or discarded.
  A selected event row shall use the selected background plus a non-layout-shifting
  three-pixel inset inline-start selected marker. Every keyboard-focused control or
  focusable region shall use a two-pixel focus outline with a two-pixel offset. Each
  SYS-022 definition suffix shall consist exactly of one ordinary space, `⟦`, the exact
  retained type text, and `⟧`; the complete suffix shall use the metadata color and
  italic styling. An empty type shall therefore display ` ⟦⟧`. Each
  provenance-related occurrence shall retain a fixed surface wrapper and all captured
  SSA styling while adding a
  non-layout-shifting two-pixel inset provenance box-shadow ring. That ring and the
  independent outer focus outline shall remain simultaneously visible. State remains
  identifiable without hue through marker geometry, suffix delimiters and italics, ring
  geometry, textual shared-column and absent-state labels, and the focus outline.
  A single embedded stylesheet shall define one root token set and shared base, layout,
  component, and final state rules. Viewer JavaScript shall change semantic attributes
  or shared classes rather than write presentation per event or occurrence. Ordinary
  viewer elements shall have no element-specific presentation declaration; only the
  one active overlay may receive exactly `--overlay-inline-start` and
  `--overlay-block-start` as measured position custom properties. Validated normalized
  non-`None` Rich style tuples shall be interned into shared generated classes, with every
  matching span reusing its class; the `None` sentinel shall inherit base code styling
  without a generated rule, using MONOKAI foreground `#D9D9D9` on the fixed occurrence
  surface. The serialized style association shall retain every SYS-006-supported Rich
  15.0.0 field and distinguish explicit `False` from `None`.
  The fixed projection shall use the unmodified Rich 15.0.0
  `rich.terminal_theme.MONOKAI` palette and handle all five `ColorType` encodings. It
  shall apply reverse by swapping foreground and background, supplying MONOKAI defaults
  for a missing side; then apply dim per channel as
  `int(foreground + (background - foreground) * 0.5)` against the MONOKAI background.
  It shall project bold and italic directly; combine underline, strike, and overline
  line kinds, using a double style for that combined set when underline2 is active and a
  solid style otherwise; and retain blink, blink2, conceal, frame, encircle, link, and
  meta only as inert serialized data with no animation, hiding, layout-changing effect,
  URL, or active link.
  The event hierarchy shall remain the leading column and SSA states shall remain
  consecutive, unwrapped columns in one horizontally scrollable workspace. At Chrome
  page zoom of 100% or 200% and any measured CSS viewport at least 640 pixels wide and
  480 pixels high, the viewer shall not reorder, stack, truncate, or hide their content
  or controls. SSA text shall preserve whitespace without wrapping. V1 shall provide no
  theme switcher, animation, custom search or filtering, graphical provenance panel,
  mobile/touch-specific layout, print view, or persisted UI state.
- **Parents:** STK-001, STK-002, STK-003, STK-004, STK-005
- **Acceptance criterion:** In default, selected, focused, metadata, provenance,
  shared-handoff, overlay, and combined states, computed colors equal the declared
  tokens and independently calculated unrounded contrast meets the exact adjacency
  matrix above. Selection has both its supplemental fill and authoritative three-pixel
  marker; focus has its independent two-pixel offset outline. Every definition suffix is
  exactly
  ` ⟦<retained-type-text>⟧` in metadata color and italics, including the empty
  ` ⟦⟧`, and references have none. Every related occurrence gains the provenance
  ring without changing any captured character, foreground, background, weight,
  decoration, or interval; a focused related occurrence shows both rings.
  Computed styles implement every declared Rich projection while inert fields and their
  exact typed values remain retained without acquiring active behavior.
  DOM and computed-style inspection finds one embedded cascade, one fixed token set,
  shared component/state selectors, no ordinary UI `style` attribute, no per-event or
  per-occurrence color declaration, and one generated class per unique validated Rich
  style tuple except `None`. Only the active overlay carries exactly the two declared
  measured position custom properties. At 100% and 200% Chrome page zoom in measured
  CSS viewports of `1280 × 800` and `640 × 480`, horizontal scrolling reaches every
  unchanged consecutive column and control without wrapping SSA text, clipping a
  control, or reordering states. No deferred v1 control or panel is present.
- **Verification:** SYSV-024 (test)
- **Origin / risk:** Developer authorization and selected design, 2026-07-30; a fixed
  token cascade is smaller and easier to audit than inline, framework, multi-theme, or
  element-specific styling, and preserves captured presentation independently.
- **Context:** [Viewer styling options](../../context/viewer-styling.md)
