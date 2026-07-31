# Kirin Rewrite Tracer V-Model

- **Profile status:** draft
- **Product boundary:** One standalone, developer-only Python library for observing Kirin
  rewrite effects during local debugging and tests.
- **Acceptance authority:** Project developer.
- **Last reviewed:** 2026-07-30

## Left-side specification

1. [Stakeholder outcomes](01-stakeholder-outcomes.md)
2. [System requirements](02-system-requirements/index.md)
3. [Subsystem and interface contracts](03-subsystem-contracts.md)
4. [Component contracts](04-component-contracts.md)

## Right-side evidence

- [Verification and acceptance actions](verification/index.md)

## Baseline notes

- Round 1 confirmed the actor, local operational environment, acceptance authority,
  single-threaded and non-nestable v1 boundary, strict observational intent, loud
  unsupported-use failure, and initial support for Kirin commit
  `7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a`.
- Round 2 confirmed Rich 15.0.0 styled rendering under Kirin's dark defaults, the
  declared statement and SSA metadata inventory, opt-in caller analysis, qualified
  metadata types, printable-text precedence, and guarded `repr()` fallback.
- Round 3 confirmed one uniform event shape for every supported normally returning
  `rewrite()` invocation, whether wrapper, leaf, changing, or no-op. Each event has a
  trace-unique identifier, concrete rule type, paired snapshots, nearest dynamic parent,
  and sibling entry order.
- Round 4 confirms shape-based ordinary synchronous Python public `rewrite(self, node)`
  support. Same-instance specialized dispatch remains internal, public superclass
  delegation is nested, and cross-instance specialized-handler bypass is rejected.
- Round 5 confirms that snapshot, printer, and metadata-representation hooks must not
  invoke public rewrites or specialized handlers during capture; v1 need not detect a
  violation.
- Round 6 confirms exclusive ownership of the current thread's Python profile slot.
  Activation fails without replacing an installed profile function, every supported
  normal or exceptional exit restores an initially empty slot, and replacement during
  the context is an undetected input-assumption violation.
- Round 7 rejects a CPython 3.13-only product pin. Detection uses only the documented
  Python 3.10/3.13 intersection, excluding bytecode, private frame state, newer
  monitoring, concrete frame-local assumptions, and minor-version branches. The
  supported runtime range is CPython `>=3.10,<3.14`.
- Round 8 confirms partial-but-exact provenance: stable object identity plus four pinned
  mutation APIs, entity-owned rendered intervals, and structured invocation stacks.
  Unrelated entities remain unmatched; no similarity heuristic or confidence score is
  permitted.
- Round 9 confirms neutral incomplete events for public frames that do not return a
  `RewriteResult`, with before-only state and retained completed mutation activity. It
  also adds `Statement.delete` as a fifth selected mutation seam, stores deletion as a
  unary operation effect, and requires both-direction lookup over one canonical copy of
  each relation or effect.
- Rounds 10–22 confirm autonomous offline HTML, one pinned Chrome/Linux target,
  parent-dominant plain/Shift selection, native-control keyboard/focus parity, exact
  dual-role handoffs and edge-scoped provenance, deterministic metadata disclosure, and
  one fixed dark semantic cascade. The inert artifact needs no producer, sidecar,
  server, or page request.
- Round 23 baselines the one-shot recorder lifecycle, atomic invalidation, dependency
  provenance preflight, five-descriptor transaction, deeply immutable canonical trace,
  normalized snapshot equality, pinned owner-aware capture, no-overwrite atomic export,
  native Clear selection, selected-event canonical facts, and the explicit `640 × 480`
  presentation floor. Observable unsupported callable execution invalidates the session;
  unobservable descriptors and deferred callables never executed remain v1 input
  assumptions.
- The profile remains draft while implementation and developer acceptance evidence are
  pending; the v1 behavior, compatibility range, failure semantics, and lower-layer
  contracts are baselined.
- Package topology, concrete DTOs, and canonical trace persistence/import remain
  non-normative.

## Discovery topics not yet specified

- Detection or support for C/custom rewrite descriptors that produce no classifiable
  Python frame, and rejection of deferred rewrite callables before they execute.
- Additional browser engines/platforms, themes, custom search/filter, graphical
  provenance, mobile/touch layout, printing, and UI-state persistence are post-v1.
- Kirin `SourceInfo`, broader deletion, detach, and mutation-operation coverage,
  stack-path redaction, and persistence round-trip behavior.
- Broader runtime implementations or versions outside CPython `>=3.10,<3.14`.
