# Kirin Rewrite Tracer

This repository contains a standalone, developer-only Python package for inspecting the
effects of Kirin rewrites during local debugging and tests. The package and verification
environment are scaffolded; capture and export APIs are introduced only with their
corresponding implementation contracts.

The canonical draft specification and verification map is the
[repository V-model](.agents/v-model/index.md). Exact styled-presentation fidelity,
complete statement and SSA metadata capture within the declared inventory, and opt-in
caller analysis are confirmed requirements. V1 rendering is pinned to Rich 15.0.0 and
Kirin's dark defaults; supported wrappers and leaves use one ordered parent-linked event
model, including no-op calls. A public rewrite frame that does not return a
`RewriteResult` is retained neutrally as incomplete with its before state and completed
mutation activity, but no after state. Tracing requires a process that remains
single-threaded throughout the context. As another undetected v1 input assumption,
snapshot and printer hooks and every invoked metadata-representation hook must not
invoke public rewrites or specialized handlers.
Activation also requires `sys.getprofile()` to be `None` and fails without replacing an
installed profile function; once active, the tracer assumes nothing replaces its hook.
Ordinary synchronous Python public `rewrite(self, node)` entries are the confirmed v1
category, including Kirin's six pinned direct overrides; an executed ordinary Python
cross-instance specialized-handler bypass is rejected. The detector is not pinned to
CPython 3.13: initial tests may use CPython 3.13.11, while implementation is constrained
to the generic profiling and object-introspection surface documented in both Python
3.10 and 3.13.

Provenance is partial but exact: trace-scoped identity covers surviving objects; four
pinned mutation seams cover statement replacement, SSA-use retargeting, statement
copying, and region cloning; and `Statement.delete` contributes a completed-deletion
effect. Each relation or effect is stored once and indexed from every applicable
endpoint, rather than duplicated in forward and backward forms. No textual or structural
heuristic fills gaps. Supported rewrite events and mutation operations retain structured
filename, line-number, and function-name invocation stacks without live frames or
locals.

Any retained trace, including one marked incomplete, can be exported as one
self-contained interactive HTML file. It embeds trace data and presentation resources,
opens directly with only a local browser, makes no page-originated external request, and
preserves free-form trace content as inert data. Incomplete events retain their before
states and completed activity without fabricated after states. V1's sole supported
  viewer environment is headed Chrome for Testing `151.0.7922.47`, revision `r1654411`,
  `linux64` on x86-64 Linux. Other browser/platform support, Python implementations or
  versions outside CPython `>=3.10,<3.14`, other callable forms, broader mutation
  coverage, and canonical trace
  persistence remain future work.

The viewer keeps the event hierarchy in a leading tree column. Selecting a parent hides
every strict descendant row and contributes that parent's coarse pair instead of
descendant pairs; excluding it through a later selection restores the original rows and
order, unselected and without stale detail state. There is no independent
descendant-disclosure state.
Plain click replaces the selection with one row and never toggles it off. Shift-click
replaces the selection with the inclusive anchor-to-target interval in pre-action
visible order, then applies parent dominance; a swallowed anchor rebases to the
unique surviving selected ancestor. Ctrl/Meta does not alter click mode—Shift still
selects the range—and drag alone does not select.
Selected events otherwise contribute logical event-local pairs in one consecutive
coarse range. Exactly equal
`A.after` and `B.before` handoffs render once in an always-visible dual-labelled shared
column while both logical snapshots remain retained.
Unequal handoffs stay separate and support identity-only hover across their boundary.
Within an event pair, hover may also project one-hop relations owned anywhere in its
dominated subtree without changing ownership or composing relation paths. Each SSA
definition has an italic cyan ` ⟦type⟧` suffix containing only its exact
  snapshot-specific retained type text; references have no suffix. Clicking any
  definition or reference opens its complete retained owner metadata anchored to it,
  above when space permits. At most one disclosure is open; occurrence clicks replace
  or toggle it, outside clicks and `Escape` dismiss it, and column removal or a
  single/shared role change clears it without migration or stale restoration.

The hierarchy uses nested lists and native buttons rather than a custom tree widget.
Enter/Space mirrors click, Shift mirrors range selection, swallowed targets move focus
to their selected ancestor, and keyboard-focused SSA values get the same exact
provenance preview as hover. One fixed dark token palette supplies high-contrast
selection, focus, metadata, and provenance cues through a shared CSS cascade without
  overwriting captured Rich styles. Columns stay consecutive and horizontally
  scrollable at 100% and 200% Chrome page zoom down to a `640 × 480` CSS viewport.
  Themes, custom search/filter, graph views, mobile layout, printing, and UI state
  persistence are intentionally outside v1.
