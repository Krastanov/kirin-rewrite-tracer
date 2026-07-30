# Snapshot Representation Options

- **Context need:** Explanation
- **Open when:** Designing, implementing, or reviewing snapshot capture, persistence,
  rendering, metadata extraction, or line-based provenance.
- **Do not open when:** Changing rewrite interception or orchestration semantics without
  touching captured states.
- **Related specification IDs:** STK-001, STK-003, STK-005, SYS-001, SYS-002, SYS-003,
  SYS-005, SYS-006, SYS-007, SYS-012, SYS-013, SYS-019, SYS-020, SYS-022
- **Review when:** The supported Kirin or Rich version changes, a new printer output path
  is supported, the metadata inventory changes, or the snapshot component contract is
  baselined.

The [V-model](../v-model/02-system-requirements/index.md) owns fidelity. This page
records the smallest implementation recommendation; concrete DTOs and persistence remain
open, and SYS-019 makes HTML a one-way view rather than canonical storage.

## Options considered

| Canonical form | Advantage | Limitation | Judgment |
| --- | --- | --- | --- |
| Plain or ANSI text | Almost no model code; ANSI displays immediately in a terminal. | Plain text loses style association. ANSI bakes in a terminal palette, pollutes offsets, requires parsing for HTML, and contains only metadata Kirin happened to print. | Keep as export projections, not storage. |
| Rich HTML or live `Segment` objects | Immediate colored output or direct access to Rich's rendered segments. | HTML couples storage to one exporter. Rich objects are not a stable JSON contract, and naive console recording includes Kirin's hidden width-measurement prints. | Use Rich transiently inside the capture adapter only. |
| Cloned or serialized Kirin IR | Retains a semantic IR shape that can be printed again. | Heavier and coupled to dialect imports and object reconstruction; current cloning and serialization omit relevant hints or source fields and do not capture the original presentation. | Reject for v1 snapshots. |
| Unicode text, normalized style spans, and owner-keyed metadata records | Renderer-neutral; preserves presentation, supports plain/terminal/HTML views, keeps offsets usable for later provenance, and makes otherwise-unprinted metadata inspectable. | Requires a small normalizer and explicit metadata inventory. | **Recommended canonical model.** |

## Recommended minimal shape

The names are illustrative until a component contract is baselined:

```text
Snapshot
  schema_version
  root_entity_id
  text
  styles[]                         # deduplicated serialization-safe styles
  spans[start, end, style_id][]    # Unicode code-point offsets
  entities[trace_id, kind, display_name][]
  occurrences[trace_id, role, start, end][]
  metadata[owner_trace_id, namespace, key, value_type, rendered, status][]
  capture_config[kirin_commit, rich_version, theme]
```

`status` distinguishes printable text from `repr()` fallback; dual failure is explicit
under SYS-004. Metadata objects need not round-trip, but their presentation and ownership
do. Process-local monotonic `trace_id` values, not persisted `id()`, correlate survivors;
SYS-012 extends them to mutation-only entities. Overlapping `occurrences` associate
container, definition, and reference text without asserting lineage.

Expose the root trace ID. SYS-020 comparison uses every retained semantic field and
association except its stated identity/binding exclusions, preserving order and
multiplicity while normalizing only encoding artifacts such as style-table layout.
Compare the parsed value—not JSON layout, DOM, or live IR—and use it neither for
persistence nor interning.

## Confirmed v1 rendering and metadata text

The normative details are in SYS-002 and SYS-007. Their implementation-facing
consequences are:

| Concern | Confirmed v1 behavior |
| --- | --- |
| Rendering dependency | Rich 15.0.0 |
| Kirin printer | Dark theme, indentation marks enabled, no selected inline hint, and Rich default highlighter |
| Root invocation | One `captured_root.print(printer, end="")`; no automatically appended final newline |
| Rendering override | None; explicitly supplied caller analysis is metadata-only input |
| Type label | `type(value).__module__ + "." + type(value).__qualname__` |
| Preferred value text | Exact string from `Printable.print_str(end="")`, including empty text and intentional internal whitespace |
| Fallback value text | Exact guarded `repr(value)` after discarding failed printable output |
| No representation | Type-label failure or failure of both text paths causes explicit unsupported-use failure |

Test pinned `Printable` directly; third-party duck types need a declared category.
Catch `Exception`, not `KeyboardInterrupt` or `SystemExit`; preserve returned strings
verbatim. Qualified types are labels, not import promises.

V1 assumes capture and representation hooks terminate and neither invoke rewrites nor
mutate IR; it does not pretend to detect arbitrary hook effects.

Keep three responsibilities separate:

1. A Kirin/Rich compatibility adapter captures visible printer output and inventories
   the explicitly supported metadata.
2. A renderer-independent snapshot model validates and stores text, styles, entities,
   and metadata.
3. Terminal, plain-text, and the confirmed interactive HTML view project that model
   without changing capture or inventing provenance.

## Smallest capture seam

For the pinned Kirin revision, a small `rich.console.Console` subclass can override the
public `out()` method. It retains calls only while `console.file` is the designated outer
snapshot sink, then delegates normally. Kirin's hidden `Printer.result_str()` width
measurements temporarily replace `console.file`, so the identity guard excludes them
without reproducing printer layout logic.

The adapter can render retained calls through Rich's public rendering path, immediately
normalize non-control segments into project-owned style records and offsets, and discard
the Rich objects. Nonempty control segments or printer implementations that bypass
`Console.out()` must either be faithfully handled by a supported capture path or fail
explicitly under SYS-004.

For SYS-006, normalized style means Rich 15.0.0 `Segment.style`, with `None` retained as
the unstyled sentinel, after the dark theme and default highlighter compose styles but
before terminal palette conversion or ANSI encoding. A non-`None` record retains both
colors' original Rich encodings, all thirteen tri-state attributes, optional link, and
ordered meta entries. Meta uses a small recursive JSON-safe domain: acyclic `None`,
booleans, JavaScript-safe integers, finite binary64 floats, strings, lists, and
insertion-ordered string-keyed maps. Encode maps as ordered entries rather than ordinary
JavaScript objects. Tuples, cycles, non-string keys, larger integers, nonfinite floats,
and arbitrary objects are explicit unsupported paths under SYS-004, never `repr`
fallbacks. Code-point offsets include whitespace and newlines.

This seam is intentionally invasive but narrow: one pinned integration module owns the
duck typing and version checks, while the snapshot model and future renderers have no
dependency on Kirin internals.

## Why a metadata sidecar remains necessary

Kirin's styled text is incomplete: one print selects only one SSA hint, generic blocks
omit block-argument types, analysis appears only when supplied, and some values render as
`missing`. Independently inventory every contained statement attribute; the name, type,
and hints of each result or block argument beneath the root and every other SSA value
rendered there as a reference; and supplied caller analysis for those values. Falsey
analysis remains present despite Kirin displaying it as `missing`. Store
external-reference metadata in the snapshot; never populate an overlay from a later live
SSA object.

Exact identity, selected-mutation provenance, entity occurrences, and Python invocation
stacks are specified separately in
[the provenance increment](../v-model/02-system-requirements/provenance.md). Kirin
`SourceInfo`, traits, and a general use-edge inventory are not part of the current
snapshot metadata inventory. The selected `SSAValue.replace_by` operation records only
its exact then-current-use retargeting relation; it is not a complete stored use graph.

Expected values in tests should come from fixture construction and direct IR inspection,
not from the tracer's own metadata renderer.

HTML composition, inert payload encoding, and offline browser tradeoffs live in the
separate [interactive HTML export context](interactive-html-export.md).
