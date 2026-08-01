# Kirin Integration

- **Context need:** Reference
- **Open when:** Implementing or reviewing Kirin interception, snapshot capture,
  compatibility checks, exact provenance, or orchestration-wrapper analysis.
- **Do not open when:** Defining product behavior or working on Kirin-independent export
  and presentation code.
- **Related specification IDs:** STK-001, STK-002, STK-003, SYS-001, SYS-002, SYS-003,
  SYS-004, SYS-005, SYS-006, SYS-007, SYS-008, SYS-009, SYS-010, SYS-011, SYS-012,
  SYS-013, SYS-014, SYS-015, SYS-016, SYS-017
- **Review when:** The supported Kirin commit changes or an anchored dispatch, wrapper,
  root, printing, or replacement API changes.

The normative support boundary and tracing behavior live in the
[V-model](../v-model/index.md). This page records pinned upstream facts; it neither
selects interception nor settles other callable forms.

## Pinned upstream surface

| Surface | Observed shape |
| --- | --- |
| Revision | `7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a` |
| Base dispatch | `RewriteRule.rewrite` dispatches by node kind to `rewrite_Region`, `rewrite_Block`, or `rewrite_Statement`. |
| Result | `RewriteResult` exposes `terminated`, `has_done_something`, and `exceeded_max_iter`. |
| Root and text | `IRNode.get_root()` finds the containing root; `print_str()` renders printable IR. |
| Replacement | `Statement.replace_by()` inserts the replacement and deletes the original statement. |
| Selected provenance | Four pinned relation seams plus a unary completed-deletion effect from `Statement.delete`; details live in the provenance contexts. |
| Styled output | `Printer.plain_print()` is the sole pinned IR path to `Console.out()`; a `rich()` context and explicit call arguments select styles and highlighting. |
| Inline metadata | Generic statements render attributes and result types. A printer invocation renders at most one selected result-hint key and an optional caller-supplied analysis mapping. |
| SSA metadata | Each `SSAValue` owns a name, type, and arbitrary hint mapping. Generic block printing emits block-argument IDs but bypasses the block argument's type-printing implementation. |
| Rich version | Kirin declares `rich>=13.7.1`; the pinned lock resolves Rich 15.0.0. |
| Printer defaults | `theme="dark"`, `show_indent_mark=True`, `hint=None`, and `analysis=None`; the default console uses Rich's default highlighter. |
| Printable text | `Printable.print_str()` appends `"\n"` by default and accepts `end=""`; `PyAttr.print_impl()` renders `repr(data)` followed by its type. |

## Snapshot-fidelity observations

- `Printable.print_str()` redirects the console to `StringIO`; it retains characters but
  not structured style associations.
- `Printer.result_str()` also redirects the same console while measuring result-column
  width. Naive `Console(record=True)` capture therefore records hidden measurement
  output as well as visible output.
- The pinned IR implementations route visible SSA output through
  `Printer.plain_print()` and `Console.out()`. During `result_str()`, `console.file`
  differs from the outer rendering sink.
- Styled output alone is not a complete metadata snapshot: only one configured hint key
  is printed, generic block arguments omit their types, caller analysis is optional, and
  falsey analysis values render as `missing`.
- Kirin's current serializer does not preserve SSA hints or source information, so it is
  not a lossless substitute for an explicit snapshot metadata inventory.

## Direct `rewrite` overrides

| Class | Delegation shape |
| --- | --- |
| `Walk` | Invokes one child rule for each worklist node. |
| `Fixpoint` | Repeats one child rule until it reports no change or reaches its limit. |
| `Chain` | Invokes child rules sequentially. |
| `CompactifyRegion` | Forwards to a stored composite rule. |
| aggressive `Fold` | Forwards to a constructed composite rule. |
| `WalkDesugarBinop` | Constructs and forwards to `Walk(DesugarBinOp())`. |

`CFGCompactify` retains base dispatch but its specialized `rewrite_Statement` constructs
`CompactifyRegion`, so it introduces another aggregate-to-leaf delegation boundary.
The V-model now supports these owners through one shape-based ordinary Python
public-entry category and assigns the same event shape to every supported wrapper and
leaf `rewrite()` call. The six classes are mandatory compatibility fixtures rather than
an allowlist in production code.

`ScfToCfRule` delegates differently: its `rewrite_Statement` calls another rule
instance's specialized handler directly rather than entering that rule through
`rewrite()`. It is the only such site in the pinned tree; V1 records a nested event
owned by `ForRule` or `IfElseRule`, which also owns its mutations.

## Minimal compatibility fixtures

These fixtures exercise the pinned entry owners without requiring class-specific tracer
behavior:

| Entry owner | Deterministic fixture | Expected public-entry tree |
| --- | --- | --- |
| Inherited base dispatch | One probe rule over a region, block, and statement | Three root events; a separate log confirms all three handlers execute internally |
| `Fixpoint`, `Walk`, and `Chain` | The asymmetric 15-event composition in SYSV-008 | Independently logged wrapper and leaf hierarchy |
| `CompactifyRegion` | Build `region = ir.Region(ir.Block())`, construct with `CFG(region)`, replace `.rule` with an inherited no-op sentinel, then invoke on `region` | Wrapper root with one sentinel child |
| aggressive rewrite `Fold` | Construct from `const.Frame(func.ConstantNone())`, replace `.rule` with the sentinel, then invoke on an empty `ir.Block()` | Wrapper root with one sentinel child |
| `WalkDesugarBinop` | A standalone `py.Constant(0)` | Outer rule, `Walk`, and one `DesugarBinOp` event |
| Late ordinary override | Define a synchronous direct override during the active trace | One event with the local concrete type |
| `ScfToCfRule` delegation | A detached `scf.For` or `scf.IfElse` | One event with one delegated-rule child |

Replacing `.rule` in the two forwarding fixtures isolates public-entry compatibility
from large internal composites; full orchestration is covered separately.

Importing `WalkDesugarBinop` requires Kirin's `vmath` extra because the package eagerly
imports SciPy; the compatibility suite therefore needs an unskipped environment prepared
from the sibling `kirin/` checkout with `uv sync --extra vmath` and executed through
that environment, or an equivalent pinned tracer test dependency.

Use a fresh `Walk` instance in each fixture: an upstream early-termination path can
return before draining its worklist, and tracing must not repair that behavior. Build a
`CFG` only after assembling its region because its graph views are cached. Import the
aggressive rewrite `Fold` from `kirin.rewrite.aggressive`, not the unrelated pass with
the same short name. `WalkDesugarBinop.rewrite` omits a return annotation even though its
runtime result is a `RewriteResult`, so annotations cannot define compatibility.

## Anchors

- **Dispatch and result:** [`rewrite/abc.py`](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/rewrite/abc.py#L8-L49)
- **Core wrappers:** [`walk.py`](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/rewrite/walk.py#L22-L47),
  [`fixpoint.py`](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/rewrite/fixpoint.py#L18-L34),
  and [`chain.py`](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/rewrite/chain.py#L26-L35)
- **Additional delegation:** [`compactify.py`](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/rewrite/compactify.py#L253-L295),
  [`aggressive/fold.py`](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/rewrite/aggressive/fold.py#L18-L45),
  and [`desugar.py`](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/dialects/vmath/rewrites/desugar.py#L60-L68)
- **Cross-instance specialized delegation:** [`scf2cf.py`](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/dialects/scf/scf2cf.py#L171-L182)
- **Vmath fixture dependency:** [`pyproject.toml`](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/pyproject.toml#L15-L21),
  [`vmath/__init__.py`](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/dialects/vmath/__init__.py#L7-L9),
  and [`vmath/interp.py`](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/dialects/vmath/interp.py#L1-L2)
- **Snapshot-related APIs:** [`nodes/base.py`](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/ir/nodes/base.py#L57-L61),
  [`printable.py`](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/print/printable.py#L107-L136),
  and [`nodes/stmt.py`](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/ir/nodes/stmt.py#L317-L328)
- **Printer and metadata APIs:** [`printer.py`](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/print/printer.py#L26-L246),
  [`ssa.py`](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/ir/ssa.py#L23-L185),
  [`nodes/stmt.py`](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/ir/nodes/stmt.py#L625-L681),
  and [`nodes/block.py`](https://github.com/QuEraComputing/kirin/blob/7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a/src/kirin/ir/nodes/block.py#L436-L458)
