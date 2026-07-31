# V1 Acceptance Handoff

Automated implementation evidence is ready, but project-developer demonstration/review
has not occurred. ACC-001 through ACC-005 therefore remain exactly `implemented`, never
`passing`.

## Approved fixtures and runners

| Action | Approved fixture | Supporting automation and remaining demonstration gap |
| --- | --- | --- |
| ACC-001 | Structural, style-distinct, and metadata-only rewrites with independent state, owner, and printer oracles | [`test_snapshot.py`](../../../test/test_snapshot.py), [`test_viewer_styling.py`](../../../test/test_viewer_styling.py), and [`test_viewer_metadata.py`](../../../test/test_viewer_metadata.py); no one runner combines all three rewrite modes. |
| ACC-002 | Changing and already-changed `Fixpoint(Walk(Chain(...)))` runs with the independent 15-event tree | [`test_asymmetric_fifteen_event_tree_and_all_no_op_run`](../../../test/test_acceptance.py) |
| ACC-003 | Identity, replacement, retargeting, copy, clone, deletion, transient, similar-unrelated entities, and call paths | [`test_mutation.py`](../../../test/test_mutation.py), [`test_stack.py`](../../../test/test_stack.py), and [`test_viewer_provenance.py`](../../../test/test_viewer_provenance.py); evidence is distributed rather than one demonstration. |
| ACC-004 | Caught and propagated incomplete branches with completed relation/deletion activity | [`test_caught_incomplete_child_retains_exact_completed_provenance`](../../../test/test_acceptance.py) and [`test_propagated_incomplete_frames_preserve_exception_identity`](../../../test/test_acceptance.py) |
| ACC-005 | Empty, complete, and incomplete autonomous artifacts with selection, Clear, handoffs, facts, provenance, metadata, focus, and presentation | [`test_export_browser.py`](../../../test/test_export_browser.py) and the [browser audit](browser-verification.md#action-audit); no one artifact combines the three trace states and every interaction. |

The acceptance authority must run or review those fixtures in the declared local/pinned
environment and judge the corresponding STK pass criteria. Aggregate automated success
does not complete that developer decision.

## Current nonconformances

1. Invalid-`self` execution of an unbound direct rewrite override is silently ignored;
   SYSV-004, INTV-002, and UNITV-004 fail.
2. A post-link publication error can report failure while leaving the destination;
   SYSV-018 and INTV-006 fail, although no-overwrite/race preservation still works.
3. Valid unbounded snapshot text can exceed Blink's layout extent and make a later
   control unreachable; SYSV-025 and INTV-008 fail.

The first makes SYS-004, SYS-010, SUB-002, and CMP-004 nonconforming. The second makes
SYS-018 and SUB-006 nonconforming. The third makes the universal layout clauses of
SYS-024 and SUB-008 nonconforming.

## Explicit post-v1 inventory

- detection/support for unobservable C or custom descriptors, plus rejection of
  deferred rewrite callables before execution;
- Python implementations or versions outside CPython `>=3.10,<3.14`;
- multithreading, nested sessions, and nonordinary rewrite lifecycle support;
- Kirin `SourceInfo`, broader mutations, deletion/container coverage, detach, and
  additional provenance seams;
- source/stack path redaction;
- canonical trace persistence, detached JSON, import, rehydration, or round trip;
- other browsers, builds, operating systems, headless operation, mobile/touch, and
  measured viewports below `640×480`;
- themes, animation, search/filter, graphical provenance, print, persisted UI state,
  forced-colors/high-contrast mode, and broader accessibility claims;
- deterministic artifact bytes, compression, streaming, and raw-data download; and
- trace-size/performance limits. The Blink extent cap requires an explicit future choice
  among a bound/rejection, paging, nested scrolling, virtualization, or a changed
  unbounded-layout requirement.

Acceptance review may accept the implemented conforming subset, request fixes, or
authorize narrowly documented waivers; none is implied by this handoff.
