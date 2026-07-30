# Verification and Acceptance Actions

Mark an action `passing` only when durable evidence exercises every pass-criterion
clause; do not paste transient logs.

Initial detector tests may execute only on CPython 3.13.11. Such results are
single-environment evidence and do not establish the product's still-unresolved
interpreter and version support range.

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
  consecutive layout, and cascade inspection.
