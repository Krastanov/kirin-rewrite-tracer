# Verification and Acceptance Actions

Mark an action `passing` only when durable evidence exercises every pass-criterion
clause; do not paste transient logs.

Non-browser source and installed-distribution verification covers CPython 3.10, 3.11,
3.12, and 3.13. Browser verification uses CPython 3.13.11 only as the producer runtime
and does not broaden the pinned browser claim.

## Approved v1 acceptance fixtures

The project developer approved these five deterministic fixtures on 2026-07-30:

1. `ACC-001` combines structural, style-distinct, and metadata-only rewrites with
   independent state, owner, and printer oracles.
2. `ACC-002` uses the independently logged 15-event
   `Fixpoint(Walk(Chain(changing, no-op)))` hierarchy plus its already-changed no-op run.
3. `ACC-003` combines identity, replacement, retargeting, copying, cloning, deletion,
   transient, and visually similar unrelated entities with independent call paths.
4. `ACC-004` uses a child that completes selected mutations and deletion before raising,
   a catching complete parent, and the corresponding propagated-incomplete branch.
5. `ACC-005` exports approved empty, complete, and aggregate-incomplete traces and
   exercises selection, Clear, exact handoffs, provenance, facts, metadata, focus, and
   fixed presentation in the pinned offline browser.

Automated evidence may implement these demonstrations, but project-developer acceptance
remains pending until the developer performs or reviews them.

Actions are split by retrieval topic:

- [Core tracing and compatibility](core.md) — rewrite-effect acceptance, paired states,
  support envelope, transparency, ordinary public-entry compatibility, and
  unsupported-use rejection, including bypasses.
- [Snapshot fidelity](snapshots.md) — metadata completeness, styled presentation and
  style-meta validation, and metadata-value precedence.
- [Orchestration](orchestration.md) — hierarchy acceptance and the uniform ordered event
  tree, including neutral incomplete events.
- [Python portability](portability.md) — inspection of the detector's documented,
  minor-version-generic dependency surface.
- [Exact provenance](provenance.md) — identity and selected-mutation relations,
  deletion effects, both-direction navigation, rendered occurrence projection, and
  structured invocation stacks.
- [Interactive HTML export](export.md) — standalone single-file operation, complete and
  incomplete trace fidelity, inert content, and browser-based acceptance.
- [Event selection and SSA columns](viewer-selection.md) — exact click and Shift-range
  reduction, automatic descendant hiding, and exact-equal dual-role handoffs.
- [Neighboring-column provenance viewer](viewer-provenance.md) — edge-scoped identity
  and exact selected-mutation hover.
- [SSA metadata viewer](metadata-viewer.md) — definition-only SSA-type suffixes,
  complete single-overlay interaction, and column-role invalidation.
- [Viewer keyboard and focus](viewer-accessibility.md) — native-control keyboard
  parity, focus fallback, accessible descriptions, and modality arbitration.
- [Viewer styling](viewer-styling.md) — exact dark tokens, non-color cues, contrast,
  consecutive layout, cascade inspection, and the universal large-viewport analysis.
- [Subsystem integration contracts](integration-contracts.md) — lifecycle,
  compatibility, immutable storage, capture, mutation, export, projection, and
  accessibility boundary tests.
- [Component contracts](component-contracts.md) — focused ID/freeze, normalization,
  printing, profiler, delegation, stack, index, encoding, and reducer tests.
