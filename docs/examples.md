# Worked examples

These are compact versions of every scenario in
[`EXAMPLES.md`](https://github.com/Krastanov/kirin-rewrite-tracer/blob/main/EXAMPLES.md).
Each trace-producing example links to the actual exported viewer hosted with these docs.
The repository file contains complete imports, setup, printed output, and commentary.

## 1. Why a fixpoint needs more than one pass

Dead-code elimination exposes more dead code, so the event tree reveals three sweeps
before the fixpoint settles.

```python
with trace_rewrites() as recorder:
    Fixpoint(Walk(DeadCodeElimination())).rewrite(wasteful.code)

export_html(recorder.trace, Path("dce-trace.html"))
```

[Open the DCE visualization](visualizations/dce-trace.html){ .md-button target="_blank" }
[Full runnable example](https://github.com/Krastanov/kirin-rewrite-tracer/blob/main/EXAMPLES.md#1-why-a-fixpoint-needs-more-than-one-pass)

## 2. Rewrites that depend on an analysis

Supplying constant-propagation entries records the analysis facts beside the IR-resident
hints that `ConstantFold` uses.

```python
frame, _ = const.Propagate(scaled.dialects).run(scaled)
rule = Fixpoint(Walk(Chain(WrapConst(frame), ConstantFold(), DeadCodeElimination())))

with trace_rewrites(analysis=frame.entries) as recorder:
    rule.rewrite(scaled.code)

export_html(recorder.trace, Path("fold-trace.html"))
```

[Open the constant-fold visualization](visualizations/fold-trace.html){ .md-button target="_blank" }
[Full runnable example](https://github.com/Krastanov/kirin-rewrite-tracer/blob/main/EXAMPLES.md#2-rewrites-that-depend-on-an-analysis)

## 3. Following IR across a method boundary

Inlining clones statements and retargets SSA uses. The viewer connects each new entity
to its source through the recorded provenance relations.

```python
with trace_rewrites() as recorder:
    Walk(Inline(lambda _: True)).rewrite(sum_of_squares.code)

export_html(recorder.trace, Path("inline-trace.html"))
```

[Open the inline-provenance visualization](visualizations/inline-trace.html){ .md-button target="_blank" }
[Full runnable example](https://github.com/Krastanov/kirin-rewrite-tracer/blob/main/EXAMPLES.md#3-following-ir-across-a-method-boundary)

## 4. Lowering structured control flow

`ScfToCfRule` delegates the actual `scf.if` conversion to another rule instance. Its
nested event shows which rule owns the mutations.

```python
with trace_rewrites() as recorder:
    Walk(scf2cf.ScfToCfRule()).rewrite(clamp.code)

export_html(recorder.trace, Path("scf2cf-trace.html"))
```

[Open the control-flow visualization](visualizations/scf2cf-trace.html){ .md-button target="_blank" }
[Full runnable example](https://github.com/Krastanov/kirin-rewrite-tracer/blob/main/EXAMPLES.md#4-lowering-structured-control-flow-and-who-owns-the-work)

## 5. Fusing parallel gates

This `bloqade-lanes` example narrows the rewrite root to one placement and records two
gate fusions before the fixpoint converges.

```python
placement = next(
    stmt
    for stmt in placed.callable_region.walk()
    if isinstance(stmt, place.StaticPlacement)
)

with trace_rewrites() as recorder:
    Fixpoint(FuseAdjacentGates()).rewrite(placement)

export_html(recorder.trace, Path("fusion-trace.html"))
```

[Open the gate-fusion visualization](visualizations/fusion-trace.html){ .md-button target="_blank" }
[Full runnable example](https://github.com/Krastanov/kirin-rewrite-tracer/blob/main/EXAMPLES.md#5-fusing-parallel-gates-in-a-neutral-atom-kernel)

## 6.1 A fixpoint that never converges

Alternating rules keep undoing each other. **Hide unchanged events** identifies which
rule fired in each sweep.

```python
rule = Fixpoint(Walk(Chain(ConstantsRight(), ConstantsLeft())), max_iter=3)
with trace_rewrites() as recorder:
    result = rule.rewrite(shift.code)

assert result.exceeded_max_iter
export_html(recorder.trace, Path("nonconvergent-trace.html"))
```

[Open the nonconvergent visualization](visualizations/nonconvergent-trace.html){ .md-button target="_blank" }
[Full runnable example](https://github.com/Krastanov/kirin-rewrite-tracer/blob/main/EXAMPLES.md#61-a-fixpoint-that-never-converges)

## 6.2 A rule that raises part way through

A supported body exception is re-raised, but the recorder first freezes the incomplete
events and snapshots for inspection.

```python
recorder = trace_rewrites()
try:
    with recorder:
        Walk(NameResults()).rewrite(f.code)
except ValueError:
    export_html(recorder.trace, Path("crash-trace.html"))
```

[Open the partial-trace visualization](visualizations/crash-trace.html){ .md-button target="_blank" }
[Full runnable example](https://github.com/Krastanov/kirin-rewrite-tracer/blob/main/EXAMPLES.md#62-a-rule-that-raises-part-way-through)

## 6.3 A rule the tracer refuses to trace

A specialized handler invoked outside a public `rewrite()` event cannot be attributed,
so the recorder rejects it.

```python
recorder = trace_rewrites()
try:
    with recorder:
        Noop().rewrite_Statement(py.Constant(0))
except UnsupportedTraceError:
    assert recorder.state == "INVALID"
```

No visualization is produced by design: an invalid recorder never exposes a partial
trace. Calling the same rule through `Noop().rewrite(...)` is supported.

[Full runnable example](https://github.com/Krastanov/kirin-rewrite-tracer/blob/main/EXAMPLES.md#63-a-rule-the-tracer-refuses-to-trace)
