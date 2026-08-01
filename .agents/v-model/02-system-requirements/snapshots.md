# Snapshot Fidelity Requirements

## SYS-005 — Preserve the declared SSA metadata inventory

- **Normative statement:** For each SSA state retained under SYS-001, the product shall
  preserve and make inspectable under the corresponding owner every attribute entry of
  each recursively contained statement and the name or absence of a name, type, and
  every hint entry of each block argument or result value owned beneath the captured
  root, including hints not selected by the printer. It shall preserve that
  name-or-name-absence, type, and hint inventory for every additional SSA value rendered
  there as a reference even when that value's definition is outside the captured root.
  When caller analysis entries for those SSA values are explicitly supplied, it shall
  also preserve and expose every supplied entry; it shall not synthesize caller analysis
  when none is supplied.
- **Parents:** STK-001
- **Acceptance criterion:** Given an asymmetric deterministic fixture containing nested
  statement attributes and multiple named and unnamed SSA owners with distinct types and
  multiple hint keys, including an unselected hint changed by a supported rewrite, and a
  repeatedly rendered reference whose definition is outside the captured root, the
  retained states expose every independently established representation only under its
  correct state and owner without omission or swapping. In a run with explicitly
  supplied analysis, every supplied entry, including falsey entries, is exposed under
  its correct SSA owner; in an otherwise equivalent run without supplied analysis, no
  entry is represented as caller analysis.
- **Verification:** SYSV-005 (test)
- **Origin / risk:** Explicit developer confirmations, 2026-07-29 and 2026-07-30;
  render-only capture omits metadata relevant to rewrite diagnosis.
- **Context:** [Snapshot representation options](../../context/snapshot-representation.md)
  and [Kirin integration reference](../../context/kirin-integration.md)

## SYS-006 — Preserve styled SSA presentation

- **Normative statement:** Each SSA state retained under SYS-001 shall preserve and make
  inspectable every code point emitted by invoking
  `captured_root.print(printer, end="")` once with the printer configuration declared in
  SYS-002, including whitespace and newlines, and the effective style associated with
  it. The empty `end` omits only `Printable.print()`'s automatically appended final
  newline. The effective style is Rich 15.0.0's `Segment.style`, including `None` as the
  unstyled sentinel, after dark-theme and highlighter composition and before
  terminal-palette or ANSI conversion. Every emitted code point shall retain an
  equivalent effective style even when adjacent equivalent intervals are normalized
  differently. A non-`None` project-owned style record shall retain the original
  `color` and `bgcolor` encodings; all thirteen tri-state attributes; optional `link`
  string; and `meta` entry order, keys, value types, and values. V1 style-meta values
  shall be limited recursively to acyclic `None`, booleans, integers in
  `[-9007199254740991, 9007199254740991]`, finite binary64 floats, strings, lists, and
  insertion-ordered maps with string keys. Any other style-meta value shall be rejected
  explicitly under SYS-004 rather than coerced, stringified, or omitted.
- **Parents:** STK-001
- **Acceptance criterion:** Given an asymmetric deterministic fixture whose supported
  rendering contains adjacent style changes and identical text fragments rendered with
  different effective styles, reducing both the direct Kirin rendering and retained
  trace view to ordered emitted code points paired with effective `Segment.style`
  properties produces identical sequences. Supported nested style-meta records and
  links retain exact typed values and order; an out-of-domain style-meta value causes
  explicit unsupported-use failure and no successful incomplete record.
- **Verification:** SYSV-006 (test), SYSV-004 (test)
- **Origin / risk:** Explicit developer confirmation, 2026-07-29; lost or shifted
  styling can conceal distinctions used to interpret SSA.
- **Context:** [Snapshot representation options](../../context/snapshot-representation.md)
  and [Kirin integration reference](../../context/kirin-integration.md)

## SYS-007 — Represent metadata values with declared precedence

- **Normative statement:** Each metadata value required by SYS-005 shall be exposed with
  its fully qualified Python type name,
  `type(value).__module__ + "." + type(value).__qualname__`, and text selected in this
  order. If the value is an instance of pinned Kirin `Printable`, the product shall first
  attempt its non-terminal `print_str(end="")` path under the declared printer defaults;
  any returned string, including an empty string, is used exactly without further
  normalization. That path shall render through an explicitly non-terminal, uncolored
  console, so the recorded text does not vary with ambient terminal, Jupyter, or
  color-forcing environment. If that path is inapplicable, raises an `Exception`, or does not return
  a string, any partial output is discarded and the exact string returned by guarded
  `repr(value)` is used. Type-label failure or failure of both text paths is a declared
  unsupported category under SYS-004.
- **Parents:** STK-001
- **Acceptance criterion:** Given asymmetric values comprising a Kirin-printable value
  whose printable text differs from its `repr()`, a printable value returning empty
  text, a non-printable value with a successful `repr()`, a value whose printable path
  fails but whose `repr()` succeeds, and values with a failed type label or two failed
  text paths, each successful representation contains the exact qualified type and
  precedence-selected text without project normalization, while each failed use
  explicitly fails and produces no trace reported as complete.
- **Verification:** SYSV-007 (test), SYSV-004 (test)
- **Origin / risk:** Explicit developer confirmation, 2026-07-29; ambiguous fallback or
  omitted type information can make metadata misleading or impossible to interpret.
- **Context:** [Snapshot representation options](../../context/snapshot-representation.md)
  and [Kirin integration reference](../../context/kirin-integration.md)
