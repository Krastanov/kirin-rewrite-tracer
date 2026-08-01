# Kirin Rewrite Tracer Repository Guidance

## Scope

This independent repository sits in the Kirin development workspace; siblings are
evidence or dependencies, not owned code roots.

The Python library code root is `src/`, and the corresponding test root is the singular
`test/` directory. Read the nested router in either root before changing files there.

## Start here

- Open [the agent documentation index](.agents/index.md) to select only the material
  needed for the task. Do not read `.agents/` recursively.
- Open [the V-model index](.agents/v-model/index.md) before changing observable behavior,
  interfaces, acceptance criteria, or verification evidence.
- Open [the Kirin integration reference](.agents/context/kirin-integration.md) when
  working on interception, snapshots, compatibility, or orchestration wrappers.
- Open [the orchestration tracing options](.agents/context/orchestration-tracing.md) when
  choosing or changing rewrite-call interception, event hierarchy, or wrapper support.
- Open [the Python profiling portability reference](.agents/context/python-profiling-portability.md)
  when changing profile ownership, frame classification, or Python-version assumptions.
- Open [the snapshot representation options](.agents/context/snapshot-representation.md)
  when working on capture, persistence, rendering, metadata extraction, or line
  provenance.
- Open [the self-contained HTML export options](.agents/context/interactive-html-export.md)
  when working on offline HTML composition, embedded trace data, or browser-view safety.
- Open [the event tree selection options](.agents/context/event-selection.md) when
  working on click or Shift-range selection, parent dominance, collapse, unchanged
  filtering, or restoration.
- Open [the interactive trace viewer options](.agents/context/interactive-trace-viewer.md)
  when working on SSA columns, provenance hover, or metadata overlays.
- Open [the viewer accessibility options](.agents/context/viewer-accessibility.md) when
  working on native controls, keyboard parity, focus, or accessible descriptions.
- Open [the viewer styling options](.agents/context/viewer-styling.md) when working on
  colors, contrast, layout, CSS organization, or captured-style projection.
- Open [the exact provenance capture options](.agents/context/provenance-capture.md) when
  working on entity identity, mutation interception, or provenance projection.
- Open [the provenance graph storage options](.agents/context/provenance-graph-storage.md)
  when working on relation direction, reverse lookup, deletion effects, indexes, or
  provenance persistence.
- Open [the structured invocation-stack storage options](.agents/context/invocation-stack-storage.md)
  when working on stack capture, lifetime, paths, or presentation.
- Read the closest nested `AGENTS.md` before editing a code root or subsystem.

## Current boundaries

- `src/kirin_rewrite_tracer` exposes the implemented session, immutable model, and HTML
  export API. Hatchling builds it; uv runs it; `test/` holds the pytest suite.
- The implemented snapshot model is renderer-neutral text, styles, occurrences,
  metadata, partial-but-exact provenance, neutral incomplete events, single-copy
  relations, and selected statement-deletion effects.
- Complete and incomplete traces have one confirmed offline presentation target: a
  self-contained HTML file with embedded inert data and no server or external resource
  dependency. V1 is pinned to headed Chrome for Testing `151.0.7922.47`, revision
  `r1654411`, `linux64`.
  Parent-dominant selection hides descendants; exact-equal handoffs share a dual-role
  column; neighboring provenance is exact and edge-scoped. Plain click selects one row,
  while Shift replaces it with a pre-action visible range and rebases swallowed anchors.
  Each non-leaf row has one collapse control that only hides and is enabled only while
  its own subtree holds no selection.
  Complete events are classified from exact snapshot equality and their result flag;
  confirmed unchanged rows can be muted or hidden with their subtrees by one
  document-local toggle, while inconsistent signals remain visibly flagged.
  Native list/button controls provide keyboard parity and deterministic focus fallback.
  Definition-only type suffixes and one read-only metadata disclosure use a fixed dark
  semantic cascade; custom search, general-purpose filtering, graph views, themes,
  mobile layout, print, and UI persistence are outside v1.
- Open the [verification evidence index](.agents/v-model/evidence/index.md) before
  making a conformance claim. Invalid-`self` detection, post-link publication failure,
  and unbounded Blink layout extent have recorded nonconformances.

## Commands

- Create or update the development environment: `uv sync --python 3.13`
- Run tests: `uv run pytest`
- Run lint and formatting checks: `uv run ruff check .` and
  `uv run ruff format --check .`
- Run static typing: `uv run mypy src test`
- Build distributions: `uv build`
- Run repository hooks: `uv run pre-commit run --all-files`
- Check patches: `git diff --check`
- Validate repository documentation:
  `python3 ../.agents/skills/document-repository-v-model/scripts/lint_repository_docs.py . --fail-on-warn`

## Repository rules

- Prefer the simplest maintainable design that satisfies the confirmed specification.
- Compare viable options before adopting a non-trivial dependency, abstraction, or
  repository boundary.
- Keep normative behavior in `.agents/v-model/`; record implementation facts and
  rationale separately only when a recurring retrieval need exists.
- Preserve unrelated user changes and update canonical documentation before its routers.

## Handoff

Report changed behavior and documentation, checks run, unresolved specification or
evidence gaps, and checks not run.
