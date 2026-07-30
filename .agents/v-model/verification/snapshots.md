# Snapshot Fidelity Verification Actions

## SYSV-005 — Verify snapshot metadata completeness

- **Covers:** SYS-005
- **Method:** test
- **Procedure:** Construct an asymmetric deterministic fixture with outer and nested
  statement attributes; named and unnamed result and block-argument values; distinct
  types; and multiple hints, including an unselected hint changed by a supported
  metadata-only rewrite. Include repeated references to a value whose definition is
  outside the captured root and whose metadata differs from every locally defined value.
  Before each captured state, record an immutable metadata oracle. Capture once with
  asymmetric caller analysis containing truthy, falsey, empty, and `None` values and
  once without analysis. After tracing, mutate surviving local and external SSA values
  to third sentinel metadata, then compare every retained representation and association
  with its time-specific oracle and the supplied mapping.
- **Environment / configuration:** Local Python test process using Kirin commit
  `7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a`, Rich 15.0.0, and the declared default
  rendering configuration, with one non-nested trace in a process that remains
  single-threaded within the SYS-002 support envelope.
- **Pass criterion:** Every statement attribute, SSA name or name absence, type, and hint
  appears only under the correct state and owner, including the externally defined owner
  reached by every repeated reference; every explicitly supplied analysis entry appears
  under its correct SSA owner regardless of truthiness; no value is omitted or swapped;
  no retained state contains post-trace sentinel metadata; and the run without supplied
  analysis does not represent analysis as caller-supplied.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None

## SYSV-006 — Verify styled presentation fidelity

- **Covers:** SYS-006
- **Method:** test
- **Procedure:** Render one or more asymmetric fixtures containing at least two
  result-producing statements by invoking `captured_root.print(printer, end="")` once
  through the pinned Kirin printer and once through the tracer. Exercise the pinned
  printer's default-theme roles, direct explicit styles, and highlighter-generated
  styles. Include links and supported nested style-meta values covering every admitted
  scalar and container, insertion order, falsey values, `__proto__`, and the safe-integer
  boundaries. In separate runs exercise a cycle, tuple, non-string map key, integer
  outside either boundary, nonfinite float, and arbitrary object. Use only text and
  styles written to the designated outer printer sink as the direct oracle, then compare
  every ordered emitted code point, including whitespace and newlines, and its composed
  pre-terminal Rich 15.0.0 `Segment.style`, treating `None` as the unstyled sentinel.
- **Environment / configuration:** Local Python test process using Kirin commit
  `7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a`, Rich 15.0.0, dark theme, indentation
  marks, no selected inline hint or printer analysis, and Rich default highlighter, with
  one non-nested trace in a process that remains single-threaded within the SYS-002
  support envelope.
- **Pass criterion:** Direct and retained views have identical ordered
  code-point/effective-style sequences; no text or style is lost, inserted, shifted, or
  swapped; every supported link and style-meta entry retains exact type, value, order,
  and code-point association; and no hidden width-measurement output appears. Each
  out-of-domain style-meta case explicitly fails under SYS-004 without coercion or a
  successfully reported partial trace.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None

## SYSV-007 — Verify metadata value representation precedence

- **Covers:** SYS-007
- **Method:** test
- **Procedure:** Capture metadata values whose qualified types and text paths are
  independently known: one Kirin-printable value with deliberately different printable
  and `repr()` text, one printable value returning empty text, one printable value with
  internal newline or tab content, one non-printable value with a successful `repr()`,
  and one value with a raising printable path and successful `repr()`. Put values with
  custom printable behavior in unselected hints or metadata-only caller-analysis
  entries, so canonical root rendering does not invoke them. Establish printable-text
  oracles by calling each value's `print_str(end="")` directly; do not infer them from
  the value's raw payload.
- **Environment / configuration:** Local Python test process using Kirin commit
  `7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a`, Rich 15.0.0, and the declared default
  rendering configuration, with one non-nested trace in a process that remains
  single-threaded within the SYS-002 support envelope.
- **Pass criterion:** Each successful record contains the exact fully qualified Python
  type name and exact selected string: printable empty output remains empty, printable
  internal whitespace receives no project normalization, and a failed printable path
  discards partial output before using its successful `repr()`.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None
