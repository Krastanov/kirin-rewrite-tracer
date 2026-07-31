# Large-Viewport Layout Analysis and Counterexample Evidence

This is the durable SYSV-025 artifact. **Analysis result: failing.** The cascade is
no-wrap for ordinary finite fixtures, but pinned Blink's bounded layout extent can
leave a later, nonzero control unreachable. The matrix corroborates its named fixture;
it does not prove the universal requirement. A changed digest requires renewed review.

## Reviewed source identity

| Source | SHA-256 |
| --- | --- |
| `src/kirin_rewrite_tracer/assets/viewer.css` | `aa4e8ae2c12e099b314135b05115a13417d8a8076d570bd6c9693b67b38c9087` |
| `src/kirin_rewrite_tracer/assets/viewer.js` | `ec868f7a9ab02cbccde4c7e667f614681b4e0ba9700e0eb81a0fb19b7e19adf3` |
| `src/kirin_rewrite_tracer/_export.py` | `d8acfd848a1043e08658349c71cd8cf470042d2be25c9123d97474dc2c796260` |
| `src/kirin_rewrite_tracer/_encoding.py` | `434d433816772498a7de53e7c970f87cc93da955d7790fe3be5fe5fcc383f8aa` |
| `src/kirin_rewrite_tracer/_model.py` | `a9f1a5298dc1fd94f0b3229a09110fda6389785e6138c99a004b01cdda88e4f3` |
| `test/test_viewer_styling_browser.py` | `129bd134144c2974ddb3a5e7fbbc653238e2d58a36bbec9ccd040cd42398deb1` |
| `test/browser_harness.py` | `da3752a05839fadf95d97c6ddca1912fb5019f9792fb8b33669cb30d2590e89d` |

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
- no-wrap heading flex rows and their `0.75rem` gap;
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
`order`, viewport-relative column maximum, overflow clip, or column-hiding rule.

The complete reviewed JavaScript mutation set relevant to geometry is:

- `renderSelection` maps frontier-ordered columns once through `renderColumn`, then
  replaces `.ssa-columns` in that order;
- `renderColumn` adds semantic classes and a heading plus absent label or code;
- selection changes which event rows are `hidden` and therefore may change the event
  hierarchy's max-content width, but it never moves the leading event column or changes
  the reducer's SSA column order;
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
behavior. This commit introduces none.

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
