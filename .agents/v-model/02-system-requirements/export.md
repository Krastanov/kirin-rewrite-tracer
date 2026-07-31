# Interactive HTML Export Requirements

The first export target is one standalone offline HTML artifact for every retained
trace, including an aggregate trace marked incomplete. The viewer interactions and
presentation are specified separately, and v1 has one reproducible browser target.

## SYS-018 — Produce one autonomous HTML trace artifact

- **Normative statement:** When requested to export any retained trace, including a
  complete trace with no events and an aggregate trace marked incomplete, the product
  shall produce exactly one requested regular HTML file containing all trace data and
  presentation resources required by SYS-019 through SYS-024. After export, that file
  shall open directly from the local filesystem in each declared-supported browser and
  operate without the producer, Python, Kirin, a server, an auxiliary export file, or
  any page-originated external resource request. Export shall not mutate the retained
  trace. The sole declared-supported v1 environment shall be headed Chrome for Testing
  `151.0.7922.47`, revision `r1654411`, `linux64` on x86-64 Linux. Other browser builds,
  engines, operating systems, headless operation, and mobile or touch environments shall
  carry no v1 compatibility claim. Export shall require an existing destination parent
  and a target that does not exist, shall refuse overwrite with `FileExistsError`, and
  shall publish through a same-directory atomic no-clobber operation that leaves no
  temporary file after any failure.
- **Parents:** STK-005
- **Acceptance criterion:** Given an empty complete trace, a nonempty complete trace,
  and an aggregate-incomplete trace exported into separate empty directories, each
  successful export leaves exactly one requested file and leaves an independent trace
  oracle unchanged. After relocating that file alone, stopping the producer, denying
  external networking, and opening it through a local file URL in every
  declared-supported headed Chrome for Testing environment, its view initializes and
  supports SYS-019 through SYS-024 while page-level monitoring observes no
  auxiliary-file, `http`, `https`, `ws`, or `wss` request. Substitution of another
  browser build or platform establishes no compatibility result. A missing parent fails,
  a pre-existing or raced target remains byte-for-byte unchanged and raises
  `FileExistsError`, and injected encoding, write, flush, close, or publication failures
  leave neither a published target nor a temporary artifact.
- **Verification:** SYSV-018 (test)
- **Origin / risk:** Developer confirmation, 2026-07-30; sidecars, servers, or remote
  assets would defeat the confirmed portable offline artifact.
- **Context:** [Self-contained HTML export options](../../context/interactive-html-export.md)

## SYS-019 — Preserve retained trace information in the exported view

- **Normative statement:** The document exported under SYS-018 shall make inspectable
  through its own view, without omission, fabrication, reassociation, or reordering, all
  information retained for that trace under SYS-001, SYS-005 through SYS-009, and
  SYS-012 through SYS-017. It shall preserve exact rendered characters, equivalent
  effective style associations, metadata ownership and labeled value text, aggregate
  and event completion status, event and operation hierarchy and order, entity
  identities and occurrences, provenance relations and effects, absent after states and
  endpoints, and invocation-stack fields. Every free-form trace-supplied string shall
  remain inert data rather than executable HTML, script, style, URL, or event-handler
  content; only validated normalized style fields may affect presentation through the
  declared style mapping. It shall not replace an incomplete event's absent after state
  with an ancestor or final state, synthesize a failure state or traceback, or classify
  the exit as an exception or explicit return. Derived presentation state and indexes
  shall not mutate the retained trace or create another authoritative provenance fact.
  The view shall keep an always-visible selected-event facts region that exposes every
  canonically owned field and explicit absence for the selected event and its owned
  snapshots, styles, entities, occurrences, metadata, stack, operations, relations, and
  effects. It shall not copy a descendant-owned fact into a selected parent.
- **Parents:** STK-001, STK-002, STK-003, STK-004, STK-005
- **Acceptance criterion:** An exported empty complete trace is unambiguously inspectable
  as zero events. For asymmetric complete and incomplete trace fixtures containing
  changed and no-op events, caught and propagated incomplete branches, completed
  mutation activity before incomplete exits, style and metadata distinctions, nested
  hierarchy, transient entities, exact identities, relations and deletion effects,
  absent after states and endpoints, and invocation stacks, every browser-visible fact,
  association, and explicit absence equals an independent oracle. Unique hostile strings
  placed across trace-controlled text fields remain exact and inspectable, execute no
  code, create no interpreted element, attribute, style, or URL, and initiate no
  resource request. With zero selection the facts region states that no event is
  selected; with each selected event it exposes all and only that event's canonical
  inventory and explicit absences, while descendant-owned facts remain under their
  original owners.
- **Verification:** SYSV-019 (test)
- **Origin / risk:** Developer confirmations, 2026-07-29 and 2026-07-30; an artifact that
  flattens styles, metadata, provenance, or code paths would not preserve the diagnostic
  trace, while active interpretation of trace text is unsafe and can alter the view.
- **Context:** [Self-contained HTML export options](../../context/interactive-html-export.md)
