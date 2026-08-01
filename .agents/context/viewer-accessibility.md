# Viewer Keyboard and Focus Model

- **Context need:** Explanation
- **Open when:** Designing, implementing, or reviewing viewer keyboard activation,
  focus movement, accessible control semantics, provenance preview arbitration, or
  metadata disclosure behavior.
- **Do not open when:** Working only on selection reduction, CSS tokens and layout,
  capture, export encoding, or canonical provenance storage.
- **Related specification IDs:** SYS-020, SYS-021, SYS-022, SYS-023, SYS-024, SYS-025,
  SYS-026
- **Review when:** A viewer control, keyboard mapping, focus transition, filter,
  accessible description, or input modality changes.

## Why native document controls

Three models were considered:

| Model | Benefit | Cost | Judgment |
| --- | --- | --- | --- |
| ARIA tree/grid plus managed dialog | Few tab stops and rich composite semantics | Adds roving focus, arrow navigation, and dialog focus state; its expansion model would also have to reconcile itself with parent-dominant hiding | Reject for v1 |
| Nested lists and native buttons | Browser supplies focus, Enter/Space, naming, and disabled behavior; hierarchy remains semantic | More tab stops | **Use, with one skip link** |
| Focusable spans with `role=button` | Minimal-looking markup | Reimplements native activation and focus semantics in JavaScript | Reject |

The WAI [tree-view pattern](https://www.w3.org/WAI/ARIA/apg/patterns/treeview/)
has substantial expansion and keyboard obligations. Claiming that role without its
interaction model would be harder to maintain than honest document semantics.

Render event ancestry as nested `<ol>`/`<li>` structures with one `<button>` per visible
row. Do not use `aria-pressed`: activation never toggles the selected singleton off.
Instead, give each button an accessible description containing event identity, type,
hierarchy/completion, and selected state. A visually hidden polite status uses one of
three deterministic forms: `Selected: 0; hidden: H.`, `Selected: 1; event: E; hidden:
H.`, or `Selected: N; first: E1; last: E2; hidden: H.` A first-focus skip link avoids
forcing a keyboard user through a large event list before reaching the labelled empty or
populated SSA workspace.
An always-available native Clear button and the document-local unchanged-filter button
follow ordinary Tab order, invoke their reducers once for pointer or keyboard
activation, and retain focus. The filter uses `aria-pressed`, names the event tree with
`aria-controls`, and is natively disabled when it has no qualifying event. The canonical
selected-event facts display is a labelled region, including its explicit no-selection
state.

Every row description includes its derived change classification. An inconsistent row
also has a visible textual badge and the description states which exact snapshot/result
signals disagree. Filtered rows use native `hidden` ancestry, leaving neither focus nor
accessibility nodes, and a filter transition that removes the current row keeps focus on
the toggle.

Each non-leaf row leads with one native SYS-025 collapse button carrying `aria-expanded`
and `aria-controls` for its child list, an accessible name naming its action, its event,
and, while disabled, why it is unavailable, and a marker glyph held outside that name
subtree. The native `disabled` attribute does the work here that a custom widget would
have to reimplement: it removes the control from sequential focus order, blocks pointer
and keyboard activation, and exposes the unavailable state to assistive technology
without a parallel ARIA vocabulary. That is the whole reason the eligibility rule is
expressed as a disabled control rather than as an ignored click.

Native Enter and Space dispatch the same reducer entry as plain click; Shift plus either
dispatches the same range entry. Focus alone is not selection. After activation, keep
focus on the target unless parent normalization removes it, then move focus to its
unique surviving selected ancestor. If only the anchor is swallowed, the surviving
target keeps focus. Restoration never resurrects old focus.

## SSA controls and one preview

Each eligible SSA occurrence is an inline native button. Its accessible name is the
exact captured occurrence text, while its column section supplies context and its
description identifies definition/reference role, exact owner, and one or both state
roles. The adjacent metadata suffix is outside the button's accessible-name subtree and
is decoration rather than another control.

Tab/Shift+Tab focus arrival requests the same exact neighbor projection as hover. Maintain
at most two candidates—one eligible pointer hover and one keyboard-origin focus—with a
monotonic last-entered order. The newest active candidate owns the single preview; when
it ends, the still-active candidate resumes. Pointer or programmatic fallback focus
does not create a candidate; Enter/Space promotes it before the ordinary action, while
Tab departure does not create a transient preview. This is smaller than parallel
highlights and prevents a parked pointer from silently overriding later keyboard
navigation. Before rendering changed columns, discard owning and suspended candidates
whose control, exact occurrence, or ordered column-role tuple vanished; recreating an
equal control does not revive input state. Derive accessible neighbor descriptions from
the same projection rather than a second provenance algorithm. Name the neighbor role
and every related occurrence's stable entity ID, owner ID, one-based ordinal within that
neighbor column, and rendered label in display order, while distinguishing an existing
neighbor with zero matches from an absent state.

Treat metadata as a nonmodal disclosure. The occurrence button owns `aria-expanded` and
`aria-controls`; one read-only region labelled with exact occurrence, entity, owner, and
role identity uses a heading and definition list.
Opening does not move or trap focus. While open, the region's one `tabindex="0"` stop
follows its anchor so a keyboard user can scroll a long inventory. Tab is ordinary
navigation and is not a dismissal input, although an induced external scroll invokes
the overlay lifecycle. A newly focused surviving outside control keeps focus; when the
region itself is focused and removed, any Escape, external-scroll, or resize close
focuses and reveals the surviving anchor without reviving provenance state. A selection
input already focuses its event-row control, so column removal cannot leave focus on a
detached occurrence.

This is a narrow v1 accessibility contract, not a claim of general WCAG conformance.
It provides keyboard parity, visible focus, semantic names and relationships, exact
accessible provenance descriptions, contrast, and non-color cues in the one supported
desktop environment. Mobile/touch behavior, type-ahead, a composite tree, screen-reader
product matrices, and forced-colors specialization remain post-v1 work.
