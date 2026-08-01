# Interactive Trace Viewer

- **Context need:** Explanation
- **Open when:** Designing, implementing, or reviewing SSA-column layout,
  neighboring-column provenance highlighting, or SSA-value metadata interaction.
- **Do not open when:** Working only on HTML payload safety, offline composition, trace
  capture, canonical provenance storage, event-row selection, keyboard/focus behavior,
  or CSS styling.
- **Related specification IDs:** SYS-020, SYS-021, SYS-022, SYS-023, SYS-024, SYS-026
- **Review when:** Handoff equality, provenance applicability, SSA suffix, or
  metadata-overlay behavior changes.

The [event-selection reducer](event-selection.md) supplies an ordered ancestor-free
frontier. This view projects that frontier into SSA columns without turning the
self-contained document into a stateful graphical provenance application.

## Handoff columns and provenance

Order frontier events by displayed tree order, retaining each logical
`before | after/absent` pair. At a consecutive-event handoff, render equal `A.after` and
`B.before` payloads once, with an always-visible header naming both event IDs and roles
and marking the column shared by exact equality. Keep the two logical snapshots and
associations intact beneath that projection. Missing after state is not an empty
snapshot; an incomplete successor may nevertheless share its existing before state
with a complete predecessor.

Three policies were considered. Never sharing is safe but repeats the common chain and
fixpoint handoff; printed-text equality is simple but can hide style, identity,
occurrence, or metadata changes. Use complete retained-payload equality instead:
captured-root binding, schema/configuration, text, effective styles, entities,
occurrences, metadata, and every other snapshot association must be semantically equal.
Ignore only storage-record identity and the event/state binding; event-level relations,
effects, and stacks are not snapshot payload. Compare effective associations rather than
raw JSON or style-table layout. Never share an event's own before and after. When both
neighboring handoffs of a no-op middle event are equal, retain two separate two-role
columns rather than one transitive multi-role column.

The selected parent's columns show only its coarse snapshots. Collect stored one-hop
relations whose endpoints are `SSAValue` entities and whose canonical mutation operation
is owned by the selected event or a descendant whose event-parent chain reaches it.
Join each individual fact only when its source occurs in the parent before snapshot and
its destination occurs in the parent after snapshot. Ancestor-owned, sibling-owned, and
non-`SSAValue` relations do not contribute. Reverse hover uses the same relation through
a derived index: its direction, ID, operation, and original event owner do not change,
and no parent copy is created. Facts with identical endpoints remain distinct canonical
records even if their visible highlights coincide. Never walk `A -> X -> B` to invent
`A -> B`; event-subtree collection joins existing individual facts to occurrences and
does not traverse or compose the provenance graph.

Exact identity is separate: it directly joins the same entity ID across the selected
snapshots, bypasses mutation-relation subtree collection, and has no relation ID,
operation, direction, or event owner. Mutation-operation or effect operands do not imply
a relation; only stored canonical relation facts enter the subtree collection.

## Derived interaction state

The selection frontier and anchor, columns, adjacency policies, hover highlights, and
active metadata occurrence are disposable browser state; none changes the trace.
Rebuild physical columns from the selected logical role sequence. A column carries one
role or exactly the two roles of one equal handoff, and its facing roles determine each
edge policy.
An event's own before/after edge uses exact identity plus applicable selected-mutation
facts. A separate `A.after | B.before` handoff uses exact same-entity identity only; no
mutation fact crosses it. An absent-after indication is a barrier rather than an SSA
state. A shared column acts as `A.after` leftward and `B.before` rightward, so facts
cannot leak or compose through it. Every related entity occurrence in the immediate
state is eligible; no occurrence or line pairing is inferred.

Keep metadata decoration separate from captured SSA text and occurrence intervals. V1
puts exactly one compact suffix on each `definition` and none on `reference`
occurrences. Its only trace-derived payload is the exact SYS-007 representation text
from that entity's snapshot-specific SSA `type` record. A fixed delimiter frames that
payload, but the suffix does not repeat the name, qualified Python class label,
representation status, hints, caller analysis, provenance, counts, or derived badges.
When type text is empty, the fixed delimiter remains visibly colored without inventing
placeholder text. Read the retained snapshot record rather than the entity's later live
state.

Definition-only placement keeps repeated uses readable; type-plus-count badges and
suffixes on every occurrence add clutter or arbitrary summary semantics. Metadata
remains locally discoverable because any definition or reference can open the
complete owner-specific inventory: name or absence, type, every hint, and explicitly
supplied caller analysis with their retained representation fields. This is an anchored
metadata disclosure, not a hover tooltip. It remains one custom read-only region rather
than depending on native Popover or CSS anchor-positioning APIs. A dual-role handoff
renders a common occurrence, suffix, and equal metadata inventory once while retaining
both logical state bindings.

Model overlay state as one `active_occurrence | null`, deriving visibility, anchor, and
content from it. Two occurrences of one entity are distinct anchors. Classify a click
once in this order: eligible occurrence toggles or replaces; content inside the current
overlay preserves it; everything else dismisses without suppressing the target's normal
action. `Escape` dismisses. Before presenting a recomputed workspace, clear an anchor
whose column is absent. Closing clears the anchor, so restoring a column, delayed work,
or a detached old node cannot revive stale state. Anchor and content update as one
settled input transition before the next presentation; styled descendants of one
occurrence must not trigger a second transition while the click bubbles. This state
model does not select the browser's native Popover API. Key a displayed column by its
ordered tuple of logical state-role bindings. A tuple change removes the old column for
overlay purposes, so a single/shared transition clears the anchor before presentation
even when the rendered occurrence is otherwise identical. Reversing the transition
does not restore it. Migrating by content or entity equality was rejected because it
adds re-anchoring state and can silently change the occurrence's event ownership.
The one custom region uses measured placement rather than the browser's Popover API:
prefer eight pixels above the exact anchor, fall below if needed, clamp to viewport
margins, and bound the box so oversized semantic key/value content scrolls internally.
Its temporary native tab stop supports keyboard scrolling without moving focus when the
region opens or creating a focus trap. Continuously tracking every page and workspace
geometry change would add observer state; instead, a viewport resize or scroll outside
the region closes it, while its own internal scroll remains open.

Keyboard, focus, and accessible-preview decisions are explained in
[viewer accessibility](viewer-accessibility.md); exact tokens, cues, layout, and CSS
organization are in [viewer styling](viewer-styling.md). Custom search,
general-purpose filtering, and graphical provenance views are intentionally outside v1
rather than unresolved hidden states. SYS-026 separately owns the narrow
confirmed-unchanged subtree toggle.
