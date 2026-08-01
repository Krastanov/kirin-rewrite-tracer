# Large-Viewport Layout Analysis and Counterexample Evidence

This is the durable SYSV-025 artifact. **Analysis result: failing.** The cascade is
no-wrap for ordinary finite fixtures, but pinned Blink's bounded layout extent can
leave a later, nonzero control unreachable. The matrix corroborates its named fixture;
it does not prove the universal requirement. A changed digest requires renewed review.

## Reviewed source identity

| Source | SHA-256 |
| --- | --- |
| `src/kirin_rewrite_tracer/assets/viewer.css` | `2e36564770383ecc8a933119178dfac50f436a33ff925606a1182a4a0c6b10a8` |
| `src/kirin_rewrite_tracer/assets/viewer.js` | `030fdad775a0a8ecca09ee57af41531b58d5c1469ca470696c498fd2d353b1e7` |
| `src/kirin_rewrite_tracer/_export.py` | `dbbd5d15b2775fb7642c912331ad328b18a0d6ab4e742a1def28c849d3f63313` |
| `src/kirin_rewrite_tracer/_encoding.py` | `434d433816772498a7de53e7c970f87cc93da955d7790fe3be5fe5fcc383f8aa` |
| `src/kirin_rewrite_tracer/_model.py` | `a9f1a5298dc1fd94f0b3229a09110fda6389785e6138c99a004b01cdda88e4f3` |
| `test/test_viewer_styling_browser.py` | `5f47ac6144add8659420cd37aac078ffa6d95af08d9a3cd5ea4990f87adce0ab` |
| `test/browser_harness.py` | `4b2f72c39b3bf727e875e56640c103bcac79afe22a33e964e9d3fe9512531ce3` |

Renewed on 2026-08-01 for the unchanged-event presentation. The filter adds a no-wrap
header control, muted event state, inconsistency badge, and semantically intended row or
frontier removal; it adds no alternate layout, wrapping, truncation, or viewport branch.
The pinned finite matrix was not rerun in the current macOS development environment, so
its measurements remain prior corroboration rather than a new current-source browser
claim. The existing Blink extent counterexample remains applicable because the reviewed
change neither bounds snapshot text nor changes the state-column scroller.

## Normal-flow and intrinsic-size inventory

One `main.workspace` contains the leading event section and the SSA workspace. Its
`div.ssa-columns` receives state sections in reducer order.

The complete reviewed set of normal-flow and intrinsic-inline-size inputs is:

- border-box reset; zero body margin; document `min-inline-size: 0`; root
  `system-ui`; inherited button/skip-link font; and fixed heading/paragraph margins;
- `.workspace`: row `flex`, `nowrap`, stretch alignment, `100%` inline size and
  maximum, `overflow: auto`, `0.75rem` gap/padding, and only a block minimum;
- `.event-column, .ssa-workspace`: nonshrinking, max-content flex items, with fixed
  minimum inline sizes of `24rem` and `22rem`; the shared component rule adds
  `0.75rem` padding and a one-pixel border;
- `.ssa-columns`: row `flex`, `nowrap`, max-content inline size, `100%` minimum,
  `0.75rem` gap, and stretch alignment;
- `.state-column`: a nonshrinking max-content flex item with a `20rem` minimum, plus
  the shared `0.75rem` padding and one-pixel border;
- one-rem event-tree indentation, row margins, full-width no-wrap event buttons, and
  button `0.4rem 0.6rem` padding/one-pixel border;
- each `.event-row`: a row `flex`, `nowrap`, stretch-aligned box with a `0.35rem` gap
  whose optional leading `.event-collapse` is a nonshrinking `2rem` no-wrap item, so the
  event column's max-content contribution per row is that fixed item plus the gap plus
  the button's own no-wrap text; the button's `100%` inline size resolves against that
  row and shrinks by exactly the leading item, never below its own text;
- an inconsistent event's inline textual badge adds fixed padding, margin, border, and
  system-font text inside the already no-wrap event button; muted unchanged styling
  changes only paint until the ordinary selected rule takes precedence;
- the disabled collapse rule changes only foreground color and border style, and the
  marker glyph swap stays inside the fixed `2rem` item;
- no-wrap heading flex rows and their `0.75rem` gap; the event heading's nested
  `.event-actions` is another no-wrap row with a `0.5rem` gap between Clear and the
  filter, whose two fixed labels contribute their ordinary max-content width;
- `.trace-code`: `ui-monospace, monospace` and `white-space: pre`; generated Rich
  weight/italics can affect glyph metrics, while color/background/decoration do not
  select another layout;
- each `.ssa-occurrence`: one atomic `inline-block`, inherited font and line height,
  baseline alignment, zero margin/border, and an always-present three-pixel
  fixed-`#0C0C0C` padding moat; the moat reserves six CSS pixels in both axes before
  provenance;
- each definition suffix's exact space, delimiters, type text, monospace metrics, and
  italics; and
- `white-space: pre` on exact metadata values, absent labels, and facts. Facts follow
  but are outside the flex workspace; the fixed metadata region and absolute skip link
  are also outside workspace flow.

The moat is an explicit +6px-per-axis base-layout tradeoff. It adds no text, reordering,
or style reassociation. Two pixels hold the ring and one dark pixel separates captured
backgrounds equal/near `#FBBF24`. At both zooms the browser test compares every run of
each adversarial occurrence, concatenated text/suffixes, relative geometry, styles, and
wrapper dimensions before/after provenance.

There is no media/container query, viewport script branch, grid alternative, wrap path,
`order`, viewport-relative column maximum, overflow clip, or presentation rule that
hides a retained frontier column.

The complete reviewed JavaScript mutation set relevant to geometry is:

- `renderWorkspace` maps frontier-ordered columns once through `renderColumn`, then
  replaces `.ssa-columns` in that order; `renderSelection` calls it after
  `renderEventTree`, and the collapse path calls `renderEventTree` alone, so a collapse
  transition performs no column mutation at all;
- `renderColumn` adds semantic classes and a heading plus absent label or code;
- selection, collapse, and unchanged filtering change which event rows are `hidden` and
  therefore may change the event hierarchy's max-content width. Filtering may also
  reconcile the selected frontier and rebuild its intended columns, but none of the
  three rules moves the leading event column or reorders any surviving SSA role;
- `renderEventTree` additionally sets each collapse button's `disabled`, `aria-expanded`,
  `aria-label`, `data-collapsed`, and marker text, plus the filter label and ARIA/data
  state; the collapse marker stays inside its fixed inline size while the filter swaps
  between its two ordinary no-wrap labels;
- the no-selection path toggles `emptyWorkspace.hidden` and replaces state columns;
- provenance/focus/metadata change data/ARIA/shared classes, not dimensions;
- metadata opening inserts one fixed region and closing removes it; and
- the only presentation writes are the active region's
  `--overlay-inline-start` and `--overlay-block-start` properties, which cannot affect
  normal-flow workspace geometry.

The selected marker, focus outline, and absolute provenance pseudo-element are
paint-only. Its 2px shadow leaves the moat's 1px separator. Overlay and skip link stay
outside flow.

## Finite-layout arithmetic

For event width `E` and state widths `S1 … Sn`, fixed zoom makes the unbounded-model
extent their sum plus padding, borders, and gaps. No-shrink, nowrap, and reducer order
preserve each term; a larger viewport would only reduce required scrolling. The
cascade follows this below Blink's bounded coordinates, so the arithmetic is not a
universal proof.

## Pinned-Blink counterexample

The model/encoder impose no string or render-width bound. The valid counterexample
prefixes a snapshot with `x`, shifts spans/occurrences, uses normal export, and selects
the normal two-column event at `640 × 480`.

Chrome for Testing `151.0.7922.47`, revision `r1654411`, `linux64` produces these
brackets:

| Page zoom | Prefix characters | Result |
| --- | ---: | --- |
| 100% | 3,400,000 | Below the cap; the final control is revealed and activated |
| 100% | 3,600,000 | `scrollWidth` caps at `33,554,432`; the final control cannot be revealed and its click is intercepted |
| 200% | 1,700,000 | Below the cap; the final control is revealed and activated |
| 200% | 1,800,000 | `scrollWidth` caps at `16,777,216`; the final control cannot be revealed and its click is intercepted |

Both failures retain exact order, nowrap, and a nonzero target. Maximum scroll plus
`scrollIntoView({inline: "nearest"})` cannot reveal it. The CSS-pixel cap halves at
200%, consistent with a device-coordinate limit.

A 100% case splits four million characters across 400 style spans. At least 400 render
spans, each 10,000 characters (about 96,000px), still produce the `33,554,432` parent
cap and an unclickable final control. Run splitting does not help.

The durable browser regression
`test_blink_extent_cap_is_a_reproducible_universal_layout_counterexample` passes only
when it reproduces this known nonconformance. It is not passing evidence for the
universal SYSV-025 criterion.

An in-scope correction is unavailable: a size bound/rejection narrows valid inputs;
wrapping, scaling, paging, nested scrolling, or virtualization changes approved
behavior. This reviewed change introduces none of those corrections.

## Finite corroboration and exclusions

The headed pinned-Chrome matrix uses real settings page zoom at 100% and 200%. At each
zoom it measures and operates the approved finite fixture at:

- boundary and one-pixel cases: `640 × 480`, `641 × 480`, `640 × 481`, and
  `641 × 481`;
- required and asymmetric cases: `1280 × 800`, `1600 × 480`, and `640 × 1000`; and
- seed-25025 varied larger cases: `1307 × 727`, `1260 × 766`, `1354 × 730`, and
  `1435 × 818`.

Samples check order, row placement, no-shrink columns, preformatted text, nonzero
controls, both extremes, viewport intersection, and operation. They corroborate only
the finite fixture.

The samples `639 × 480` and `640 × 479` are measured only as explicit below-floor
exclusions. They establish no compatibility result.

`test/test_sysv_025_layout_analysis.py` binds this conclusion to the reviewed sources
and inventory anchors. The counterexample invalidates the universal large-viewport
claim, so SYSV-025 and that clause of SYS-024 cannot be reported as passing.
