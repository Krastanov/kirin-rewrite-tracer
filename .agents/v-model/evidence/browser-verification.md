# Pinned Headed-Chrome Verification

This ledger records the 2026-07-31 browser run over production source commit
`ae2d1bed94a1b812e3cae98dc14dfed45d8c2539`, which added the SYS-025 collapse control.
It supersedes the earlier run over `e8077564b5503b2b02bd51230657f25cad00cd85`.

## Provision and command

| Item | Exact value |
| --- | --- |
| Producer | CPython `3.13.11`; Selenium `4.46.0` |
| Browser | Google Chrome for Testing `151.0.7922.47`, `linux64`, x86-64 |
| Driver | ChromeDriver `151.0.7922.47`, matching branch-head build |
| Provision manifest | Declared revision `r1654411` |
| Chrome archive SHA-256 | `14ac03a67e154e3f8bbc57e03ef03315fda8fedff8e045eee8b31500283a33f4` |
| Driver archive SHA-256 | `2faa72828261cd3c5ff00cbc71cfca57a12c26c1406e084e1a34d8d90e292140` |
| Display | Xvfb `21.1.24-1`, `4096x3072x24` |

The harness hashes both archives, invokes both binaries, checks the Selenium capability
versions, and creates profiles, caches, downloads, and observations under `/tmp`.
`r1654411` is provision-manifest metadata, not a browser/driver version report.

```console
KRT_CHROME_FOR_TESTING_ROOT=/home/stefan/.cache/kirin-rewrite-tracer/chrome-for-testing/151.0.7922.47 \
  xvfb-run -a -s '-screen 0 4096x3072x24' \
  uv run --python 3.13.11 --frozen python -m pytest -q -m browser
```

Final handoff-candidate result: `47 passed, 177 deselected`, no failure or skip.

[`browser_harness.py`](../../../test/browser_harness.py) applies CDP network blocking
for `ftp/http/https/ws/wss`, records every request, CSP violation, and console entry,
and verifies local-file relocation. The clean/hostile probes in
[`test_browser_harness.py`](../../../test/test_browser_harness.py) prove the monitors can
see attempted network, CSP, and console activity rather than merely reporting empty
logs. [`test_export_browser.py`](../../../test/test_export_browser.py) and the viewer
tests assert zero page network requests, no CSP violation, no unexpected console entry,
and no hostile execution under that denial.

## Action audit

| Actions | Durable artifacts | Clause result |
| --- | --- | --- |
| SYSV-021 | [`test_viewer_provenance.py`](../../../test/test_viewer_provenance.py) | Implemented: the exact edge policy is exercised, but every tagged occurrence is not hovered in both directions. |
| SYSV-022 | [`test_viewer_metadata.py`](../../../test/test_viewer_metadata.py) | Passed: definition suffixes, exact owner inventory, hostile inert text, geometry/scroll/dismissal, and role invalidation. |
| SYSV-020 | [`test_viewer_selection.py`](../../../test/test_viewer_selection.py), [`test_viewer_projection.py`](../../../test/test_viewer_projection.py) | Implemented; isolated metadata schema/namespace/key and rendered qualified-type near-misses do not complete the procedure. |
| SYSV-026 | [`test_viewer_collapse.py`](../../../test/test_viewer_collapse.py) | Implemented; structure, subtree hiding, nested retention, eligibility, disabled presentation, range bounding, Clear persistence, and Enter/Space parity pass on the depth-three selection fixture, which is the only tree exercised. |
| SYSV-023 | [`test_viewer_accessibility.py`](../../../test/test_viewer_accessibility.py), [`test_viewer_collapse.py`](../../../test/test_viewer_collapse.py) | Implemented; targeted Tab/Shift+Tab checks do not record exhaustive forward/reverse traversal of every visible event control. |
| SYSV-024 | [`test_viewer_styling.py`](../../../test/test_viewer_styling.py), [`test_viewer_styling_browser.py`](../../../test/test_viewer_styling_browser.py) | Implemented; active-overlay visible/nonzero geometry is not measured in all four required zoom/viewport combinations. |
| SYSV-019 | [`test_export_browser.py`](../../../test/test_export_browser.py), viewer fixtures | Implemented for the artifact combinations and hostile-domain gap recorded in the [source ledger](source-and-wheel-verification.md#action-audit). |
| INTV-007 | Selection, projection, provenance, metadata, and facts browser tests | Implemented; the complete reducer cross-product is not one clause-complete durable action. |
| UNITV-008 | Export, style, harness, and hostile browser tests | Passed with the source-side encoder and full Rich projection evidence. |

The finite styling matrix uses real 100%/200% page zoom at `640×480`, one-pixel
boundaries, `1280×800`, asymmetric wide/tall, and seeded larger viewports. Samples below
either floor are labelled exclusions. It does not prove unbounded reachability.

## Known nonconformances

- **SYSV-018 / INTV-006:** the green regression
  [`test_unconfirmed_publication_is_never_rolled_back`](../../../test/test_export.py)
  creates the destination hard link and then raises. `export_html` reports failure,
  removes its temporary file, but leaves the target. This violates the specified
  “failed publication leaves no target” clause; raced/pre-existing no-overwrite
  behavior still passes.
- **SYSV-025 / INTV-008:** pinned Blink caps the scroll extent for valid unbounded
  snapshot text, so a later nonzero control is unreachable at both zooms. See the
  [layout analysis](sysv-025-layout-invariant.md). The bounded accessibility, style, and
  finite-layout cases remain useful without satisfying the universal clause.
