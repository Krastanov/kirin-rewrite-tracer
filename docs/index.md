# Kirin Rewrite Tracer

`kirin-rewrite-tracer` records a Kirin rewrite as an immutable trace, then exports a
self-contained HTML viewer for inspecting events, IR snapshots, mutations, analysis
metadata, and provenance.

## Quick start

```python
from pathlib import Path

from kirin_rewrite_tracer import export_html, trace_rewrites

with trace_rewrites() as recorder:
    rule.rewrite(node)

export_html(recorder.trace, Path("rewrite-trace.html"))
```

The destination's parent directory must exist, and `export_html` will never overwrite
an existing file. The resulting HTML is autonomous: it needs no server, network access,
or external assets.

[Explore the worked examples](examples.md){ .md-button .md-button--primary }
[View the API reference](api.md){ .md-button }

## What the viewer answers

- Which rule fired, and under which walk, chain, or fixpoint?
- What changed between the before and after IR snapshots?
- Which mutation created, replaced, retargeted, or deleted an entity?
- Which analysis facts and IR hints were attached to an SSA value?
- Where did a partial rewrite stop when user code raised?

The supported runtime and browser boundary is documented in the
[repository README](https://github.com/Krastanov/kirin-rewrite-tracer#supported-boundary).
