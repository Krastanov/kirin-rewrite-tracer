# Examples

A Kirin rewrite is normally a black box: you hand a rule an IR node, the node comes back
mutated, and a `RewriteResult` tells you only whether *something* happened. This file
works through small kernels where that is not enough, and shows what the recorded trace
adds — the orchestration tree, the analysis facts a rule consulted, the exact statements
that were cloned or deleted, and where a run stopped when it went wrong.

Every snippet below is a complete program — save it, run it, read the printed output,
then open the exported HTML for the same trace in a browser. The only shared code is the
`print_tree` helper defined once below.

## Setting up

Examples 1 through 4 and 6 need only the repository's own environment:

```console
uv sync --python 3.13
uv run python example.py
```

Example 5 additionally needs `bloqade-lanes`, which pins `kirin-toolchain~=0.22.6` while
the tracer requires the exact pinned Kirin commit. The two cannot be co-resolved, so
install the pinned commit last and let it win:

```console
uv venv --python 3.13
uv pip install bloqade-lanes rich==15.0.0
uv pip install --no-deps kirin-rewrite-tracer
uv pip install --no-deps "kirin-toolchain @ git+https://github.com/QuEraComputing/kirin.git@7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a"
```

`bloqade-lanes` 0.11.1 works against that commit, but this combination is outside the
supported boundary in [`README.md`](README.md); treat example 5 as a demonstration
rather than a supported configuration.

`export_html` never overwrites, so delete a previous export before re-running a snippet.

## A helper you will reuse

Examples 1, 4, and 5 print the recorded event tree with this helper. Save it as `tree.py`
next to the snippet:

```python
"""Shared helper: print the recorded event tree."""


def print_tree(trace):
    depth = {}
    for event in trace.events:
        depth[event.id] = 0 if event.parent_id is None else depth[event.parent_id] + 1
        done = event.result.has_done_something if event.result else None
        mark = {True: "*", False: ".", None: "!"}[done]
        print(f"{'  ' * depth[event.id]}{mark} {event.rule_type.rsplit('.', 1)[-1]}")
```

`*` marks an event that reported a change, `.` one that did not, and `!` an event that
never returned.

## 1. Why a fixpoint needs more than one pass

`Fixpoint(Walk(rule))` is the most common shape in Kirin, and the most opaque: it tells
you a fixpoint was reached but not how many sweeps that took or which node moved on each
one. Dead code elimination is the clearest case, because deleting a statement is what
makes the *next* statement dead.

```python
from pathlib import Path

from kirin.prelude import basic_no_opt
from kirin.rewrite import Fixpoint, Walk
from kirin.rewrite.dce import DeadCodeElimination

from kirin_rewrite_tracer import export_html, trace_rewrites
from tree import print_tree


@basic_no_opt
def wasteful(x: int) -> int:
    dead = x * 999
    return x + 1


with trace_rewrites() as recorder:
    result = Fixpoint(Walk(DeadCodeElimination())).rewrite(wasteful.code)

trace = recorder.trace
print(result)
print_tree(trace)
print("deleted statements:", [effect.kind for effect in trace.effects])
print(export_html(trace, Path("dce-trace.html")))
```

The tree answers the question directly. The first `Walk` deletes the multiply; the second
deletes the constant `999`, which only became dead once its single user was gone; the
third finds nothing and ends the fixpoint:

```
* Fixpoint
  * Walk
    . DeadCodeElimination
    . DeadCodeElimination
    . DeadCodeElimination
    * DeadCodeElimination
    . DeadCodeElimination
    ...
  * Walk
    . DeadCodeElimination
    . DeadCodeElimination
    * DeadCodeElimination
    ...
  . Walk
    . DeadCodeElimination
    ...
deleted statements: ['statement_delete_completed', 'statement_delete_completed']
```

Two things to notice. Combinators are recorded, not just leaves: `Fixpoint`, `Walk` and
the rule each get their own event, so the leaf that fired is nested under the sweep that
found it. And `trace.effects` records deletions separately from mutations, because a
deleted statement leaves no node behind to inspect afterwards.

## 2. Rewrites that depend on an analysis

`ConstantFold` does not evaluate anything itself. It folds a statement only when constant
propagation has already proven a value, and `WrapConst` has attached that proof as a
hint. When a fold you expected does not happen, the rule is rarely at fault — the
analysis simply never proved the value. Pass `analysis=` and the trace carries the
lattice results alongside the IR, so you can check the premise rather than guess at it.

```python
from pathlib import Path

from kirin.analysis import const
from kirin.prelude import basic_no_opt
from kirin.rewrite import Chain, Fixpoint, Walk, WrapConst
from kirin.rewrite.dce import DeadCodeElimination
from kirin.rewrite.fold import ConstantFold

from kirin_rewrite_tracer import export_html, trace_rewrites


@basic_no_opt
def scaled(x: int) -> int:
    factor = 3 + 4
    return x * factor


frame, _ = const.Propagate(scaled.dialects).run(scaled)
rule = Fixpoint(Walk(Chain(WrapConst(frame), ConstantFold(), DeadCodeElimination())))

with trace_rewrites(analysis=frame.entries) as recorder:
    result = rule.rewrite(scaled.code)

trace = recorder.trace
print(result)
scaled.print()
facts = sum(m.namespace == "analysis" for m in trace.metadata)
print("analysis facts recorded:", facts)
print(export_html(trace, Path("fold-trace.html")))
```

`3 + 4` collapses to a single constant and the two operand constants are swept up:

```
func.func @scaled(x : !py.int) -> !py.int {
  ^0(%scaled_self, %x):
  │ %factor = py.constant.constant 7 : !py.int
  │      %0 = py.binop.mult(%x : !py.int, %factor) : ~T
  │           func.return %0
} // func.func scaled
analysis facts recorded: 780
```

`frame.entries` maps SSA values to `const` lattice elements. Passing it records those
elements per snapshot under the `analysis` metadata namespace, next to the `hint`
namespace holding what `WrapConst` wrote into the IR. In the viewer, selecting an SSA
value shows both, which is what distinguishes "the analysis knew, and the rule ignored
it" from "the analysis never knew". Omit `analysis=` and only the IR-resident hints are
captured.

## 3. Following IR across a method boundary

Inlining is where identity gets confusing: the statements in the result did not exist
before the rewrite, and the ones that did are gone. Names in a printed dump cannot tell
you which is which. The trace records the mutation calls themselves, so the copy is
linked to its original.

```python
from pathlib import Path

from kirin.prelude import basic_no_opt
from kirin.rewrite import Walk
from kirin.rewrite.inline import Inline

from kirin_rewrite_tracer import export_html, trace_rewrites


@basic_no_opt
def square(x: int) -> int:
    return x * x


@basic_no_opt
def sum_of_squares(a: int, b: int) -> int:
    return square(a) + square(b)


with trace_rewrites() as recorder:
    result = Walk(Inline(lambda _: True)).rewrite(sum_of_squares.code)

trace = recorder.trace
sum_of_squares.print()
for operation in trace.operations:
    print(f"{operation.api:22} {operation.outcome}")
print("relation kinds:", sorted({relation.basis for relation in trace.relations}))
print(export_html(trace, Path("inline-trace.html")))
```

Both `func.invoke` statements are replaced by the callee's body:

```
func.func @sum_of_squares(a : !py.int, b : !py.int) -> !py.int {
  ^0(%sum_of_squares_self, %a, %b):
  │   %square = py.constant.constant Method("square") : (!py.int) -> !py.int
  │        %0 = py.binop.mult(%a : !py.int, %a : !py.int) : ~T
  │ %square_1 = py.constant.constant Method("square") : (!py.int) -> !py.int
  │        %1 = py.binop.mult(%b : !py.int, %b : !py.int) : ~T
  │        %2 = py.binop.add(%0, %1) : ~T
  │             func.return %2
} // func.func sum_of_squares
```

and the operation log spells out the recipe, once per call site:

```
Region.clone           completed
Statement.from_stmt    completed
Statement.from_stmt    completed
Statement.from_stmt    completed
SSAValue.replace_by    completed
Statement.delete       completed
SSAValue.replace_by    completed
...
relation kinds: ['block_argument_cloned_to', 'block_cloned_to', 'region_cloned_to',
                 'result_copied_to', 'ssa_uses_retargeted_to', 'statement_copied_to']
```

`trace.relations` is the part worth keeping: each relation names a source entity and a
destination entity, so `%0` in the result is tied by `result_copied_to` back to the
multiply inside `square`. The viewer shows these as neighboring provenance on the
selected row, which is how you answer "where did this statement come from" for IR that
was never written by hand.

## 4. Lowering structured control flow, and who owns the work

Everything so far rewrote statements in place. `ScfToCfRule` is structural: it dissolves
an `scf.if` and its two nested regions into ordinary basic blocks joined by branches. It
is also the one rule in Kirin that delegates to *other* rule instances —
`self.if_else_rule.rewrite_Statement(node)` — which makes it the clearest illustration of
how the tracer decides who owns a piece of work.

```python
from pathlib import Path

from kirin.dialects.scf import scf2cf
from kirin.prelude import structural_no_opt
from kirin.rewrite import Walk

from kirin_rewrite_tracer import export_html, trace_rewrites
from tree import print_tree


@structural_no_opt
def clamp(x: int) -> int:
    if x > 10:
        y = 10
    else:
        y = x
    return y


clamp.print()
with trace_rewrites() as recorder:
    result = Walk(scf2cf.ScfToCfRule()).rewrite(clamp.code)

trace = recorder.trace
print(result)
print_tree(trace)
clamp.print()
owners = {operation.owner_event_id for operation in trace.operations}
print("mutation owners:", sorted(owners))
print(export_html(trace, Path("scf2cf-trace.html")))
```

The nested regions are gone, replaced by four blocks that pass `y` along as a block
argument:

```
  │   %0 = py.constant.constant 10 : !py.int
  │   %1 = py.cmp.gt(lhs=%x : !py.int, rhs=%0) : !py.bool
  │        cf.br ^1()
  ^1():
  │        cf.cond_br %1 goto ^2(%1) else ^3(%1)
  ^2(%2):
  │   %y = py.constant.constant 10 : !py.int
  │        cf.br ^4(%y)
  ^3(%3):
  │ %y_1 = py.assign.alias y = %x : !py.int
  │        cf.br ^4(%y_1)
  ^4(%y_2):
  │        func.return %y_2 : ~T
```

The tree shows `Walk` visiting every node and `ScfToCfRule` declining on all but one. On
that one it fires, and a second rule appears underneath it:

```
* Walk
  . ScfToCfRule
  ...
  * ScfToCfRule
    * IfElseRule
  . ScfToCfRule
  ...
mutation owners: ['event-14']
```

That `IfElseRule` row is the point. `ScfToCfRule` did not do this work itself — it handed
the node to a sub-rule instance, and the tracer follows the handoff and gives the sub-rule
its own event. All seven mutation operations belong to `event-14`, the `IfElseRule` event,
not to `event-13`, the `ScfToCfRule` event that delegated. Ownership follows the code that
actually ran.

The complementary case is just as important and is invisible here by design: when a rule
calls *its own* specialized handler — `self.rewrite_Statement(...)`, which is what the
base `RewriteRule.rewrite` does on every dispatch — that is internal plumbing, not a
handoff, and it creates no event. The distinction is by object identity, so two rules that
compare equal but are distinct objects still nest.

## 5. Fusing parallel gates in a neutral-atom kernel

The examples so far use synthetic rules. This one is a real pass from
[`bloqade-lanes`](https://github.com/QuEraComputing/bloqade-lanes), the neutral-atom
compiler built on Kirin, and it shows why a rewrite trace is worth having on a domain
dialect: the rewrite is correct only because of a property — disjointness of qubit sets —
that the printed IR does not state.

A Hadamard on Gemini hardware decomposes into `Rz · R · Rz`, so a three-qubit kernel
lowers to nine single-qubit rotations, each in its own placement region. After
`MergeStaticPlacement` puts them in one region, `FuseAdjacentGates` collapses runs of
textually adjacent, same-opcode, same-parameter gates that act on disjoint qubits into
one statement — which on hardware is one global pulse instead of several.

```python
from pathlib import Path

import bloqade.squin as squin
from bloqade.lanes.dialects import place
from bloqade.lanes.rewrite.circuit2place import MergeStaticPlacement, always_merge
from bloqade.lanes.rewrite.fuse_gates import FuseAdjacentGates
from bloqade.lanes.transform.native_to_place import PhysicalNativeToPlace
from kirin.rewrite import Fixpoint, Walk

from kirin_rewrite_tracer import export_html, trace_rewrites
from tree import print_tree


@squin.kernel
def ghz():
    reg = squin.qalloc(3)
    squin.h(reg[0])
    squin.h(reg[1])
    squin.h(reg[2])
    squin.qubit.measure(reg)


placed = PhysicalNativeToPlace().emit(ghz)
Fixpoint(Walk(MergeStaticPlacement(always_merge))).rewrite(placed.code)
placement = next(
    stmt
    for stmt in placed.callable_region.walk()
    if isinstance(stmt, place.StaticPlacement)
)


def gates():
    body = placement.body.blocks[0].stmts
    return [
        f"{type(s).__name__}{s.qubits}"
        for s in body
        if isinstance(s, place.QuantumStmt)
    ]


print("before:", gates())
with trace_rewrites() as recorder:
    result = Fixpoint(FuseAdjacentGates()).rewrite(placement)
print("after: ", gates())

trace = recorder.trace
print(result)
print_tree(trace)
print("fusions:", sum(op.api == "Statement.replace_by" for op in trace.operations))
print("statements deleted:", len(trace.effects))
print(export_html(trace, Path("fusion-trace.html")))
```

```
before: ['Rz(0,)', 'R(0,)', 'Rz(0,)', 'Rz(1,)', 'R(1,)', 'Rz(1,)', 'Rz(2,)', 'R(2,)', 'Rz(2,)', 'EndMeasure(0, 1, 2)']
after:  ['Rz(0,)', 'R(0,)', 'Rz(0, 1)', 'R(1,)', 'Rz(1, 2)', 'R(2,)', 'Rz(2,)', 'EndMeasure(0, 1, 2)']
* Fixpoint
  * FuseAdjacentGates
  . FuseAdjacentGates
fusions: 2
statements deleted: 4
```

The trailing `Rz` of qubit 0's Hadamard fuses with the leading `Rz` of qubit 1's, and
likewise for 1 and 2 — pairs that are adjacent in program order and touch different
atoms. Ten gates become eight, and the second `FuseAdjacentGates` event confirms the
fixpoint converged rather than being cut short.

Two details matter for reading the trace. Two `Statement.replace_by` calls produce four
deletions, because each fusion both replaces the run's last gate and deletes the earlier
one; the surrounding `SSAValue.replace_by` operations are the state chain being
rethreaded through the merged statement. And the rewrite root here is the
`place.StaticPlacement` statement, not `placed.code`: snapshots are taken of the rewrite
root, so scoping the rule to the region you care about keeps the export small and the
diffs readable.

Tracing a stage rather than a whole pipeline is still the safer default, now purely for
size rather than support. `PhysicalNativeToPlace` internally runs
`Walk(scf2cf.ScfToCfRule())`, and every `scf.IfElse` or `scf.For` that survives
`AggressiveUnroll` now adds a nested `IfElseRule` or `ForRule` event of its own, each with
a full before and after snapshot. Whole-pipeline traces are expensive for that reason:
unrolling a three-qubit kernel alone records well over 12000 events, each carrying a
complete snapshot of the rewrite root.

## 6. When rewrites misbehave

### 6.1 A fixpoint that never converges

Two rules that disagree about a canonical form will loop forever. This is easy to write
by accident across a large rule set and hard to diagnose from `exceeded_max_iter=True`
alone, which names no rule.

```python
from pathlib import Path

from kirin import ir
from kirin.dialects import py
from kirin.prelude import basic_no_opt
from kirin.rewrite import Chain, Fixpoint, Walk
from kirin.rewrite.abc import RewriteResult, RewriteRule

from kirin_rewrite_tracer import export_html, trace_rewrites


class ConstantsRight(RewriteRule):
    """Canonicalize `add(c, x)` to `add(x, c)`."""

    def rewrite_Statement(self, node: ir.Statement) -> RewriteResult:
        if not isinstance(node, py.binop.Add) or not isinstance(
            node.lhs.owner, py.Constant
        ):
            return RewriteResult()
        node.replace_by(py.binop.Add(node.rhs, node.lhs))
        return RewriteResult(has_done_something=True)


class ConstantsLeft(RewriteRule):
    """Canonicalize `add(x, c)` to `add(c, x)` -- the opposite convention."""

    def rewrite_Statement(self, node: ir.Statement) -> RewriteResult:
        if not isinstance(node, py.binop.Add) or not isinstance(
            node.rhs.owner, py.Constant
        ):
            return RewriteResult()
        node.replace_by(py.binop.Add(node.rhs, node.lhs))
        return RewriteResult(has_done_something=True)


@basic_no_opt
def shift(x: int) -> int:
    return 1 + x


rule = Fixpoint(Walk(Chain(ConstantsRight(), ConstantsLeft())), max_iter=3)
with trace_rewrites() as recorder:
    result = rule.rewrite(shift.code)

trace = recorder.trace
print(result)
for event in trace.events:
    if event.result is not None and event.result.has_done_something:
        print(f"  seq {event.sequence:>3}  {event.rule_type.rsplit('.', 1)[-1]}")
print(export_html(trace, Path("nonconvergent-trace.html")))
```

Filtering to the events that reported a change names the culprits and the alternation:

```
RewriteResult(terminated=False, has_done_something=False, exceeded_max_iter=True)
  seq   1  Walk
  seq  11  Chain
  seq  12  ConstantsRight
  seq  20  Walk
  seq  30  Chain
  seq  32  ConstantsLeft
  seq  39  Walk
  seq  49  Chain
  seq  50  ConstantsRight
```

One rule fires per sweep, and it is a different rule each time — the signature of two
rules undoing each other rather than of slow convergence. The root `Fixpoint` event is
absent from this list because a fixpoint that exceeds `max_iter` reports
`has_done_something=False`, discarding the work it did.

### 6.2 A rule that raises part way through

A rewrite that crashes normally leaves you with a traceback and IR in an unknown state:
some nodes rewritten, some not, and no record of which. A supported body exception
freezes the valid trace before re-raising the same exception object, so the partial run
stays inspectable. Bind the recorder outside the `with` statement to reach it.

```python
from pathlib import Path

from kirin import ir
from kirin.dialects import py
from kirin.prelude import basic_no_opt
from kirin.rewrite import Walk
from kirin.rewrite.abc import RewriteResult, RewriteRule

from kirin_rewrite_tracer import export_html, trace_rewrites


class NameResults(RewriteRule):
    """Give every statement result a readable name -- and crash on `func.return`."""

    def rewrite_Statement(self, node: ir.Statement) -> RewriteResult:
        prefix = "k" if isinstance(node, py.Constant) else "v"
        node.expect_one_result().name = prefix
        return RewriteResult(has_done_something=True)


@basic_no_opt
def f(x: int) -> int:
    return x + 1


recorder = trace_rewrites()
try:
    with recorder:
        Walk(NameResults()).rewrite(f.code)
except ValueError as exc:
    print("rewrite raised:", exc)

print("recorder state:", recorder.state)
trace = recorder.trace
print("complete:", trace.complete)
for event in trace.events:
    name = event.rule_type.rsplit(".", 1)[-1]
    print(f"  {event.id:>8}  {name:<20} {event.completion}")
print(export_html(trace, Path("crash-trace.html")))
```

```
rewrite raised: expected one result, got 0
recorder state: FROZEN
complete: False
   event-0  Walk                 incomplete
   event-1  NameResults          complete
   event-2  NameResults          complete
   event-3  NameResults          complete
   event-4  NameResults          complete
   event-5  NameResults          incomplete
crash-trace.html
```

`event-5` is the invocation that raised and `event-0` is the sweep that never finished;
every event before them completed normally and carries a usable before/after snapshot.
`trace.complete` is `False`, and incomplete events have `result is None` — which is what
the `!` marker in `print_tree` reports. An incomplete trace exports and renders like any
other.

### 6.3 A rule the tracer refuses to trace

Every event the tracer records is attributed to the rewrite frame that dynamically
encloses it. A specialized handler called directly, with no `rewrite()` anywhere on the
stack, has nothing to attribute to — so the tracer refuses rather than record an orphan.

```python
from kirin import ir
from kirin.dialects import py
from kirin.rewrite.abc import RewriteResult, RewriteRule

from kirin_rewrite_tracer import UnsupportedTraceError, trace_rewrites


class Noop(RewriteRule):
    def rewrite_Statement(self, node: ir.Statement) -> RewriteResult:
        return RewriteResult()


recorder = trace_rewrites()
try:
    with recorder:
        Noop().rewrite_Statement(py.Constant(0))
except UnsupportedTraceError as exc:
    print("refused:", exc)

print("recorder state:", recorder.state)
try:
    recorder.trace
except UnsupportedTraceError:
    print("no partial trace is offered")
```

```
refused: a specialized rewrite handler ran outside a public rewrite event
recorder state: INVALID
no partial trace is offered
```

Calling the same rule through `Noop().rewrite(...)` records normally. The refusal is
narrow: it is about there being no enclosing invocation, not about which instance the
handler belongs to — a handler on a *different* instance has a parent to attribute to and
records its own nested event, as example 4 shows.

This is the deliberate difference between the two failure modes above. A body exception
is the traced code's problem, so the trace freezes and stays readable; unsupported use is
the tracer's own limit, so the recorder is permanently invalidated and offers no partial
trace at all.

Note that `UnsupportedTraceError` propagates out of the call, abandoning the rewrite at
the point of detection. Tracing is not transparent to an unsupported rewrite, so do not
wrap one in `trace_rewrites` and expect the IR to come out the same as an untraced run.
See the supported boundary in [`README.md`](README.md) for the full list of unsupported
constructions.

## Reading the exported HTML

`export_html` writes one self-contained file: no server, no network, no external assets.
Open it directly from disk.

Click a row to select an event and see its canonical facts, the neighboring provenance
for the entities it touched, and definition metadata; Shift-click for a range. Non-leaf
rows have a collapse control for hiding a whole subtree, and the Clear selection button
is always available. Every control is a native list or button, so keyboard navigation
works throughout.

Exports in this file range from roughly 0.3 MB to 4.6 MB. Size scales with the number of
events times the size of the rewrite root, since each event stores a full snapshot —
narrowing the rewrite root, as example 5 does, is the effective lever.

The viewer is verified only against the pinned headed Chrome for Testing build and
viewport range recorded in [`README.md`](README.md).
