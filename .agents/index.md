# Agent Documentation Index

Load only the document needed for the current task.

## Specification

- [Kirin Rewrite Tracer V-model](v-model/index.md) — open when refining product intent,
  changing observable behavior or interfaces, or adding verification evidence.

## Working context

| Context | Need | Open when | Do not open when |
| --- | --- | --- | --- |
| [Kirin integration](context/kirin-integration.md) | Reference | Implementing or reviewing Kirin interception, snapshots, compatibility, or wrapper analysis | Defining product behavior or editing Kirin-independent export and presentation code |
| [Orchestration tracing options](context/orchestration-tracing.md) | Explanation | Designing or reviewing rewrite-call interception, complete or incomplete event trees, wrapper support, or restoration | Working only on captured snapshot contents, export, or provenance |
| [Python profiling portability](context/python-profiling-portability.md) | Reference | Implementing or reviewing profile ownership, frame classification, or Python-version compatibility | Working only on event semantics, snapshots, rendering, export, or provenance |
| [Trace data and presentation context](context/presentation/index.md) | Router | Selecting snapshot, self-contained HTML, selection/filtering, viewer-interaction, accessibility, or styling context | Working only on interception, profiling, or provenance graph storage |
| [Exact provenance capture options](context/provenance-capture.md) | Explanation | Designing or reviewing entity identity, mutation interception, or rendered provenance projection | Working only on graph storage, rewrite-frame classification, or an exporter consuming a captured trace |
| [Provenance graph and deletion storage](context/provenance-graph-storage.md) | Explanation | Designing or reviewing canonical direction, reverse lookup, deletion attribution, indexes, or persistence | Working only on mutation interception or rendered owner capture |
| [Structured invocation-stack storage](context/invocation-stack-storage.md) | Explanation | Designing or reviewing stack capture, serialization, lifetime, paths, or presentation | Working only on entity relationships or rendered ownership |
