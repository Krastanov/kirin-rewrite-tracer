# Self-Contained Interactive HTML Export

- **Context need:** Explanation
- **Open when:** Designing, implementing, or reviewing HTML export composition,
  embedded trace data, offline browser behavior, or viewer safety.
- **Do not open when:** Working only on trace capture, Kirin interception, canonical
  provenance, or a non-HTML consumer of an already captured trace.
- **Related specification IDs:** STK-004, STK-005, SYS-015, SYS-018, SYS-019, SYS-020,
  SYS-021, SYS-022, SYS-023, SYS-024, SYS-026
- **Review when:** The pinned browser target, required interactions, embedded-data
  boundary, or offline constraint changes.

The exported HTML is a terminal presentation artifact over the canonical in-memory
trace. It is not the canonical trace store, an import format, or a promise that embedded
data or DOM structure remains stable across product versions.

## Options considered

| Viewer shape | Advantage | Limitation | Judgment |
| --- | --- | --- | --- |
| Python-generated final DOM with tiny toggles | Little browser rendering code. | Couples data to markup, repeats facts, expands escaping surface, and makes reverse navigation awkward. | Reject. |
| Inline bundled React, Preact, Svelte, or similar | Rich component ecosystem. | Adds a package manager, build output, framework runtime, and dependency maintenance before the interaction set warrants them. | Defer. |
| Separate JSON plus modules or `fetch` | Clean files during development. | Violates the one-file boundary and has browser-dependent local-file loading behavior. | Reject. |
| SVG- or canvas-first artifact | Useful for a bounded graph panel. | Poor whole-trace container for long searchable text, metadata, and accessible controls. | Defer as a derived panel. |
| Inline vanilla CSS and classic JavaScript over inert embedded JSON | Direct local-file operation, no build/runtime dependency, one canonical payload, and sufficient DOM interaction. | Requires a small serializer, renderer, and careful escaping. | **Recommended.** |

## Recommended composition

Keep capture, export encoding, and browser presentation distinct:

1. Capture and provenance produce a validated renderer-neutral trace.
2. A pure one-way encoder copies it into JSON primitives and fails on an unsupported
   value; do not use `default=str` or retain live Python, Kirin, Rich, frame, or traceback
   objects.
3. A fixed HTML shell inlines plain CSS, one classic non-module JavaScript viewer, and
   one inert trace payload. Source assets may remain logically separate for maintenance,
   but the exported artifact contains their exact content.
4. The viewer parses the payload, rebuilds disposable reverse and occurrence indexes
   from single-copy facts, and keeps selection, expansion, unchanged filtering, and
   panel state only in memory. It never treats the DOM as the canonical trace.

Require an existing destination parent and a nonexistent target. Write a temporary file
in that same directory and publish atomically without overwrite; an existing or raced
target raises `FileExistsError`, and every failure removes the temporary artifact.
There is one known contract gap: if publication creates the destination and then raises,
the target can remain while failure is reported. See the
[browser/export evidence](../v-model/evidence/browser-verification.md#known-nonconformances).

The simplest safe payload is compact JSON produced with `ensure_ascii=True` and
`allow_nan=False`, with `<`, `>`, and `&` escaped as JSON Unicode escapes before
insertion into a fixed `<script type="application/json">` raw-text element. Escaping
every `<` prevents trace text containing any case form of `</script>` from terminating
that element. A schema version may diagnose exporter/viewer mismatch inside one
artifact; it does not establish a public detached-JSON or round-trip contract. Base64 is
a fallback, not the default, because it adds size and decoding code without improving on
complete raw-text escaping.

Create visible trace content with DOM text nodes or `textContent`, never `innerHTML`,
template-to-markup interpolation, `eval`, or `Function`. Store arbitrary keys as values
or `Map` entries rather than merging them into ordinary objects. Translate normalized
style fields through a fixed allowlist, intern each unique non-`None` effective tuple,
emit one generated class per tuple, and assign only those classes to captured spans.
Keep the SYS-006 style-meta domain as typed inert payload data. Typed validated color and
boolean values may enter fixed declaration templates; never splice free-form trace
strings into CSS, selectors, element IDs, URLs, or active links. Filenames, source-like
text, and apparent links remain inspectable plaintext until a later feature defines
activation safely.

Use no resource-bearing elements, CDN assets, fonts, network APIs, modules, workers,
service workers, browser storage, or external source maps. A restrictive generated
content-security policy should deny connections, images, fonts, media, objects, frames,
workers, base URLs, and forms while authorizing the single exporter-authored inline
script, final generated stylesheet, and inert payload with a per-artifact nonce. The
browser itself is the only viewing runtime; browser or extension telemetry outside the
document is not page-originated behavior.

## Browser and presentation baseline

Three browser policies were considered. “Current evergreen browsers” cannot produce
durable evidence, while adding Firefox, Safari, Edge, mobile, and operating-system
combinations multiplies a quick diagnostic tool's test surface. V1 therefore pins one
headed `linux64` [Chrome for Testing](https://developer.chrome.com/blog/chrome-for-testing/)
build: [`151.0.7922.47`, revision `r1654411`](https://googlechromelabs.github.io/chrome-for-testing/known-good-versions.json),
a Stable-channel build selected during the 2026-07-30 design round. Chrome for Testing
is versioned and does not auto-update, so a future browser change is an explicit mini-V
rather than silent compatibility drift. Operation of the artifact remains offline; only
test-environment provisioning may obtain the browser beforehand.

Do not spend that narrow matrix on experimental presentation APIs. Use classic
JavaScript, ordinary native buttons and lists, a custom read-only metadata region, basic
CSS custom properties, and one ordered cascade. Avoid native Popover, CSS anchor
positioning, registered properties, CSS nesting, frameworks, and browser-specific
extensions. The [viewer accessibility](viewer-accessibility.md) and
[viewer styling](viewer-styling.md) contexts own those decisions.

## Separation and open boundaries

The generic view must expose all canonical information even when a specialized
visualization is absent; owner-associated metadata may remain labeled plaintext
key/value records. An always-visible selected-event facts region inventories all and
only the selected event's canonically owned fields and explicit absences; it never copies
descendant facts into a parent. The confirmed interaction is split between
[event-tree selection](event-selection.md) and the
[SSA-column viewer](interactive-trace-viewer.md). Both consume the same payload and may
group presentation without changing facts.

V1 exports aggregate-incomplete traces without inventing information: an incomplete
event retains its before snapshot and completed child operations, relations, effects,
hierarchy, and stack, while its after snapshot remains absent. The viewer presents the
neutral recorded status and does not infer whether an exception or explicit return
caused the exit.

V1 targets the pinned browser and the narrow SYS-023 accessibility contract at 100% or
200% zoom. Finite fixtures are exercised at and above `640 × 480`; below either floor
dimension has no claim. Unbounded valid text can exceed Blink's layout extent, so the
universal SYS-024/SUB-008 reachability clause currently fails; see
[SYSV-025](../v-model/evidence/sysv-025-layout-invariant.md). V1 does not promise other
engines, builds, operating systems, headless/mobile/touch operation, pixel equivalence,
general WCAG conformance, stable HTML/DOM/JSON, import, UI persistence, printing,
download, path redaction, deterministic bytes, compression, streaming, or a
trace-size/performance limit.
