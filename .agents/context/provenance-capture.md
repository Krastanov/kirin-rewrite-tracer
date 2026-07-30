# Exact Provenance Capture Options

- **Context need:** Explanation
- **Open when:** Designing, implementing, or reviewing entity identity, mutation
  interception, or rendered provenance projection.
- **Do not open when:** Working only on rewrite-frame classification, unrelated metadata
  rendering, or an exporter that consumes an already complete provenance model.
- **Related specification IDs:** STK-003, STK-004, SYS-004, SYS-006, SYS-012, SYS-013,
  SYS-015, SYS-017
- **Review when:** The supported Kirin commit, selected mutation API, or entity-to-text
  ownership mechanism changes.

The normative behavior lives in the
[capture requirements](../v-model/02-system-requirements/provenance.md) and
[navigation and deletion requirements](../v-model/02-system-requirements/provenance-navigation.md).
The **partial but exact** base records identity, four relation calls, and completed
statement deletion from a fifth call. Absence means “not established,” never “probably
unrelated”; no confidence field exists.

## Provenance options considered

| Option | Advantage | Limitation | Judgment |
| --- | --- | --- | --- |
| Snapshot identity only | Almost free once snapshots have trace-scoped entity IDs. | Explains survival and movement, but not replacement or cloning. | Keep as one exact basis. |
| Textual or structural diff | Can produce a visually dense mapping for almost any rewrite. | Equal names, text, types, positions, or shapes do not prove lineage. | Reject; no heuristic relations. |
| Log every IR mutation | Captures insertions, deletion, movement, setters, and field edits. | More than 100 call sites, substantial nested duplication, and most operations establish no source-to-destination lineage. | Reject for the base model. |
| Wrap a small pinned API | Captures exact replacement, use retargeting, clone relations, and one high-value deletion effect while keeping the invasive code isolated. | Deliberately leaves direct field changes and other APIs unmatched. | **Selected alongside identity.** |

## Selected mutation surface

| Pinned API | Exact retained relations | Deliberate boundary |
| --- | --- | --- |
| `Statement.replace_by(replacement)` | source statement → replacement statement | Result relationships come from its nested SSA calls; do not synthesize duplicates. |
| `SSAValue.replace_by(value)` | source SSA value → value receiving one or more then-current uses | The source can remain live, so this is `ssa_uses_retargeted_to`, not “merged.” Retain zero-use and `DeletedSSAValue` calls and their known operands as operations, but emit no relation for them. |
| `Statement.from_stmt(source, ...)` | source statement → returned copy and corresponding source result → returned result by index | This is a copy relation, not identity. |
| `Region.clone(...)` | source region → returned clone, direct source block → direct cloned block, and corresponding direct block arguments | Nested `Region.clone` and `Statement.from_stmt` calls own nested region, statement, and result relations. |
| `Statement.delete(safe=...)` | one `statement_delete_completed` effect on the affected statement | This is a unary operation occurrence, not a source-to-destination relation or a claim that the object can never be reinserted. |

Record repeated operations separately even when endpoints repeat. While a retained
rewrite event is active, create an operation shell at selected-call entry, assign it once
to the innermost event, and keep its dynamic parent operation; calls outside a retained
event are not provenance operations. A normal return completes the shell and attaches
the call's exact relations or deletion effect. An exceptional exit leaves the shell
`incomplete` with no own relation or completed effect. Completed nested operations stay
under their actual parent; do not roll them back, copy them to an ancestor, or discard
them. This preserves the composite shape of `Statement.replace_by`, recursive
`Region.clone`, and partial failures without duplicating child facts.

The trace entity registry must include objects referenced only by operations. Inlining,
for example, can clone a region and then copy from that clone before either event
snapshot is retained. Holding one trace-lifetime reference per registered object and
assigning monotonically increasing project IDs prevents Python object-ID reuse from
corrupting identity. Persist the project ID, never `id(obj)`.

Exact omissions include effects for `Statement.detach`, block or region deletion and
detachment, constructor-plus-insertion, block compaction, direct `.type`, `.name`,
`.hints`, `.args`, or `_blocks` assignment, overridden or third-party copy APIs, and any
other mutation seam. An unselected container deletion can still dynamically invoke
selected `Statement.delete` calls; retain those statement effects without inventing an
effect for the container. A surviving directly edited object still has identity
provenance, but there is no invented mutation edge or callsite. DCE through the pinned
`Statement.delete` has an exact effect; disappearance through another path remains
unexplained. CSE records exact SSA-use retargeting but does not invent a
duplicate-statement → survivor-statement relation.

## Simplest interception

Temporarily replace the five raw class descriptors with small wrappers. Save
`vars(owner)[name]`, including the raw `classmethod` descriptor for `from_stmt`; invoke
the exact saved implementation; create the operation shell before invocation; complete
it and record relations or effects only in the `else` branch of
`try`/`except BaseException`/`else`; mark it incomplete and use a bare `raise` in the
`except` branch; and restore the exact descriptor in context cleanup. On cleanup,
restore only if the installed attribute is still the tracer wrapper, so an unexpected
third-party replacement is not clobbered.

This is simpler and more exact than extending the profile callback. Ordinary Python
wrappers know whether their saved mutator returned or raised and can preserve the
original exception. `sys.settrace` would require ownership of a second tracing slot and
add debugger and coverage conflicts. An upstream Kirin hook would be cleaner long-term
but does not meet the standalone quick-tracer goal.

A method bound before activation bypasses class replacement. The existing profile
callback can recognize entry into each saved original code object. Wrappers set a
delegation guard only while invoking that original; entry outside the guard invalidates
the trace and reports unsupported use at a safe boundary. This preserves the exactness
claim without adding a second tracing hook. Calls to unrelated overrides are outside the
selected surface and remain unmatched.

Canonical relation direction, deletion lifecycle, storage DTOs, and derived lookup
indexes live in the separate
[provenance graph storage context](provenance-graph-storage.md).

Rendered provenance is an identity projection, mutation relation, or effect plus
occurrence sets, not a guessed Cartesian line mapping. Use identity or relation sources
from the owning event's before snapshot and destinations from its after snapshot. For a
deletion effect, expose the affected entity's actual occurrences in both available
snapshots and a separate absent product endpoint. A statement deleted and reinserted in
one event therefore has same-ID after occurrences without acquiring a destination from
the deletion effect. Every projection in an incomplete event has an empty
after-occurrence set because that event has no after snapshot; do not borrow the eventual
trace state.
Intersect each half-open interval with one-based
`"\n"`-delimited lines, assigning a newline to its preceding line. Empty sets also
represent transient, created, or unrendered endpoints. Definition, reference, and
container roles keep occurrences inspectable; they do not create relationships.

Stack capture and its portability tradeoffs live in the separate
[invocation-stack storage context](invocation-stack-storage.md). Provenance operations reference
that project-owned DTO; this adapter does not retain frames itself.

## Anchors

- Kirin replacement and copying:
  [`Statement.replace_by`](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/ir/nodes/stmt.py#L317-L328),
  [`SSAValue.replace_by`](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/ir/ssa.py#L78-L86),
  and [`Statement.from_stmt`](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/ir/nodes/stmt.py#L493-L521)
- Kirin recursive cloning:
  [`Region.clone`](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/ir/nodes/region.py#L146-L204)
- Representative exact and incomplete cases:
  [vmath replacement](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/dialects/vmath/rewrites/desugar.py#L42-L55),
  and [CSE retargeting](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/rewrite/cse.py#L80-L84)
