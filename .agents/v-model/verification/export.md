# Interactive HTML Export Verification and Acceptance

Pass only with durable evidence covering every criterion; omit transient logs.

## ACC-005 — Demonstrate standalone interactive trace inspection

- **Covers:** STK-005
- **Method:** demonstration
- **Procedure:** Export developer-approved empty, representative complete, and
  incomplete traces, copy only each resulting HTML file into a clean offline
  environment, stop the producer, and open each directly in the target browser. Use
  only the nonempty documents' tree to plain-click an anchor, Shift-click outward then
  inward, and plain-click a selected range member. Inspect known styled SSA, completion
  and absent-after states; activate Clear from a parent-dominant selection and inspect
  restored rows, zero-selection facts, and focus; select a parent and later exclude it
  through another selection; inspect each selected event's canonical facts and an
  exact-equal shared handoff whose middle value has distinct
  descendant-owned `A`-left and `B`-right facts and an unequal separate handoff. Hover
  tagged values, click them for metadata, and inspect deletion effects and stacks.
  Repeat the representative inspection without a pointer: use the skip link, Tab,
  Enter/Space and Shift variants, focus provenance values, open metadata, and dismiss it
  with Escape. Inspect selected, focused, related, suffix, shared, and overlay styling
  at 100% and 200% Chrome page zoom in `1280 × 800` and `640 × 480` measured CSS
  viewports.
- **Environment / configuration:** Headed Chrome for Testing `151.0.7922.47`, revision
  `r1654411`, `linux64` on x86-64 Linux, with external networking denied and no Python,
  Kirin, tracer, server, or auxiliary export file available.
- **Pass criterion:** The acceptance authority opens each one-file artifact and
  identifies every expected fact, association, completion state, and explicit absence
  without starting another process, supplying another file, or enabling network access.
  The empty artifact is explicitly zero-event.
  In the incomplete artifact, completed relations and deletion effects remain under
  their original owners and no absent after state is filled from another event. Plain
  click selects exactly one row without toggling it off; Shift-click inclusively expands
  or contracts from its retained anchor and replaces the prior range. Clear empties the
  frontier and anchor, restores all rows, removes derived state, and retains its focus.
  The selected-event facts region exposes exact canonical ownership and explicit absence
  without copying descendant facts. Tree, hover,
  suffix, and overlay interactions support the prescribed inspection. Parent selection
  hides every descendant row, and a later excluding selection restores the original
  hierarchy unselected. The shared handoff is always labelled with both roles and keeps
  `A` facts left and `B` facts right; the separate handoff uses identity-only
  cross-boundary hover. The keyboard-only pass reaches the same facts and exact
  selection, provenance, and metadata states without detached focus. Viewer-authored
  text and state cues meet the declared contrast and non-color policy, and every
  consecutive SSA column remains reachable in all declared zoom/viewport combinations.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None

## SYSV-018 — Verify autonomous single-file HTML export

- **Covers:** SYS-018
- **Method:** test
- **Procedure:** Export an empty complete trace, a nonempty complete trace, and an
  aggregate-incomplete trace into separate empty directories while retaining independent
  pre-export trace oracles. Inventory each directory, compare each post-export oracle,
  relocate each HTML file alone into another empty directory, remove the source trace,
  and stop the producer. Open each artifact directly through a local file URL in a clean
  target-browser profile while denying external networking. Record the executable's
  reported version and the provisioned artifact's platform and Chrome-for-Testing
  revision before recording
  page-originated resource requests during loading and the SYSV-019 through SYSV-025
  interaction scenarios. Attempt a missing parent and pre-existing sentinel target,
  race target creation before publication, and inject encoding, write, flush, close, and
  final-publication failures while inventorying temporary files.
- **Environment / configuration:** Headed Chrome for Testing `151.0.7922.47`, revision
  `r1654411`, `linux64` on x86-64 Linux; browser profile and cache outside the export
  directory.
- **Pass criterion:** Each successful export creates exactly one requested regular HTML
  file and no sidecar, leaves its source trace unchanged, initializes after relocation
  with only the browser running, reports version `151.0.7922.47` from the executable and
  `linux64` revision `r1654411` from the provisioned artifact, supports the SYSV-019
  through SYSV-025 scenarios, and makes no auxiliary-file, `http`, `https`, `ws`, or
  `wss` request. Missing parents fail; every existing or raced target raises
  `FileExistsError` without changing its bytes; and no failed export leaves a target or
  temporary file.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None

## SYSV-019 — Verify retained-trace fidelity and inert content

- **Covers:** SYS-019
- **Method:** test
- **Procedure:** Maintain an oracle independent of the exporter. Export an empty
  complete trace; an asymmetric complete trace containing changed and no-op events; and
  one aggregate-incomplete trace with two roots. In one root an incomplete child
  completes a selected relation and deletion effect before exiting, its parent catches
  the exit, completes another mutation, and returns normally. In the other root the
  child's incomplete exit propagates through its parent before the driver catches it.
  Include an incomplete selected-operation shell, nested event and operation hierarchy,
  distinct styled text and metadata records, surviving and transient entities, identity
  projections, empty endpoints, and invocation stacks. Place unique tagged strings
  containing HTML delimiters, both quote forms, `&`, mixed-case `</script>`,
  executable-looking script and event-handler markup, comment delimiters, backslashes,
  `__proto__`, apparent URLs and CSS `url(...)`, non-ASCII text, and Unicode line
  separators across free-form trace fields. Open each relocated artifact under
  SYSV-018, select every event and inspect its always-visible facts inventory and
  explicit absences, inspect every tagged value and association through document
  facilities, and
  observe an execution sentinel, interpreted DOM, computed valid styles, and page
  request log.
- **Environment / configuration:** The same isolated pinned browser environment and
  network controls as SYSV-018.
- **Pass criterion:** The empty trace is explicitly zero-event. Every aggregate and
  event status, fact, owner, identifier, order, text code point, effective style
  association, endpoint, and navigation result equals its oracle. Incomplete events
  expose their before states and no after states; completed child relations and effects
  remain under their original owners; and incomplete operation shells expose no
  fabricated relation or effect. The caught ancestor's after state and the eventual
  final IR are not substituted for an incomplete descendant, and no exception
  classification, failure snapshot, traceback, or raise-site stack is invented. Hostile
  strings remain exact inert text, trigger no sentinel, add no interpreted node,
  attribute, style, or URL, and initiate no request; valid normalized styles alone
  produce their expected visual associations. Every selected-event region contains all
  and only the selected event's canonically owned event, snapshot, style, entity,
  occurrence, metadata, stack, operation, relation, and effect fields and explicit
  absences; zero selection names no event, and parent selection does not copy descendant
  facts. Browser interaction does not alter the source oracle or introduce a second
  authoritative provenance fact.
- **Status:** planned
- **Evidence:** None
- **Nonconformance:** None
