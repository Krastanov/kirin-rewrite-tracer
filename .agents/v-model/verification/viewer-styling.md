# Viewer Styling Verification

Use computed styles, DOM structure, geometry, and independent contrast calculations as
the oracle. Screenshots may diagnose failures but are not golden evidence.

## SYSV-024 — Verify fixed tokens, state cues, layout, and shared cascade

- **Covers:** SYS-024
- **Method:** test
- **Procedure:** Under SYSV-018, render fixtures combining default, selected, focused,
  metadata-suffix, provenance-related, shared-handoff, absent-after, and open-overlay
  states, including every pairwise overlap that can occur. Include all unique
  normalized Rich effective-style tuples from SYSV-006, repeated uses of each tuple,
  the `None` sentinel, an empty type, `DEFAULT`, `STANDARD`, `EIGHT_BIT`, `TRUECOLOR`,
  and `WINDOWS` colors, missing foreground or background, reverse, dim, bold, italic,
  underline, underline2, strike, overline, their supported combinations, explicit
  `True`/`False`/`None` differences for the inert boolean fields, and distinct supported
  link and meta payloads. Record exact serialized fields and computed color, background,
  outline, box-shadow, font, decoration, dimensions, and adjacent backgrounds. Use an
  implementation-independent projection oracle containing the enumerated MONOKAI and
  Rich 15.0.0 indexed palettes, reverse defaults, integer-truncating dim formula,
  composed decorations, and inert fields. Independently calculate unrounded sRGB
  contrast for viewer-authored text and only the adjacency pairs declared by SYS-024.
  Inspect the selected marker, delimiters, italics, rings, and textual state labels in
  the DOM and computed styles; a grayscale screenshot may be retained only as a
  diagnostic.
  Inventory embedded stylesheets, root properties, selectors, generated Rich classes,
  every ordinary viewer `style` attribute, and the active overlay's measured custom
  properties. Trigger every state using pointer and keyboard inputs and verify that
  JavaScript changes only shared classes or semantic attributes, except for the active
  overlay's two declared position properties. Keyboard-focus every sequential control
  and the open overlay region. Compare each span's serialized typed association with the
  SYSV-006 oracle and its computed CSS only with the independent projection oracle.
  At Chrome page zoom 100% and 200%, repeat in measured CSS viewports of `1280 × 800`
  and `640 × 480`. Horizontally scroll from the event hierarchy through the last SSA
  column and activate controls at both extremes. Record viewport, workspace, column,
  control, focus-outline, and open-overlay bounding boxes plus `clientWidth`,
  `scrollWidth`, initial and maximum `scrollLeft`. Inspect text wrapping, column and role
  order, clipping, and reachability. Inventory controls and panels for the explicitly
  deferred features.
- **Environment / configuration:** The declared headed Chrome for Testing
  `151.0.7922.47`, revision `r1654411`, `linux64` environment under SYSV-018, using its
  exact sRGB computed styles and the declared Rich 15.0.0 MONOKAI projection.
- **Pass criterion:** Every computed viewer token equals SYS-024. Viewer-authored
  normal text reaches 4.5:1 against its declared background. The border, selected
  marker, provenance ring, and focus outline each reach 3:1 against every background in
  their exact SYS-024 adjacency set; the selected fill is not treated as the sole
  indicator. Selection has background `#1E3A5F` and a
  non-layout-shifting three-pixel `#93C5FD` inline-start marker. Keyboard focus has a
  two-pixel, two-pixel-offset `#F472B6` outline on every focused control and on the
  focused overlay region. Every definition suffix is exactly one space, `⟦`,
  unnormalized retained type text, and `⟧`, in `#7DD3FC` italics; empty type is ` ⟦⟧`
  and references have none. Each related occurrence adds only a two-pixel inset
  `#FBBF24` box-shadow ring to its fixed-surface wrapper. A focused related occurrence
  exposes both that ring and its outer focus outline without changing geometry or any
  captured character or style association. Marker geometry, suffix delimiters and
  italics, ring geometry, and textual shared/absent labels provide the declared
  non-color distinctions.
  One embedded stylesheet contains one token set and ordered shared base, layout,
  component, and final state rules. State transitions add no per-event or
  per-occurrence presentation. No ordinary UI element has a `style` attribute; only the
  active overlay has exactly `--overlay-inline-start` and `--overlay-block-start`.
  Every unique validated Rich non-`None` tuple has one generated class reused by all
  matching spans, while `None` adds none. Every span retains the SYSV-006 interval and
  exact typed style association. Computed color for all five encodings, reverse, the
  integer-truncated dim result, weight, italics, and combined decoration equals the
  independent projection. Blink, blink2, conceal, frame, and encircle retain exact
  `True`/`False`/`None`; supported link and meta retain their typed payloads; all remain
  inert.
  In all four zoom/viewport combinations, all states remain consecutive, unwrapped,
  correctly labelled, horizontally reachable, and operable without truncation,
  clipping, stacking, or reordering. Maximum scrolling exposes the complete final
  column and every tested control and open overlay has a visible nonzero bounding box
  within the viewport when active. Diagnostic observations at `639 × 480` and
  `640 × 479` are labelled below the support floor and establish no compatibility
  result. No theme, animation, custom search/filter, graphical
  provenance, mobile/touch layout, print view, or UI-persistence control exists.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None

## SYSV-025 — Analyze the universal large-viewport layout invariant

- **Covers:** SYS-024
- **Method:** analysis
- **Procedure:** Inspect the implemented cascade and DOM construction for the durable
  invariant that the event hierarchy and every SSA state are nonshrinking, consecutive,
  no-wrap children of one inline-direction horizontal scroller; no supported media query,
  script branch, container query, viewport-relative maximum, overflow clipping, or
  alternate layout may reorder, stack, truncate, or hide a column or control. Derive how
  increasing either CSS viewport dimension at fixed 100% or 200% Chrome page zoom can
  only preserve or increase available viewport area while horizontal `scrollWidth`
  continues to expose the same ordered content. Corroborate the invariant with boundary
  and property sampling at `640 × 480`, one-pixel larger dimensions, asymmetric wide and
  tall dimensions, and generated varied larger viewports at both zoom levels. Record
  below-floor samples separately as exclusions.
- **Environment / configuration:** Implemented fixed viewer cascade and classic-script
  DOM construction, inspected against CSS layout rules and corroborated in headed Chrome
  for Testing `151.0.7922.47`, revision `r1654411`, `linux64`.
- **Pass criterion:** The durable inspection artifact identifies every rule and state
  mutation affecting workspace geometry and demonstrates that all supported states use
  one monotonic no-wrap horizontal layout with no viewport-conditioned alternate. Every
  boundary and generated larger sample retains exact column order, nonzero complete
  controls, unwrapped SSA text, and horizontal reachability at both zoom levels. A
  counterexample invalidates the universal claim; results below 640 pixels wide or 480
  pixels high are explicitly excluded rather than passed.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None
