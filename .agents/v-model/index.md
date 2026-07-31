# Kirin Rewrite Tracer V-Model

- **Profile status:** baselined
- **Product boundary:** One standalone, developer-only Python library for observing Kirin
  rewrite effects during local debugging and tests.
- **Acceptance authority:** Project developer.
- **Last reviewed:** 2026-07-31 (SYS-025 collapse control added the same day)

## Left-side specification

1. [Stakeholder outcomes](01-stakeholder-outcomes.md)
2. [System requirements](02-system-requirements/index.md)
3. [Subsystem and interface contracts](03-subsystem-contracts.md)
4. [Component contracts](04-component-contracts.md)

## Right-side evidence

- [Verification and acceptance actions](verification/index.md)
- [Durable verification evidence](evidence/index.md)

## Implemented baseline

- One-shot transactional tracing targets CPython `>=3.10,<3.14`, Rich 15.0.0, and Kirin
  commit `7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a`.
- Frozen canonical traces retain complete/incomplete event trees, owner-aware styled
  snapshots, exact selected-mutation provenance, deletion effects, and frame-free
  invocation stacks.
- One-file inert HTML export, native event/occurrence controls, Clear selection,
  subtree collapse controls enabled only when nothing in the subtree is selected,
  canonical facts, exact neighboring provenance, metadata disclosure, focus handling,
  and the fixed dark cascade are implemented.
- The sole viewer target is headed Chrome for Testing `151.0.7922.47`, revision
  `r1654411`, `linux64` on x86-64 Linux. Below-`640×480` results are excluded.
- Input assumptions and post-v1 topics are inventoried in the
  [acceptance handoff](evidence/acceptance-handoff.md#explicit-post-v1-inventory).

## Current verification state

Across 48 actions, 7 are `passing`, 34 are `implemented`, and 7 are `failing`.
ACC-001–ACC-005 are implemented with approved automated fixtures but remain pending
project-developer demonstration or review.

Known nonconformances are:

1. [Invalid-`self` direct overrides can be silently ignored](evidence/detector-portability-inspection.md#executable-invalid-self-counterexample),
   affecting SYS-004/SYS-010, SUB-002, and CMP-004.
2. [A post-link publication error can leave the destination](evidence/browser-verification.md#known-nonconformances),
   affecting SYS-018 and SUB-006.
3. [Pinned Blink caps unbounded horizontal layout extent](evidence/sysv-025-layout-invariant.md#pinned-blink-counterexample),
   affecting the universal SYS-024 and SUB-008 presentation clauses.

Package topology and canonical trace persistence/import remain non-normative.
