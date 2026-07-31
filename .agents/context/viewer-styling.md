# Viewer Styling and Cascade

- **Context need:** Explanation
- **Open when:** Designing, implementing, or reviewing viewer colors, contrast, layout,
  CSS organization, state cues, or captured-style projection.
- **Do not open when:** Working only on keyboard/focus behavior, selection reduction,
  export encoding, or trace capture.
- **Related specification IDs:** SYS-006, SYS-019, SYS-020, SYS-021, SYS-022, SYS-023,
  SYS-024
- **Review when:** A token, selector strategy, visual state, layout, theme boundary, or
  normalized Rich-style projection changes.

## One semantic cascade

Inline-heavy styling is initially direct but scatters policy and lets viewer state
overwrite captured Rich presentation. A CSS framework or theme system adds build output,
dependencies, and unused abstractions. Use one plain embedded stylesheet with one fixed
dark token set and shared semantic selectors.

Keep the cascade deliberately boring and ordered:

1. inherited reset and typography;
2. root theme custom properties;
3. workspace and column layout;
4. reusable event, occurrence, suffix, header, and overlay components;
5. final state selectors driven by semantic attributes or shared classes.

Use low-specificity class and attribute selectors. Do not use IDs for presentation,
`!important`, CSS-in-JS, external fonts/icons, animation, registered custom properties,
nesting, CSS anchor positioning, or per-row/value color rules. JavaScript changes state
attributes/classes only. The active overlay's measured `--overlay-inline-start` and
`--overlay-block-start` properties are the sole viewer-chrome exception.

Captured presentation remains a separate input. Validate and normalize the SYS-006 Rich
style fields, intern each unique non-`None` effective tuple once, emit one generated
class for it inside the same stylesheet, and reuse that class on every matching span.
`None` inherits base code foreground `#D9D9D9` on the fixed occurrence surface and
creates no generated rule. Preserve original typed values and their association even
when two tuples have the same visual projection.
Only typed validated values enter fixed declaration templates; no free-form trace string
is spliced into CSS. Never let selection, focus, provenance, or metadata selectors
replace a captured foreground, background, weight, italic, decoration, or text interval.
The SYS-006 style-meta domain is already renderer-neutral and JSON-safe; the viewer
retains it as inert typed data rather than defining a second fallback.

Kirin's `theme="dark"` selects printer/highlighter roles; it does not select a terminal
palette. Color conversion separately pins Rich 15.0.0's unmodified `MONOKAI`
`TerminalTheme`:

| Slot | Ordered sRGB values |
| --- | --- |
| Foreground / background | `#D9D9D9` / `#0C0C0C` |
| Normal 0–7 | `#1A1A1A`, `#F4005F`, `#98E024`, `#FD971F`, `#9D65FF`, `#F4005F`, `#58D1EB`, `#C4C5B5` |
| Bright 8–15 | `#625E4C`, `#F4005F`, `#98E024`, `#E0D561`, `#9D65FF`, `#F4005F`, `#58D1EB`, `#F6F6EF` |

The v1 projection is deliberately explicit:

| Rich 15.0.0 field | CSS projection |
| --- | --- |
| `color`, `bgcolor` | Resolve `DEFAULT` through MONOKAI foreground/background, `STANDARD` through the table above, and `EIGHT_BIT`, `TRUECOLOR`, and `WINDOWS` through Rich 15.0.0's respective fixed indexed palettes or triplet. |
| `reverse` | Resolve missing sides from theme defaults, then swap foreground and background. |
| `dim` | After reverse, calculate each channel as `int(foreground + (background - foreground) * 0.5)` against MONOKAI background, matching Rich 15.0.0 truncation. |
| `bold`, `italic` | Map to font weight and style. |
| `underline`, `underline2`, `strike`, `overline` | Compose underline, line-through, and overline; `underline2` activates underline and selects double style for the combined line set, otherwise the set is solid. |
| `blink`, `blink2`, `conceal`, `frame`, `encircle` | Retain exact `True`, `False`, or `None` data but add no animation, hiding, or layout effect. |
| `link`, `meta` | Retain as inert data only; never create a URL, active link, selector, or declaration from it. |

## Fixed palette and cues

| Role | sRGB token | Use |
| --- | --- | --- |
| Canvas | `#0B1020` | Page background |
| Surface / raised | `#111827` / `#1F2937` | Columns and overlay |
| Text / muted | `#F3F4F6` / `#CBD5E1` | Viewer-authored labels |
| Border | `#94A3B8` | Structural boundaries |
| Selected background / marker | `#1E3A5F` / `#93C5FD` | Event selection |
| Metadata | `#7DD3FC` | Definition suffix |
| Provenance | `#FBBF24` | Related-occurrence inset ring |
| Focus | `#F472B6` | Keyboard outline |

The metadata color has at least 8.8:1 contrast on the declared surfaces, selected text
has 10.45:1 on its background, and its marker has 6.38:1. Require at least 4.5:1 for
viewer-authored normal text, following W3C
[text contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum) and
[non-text contrast](https://www.w3.org/WAI/WCAG22/understanding/non-text-contrast.html).
For non-text cues, test only real adjacency: border against canvas/surface/raised,
selected marker against selected/surface, provenance against its fixed occurrence
surface, and focus against every fixed viewer surface including selected. Each pair
exceeds 3:1. The selected fill is supplemental, not the contrast-qualified indicator.
Do not “fix” arbitrary captured colors; fixed wrappers isolate state cues and fidelity
remains authoritative for SSA spans.

Selection combines fill with an inset leading marker. Focus uses an offset outline.
Provenance uses an inset box-shadow ring on the fixed occurrence wrapper, so it can
coexist with the outer focus outline without changing text. The metadata suffix uses
exact ` ⟦type-text⟧` delimiters plus italics. Shared columns and absent states retain
their authoritative textual labels. Thus hue is never the only added signal.

Keep code in the captured monospace presentation with `white-space: pre`. Put the
leading event hierarchy and all consecutive SSA columns in one horizontal scroller
rather than inventing a responsive stack that destroys adjacency. At 200% Chrome page
zoom, finite fixtures preserve columns through scrolling rather than reflow. Tests cover
`640 × 480`, `1280 × 800`, and varied larger viewports at both zooms; below either floor
dimension has no claim. This is not universal: valid unbounded text reaches Blink's
layout cap and leaves a later control unreachable, so SYSV-025 and the universal
SYS-024/SUB-008 clause fail. See the
[layout evidence](../v-model/evidence/sysv-025-layout-invariant.md).

Keep overlay collision handling equally small: size the one active region to at most
`min(36rem, calc(100vw - 1rem))` by
`min(20rem, calc(50vh - 2rem))`, prefer an eight-pixel gap above its measured anchor,
fall below when needed, clamp inline to eight-pixel viewport margins, and scroll its
contents internally. The two measured position properties fit the shared overlay rule;
no anchor-specific selector or style block is needed. A light theme, theme controls,
custom search/filter, graph panel, mobile layout, print view, animation, and UI-state
persistence are deferred as separate features rather than hidden hooks in the first
stylesheet.
