# Source and Installed-Wheel Verification

This ledger records the 2026-07-31 non-browser release-candidate run. Production source
identity is commit `e8077564b5503b2b02bd51230657f25cad00cd85`; this handoff changes
documentation and adds only the detector counterexample test.

## Locked environment

| Item | Exact value |
| --- | --- |
| Host | Linux `7.1.5-arch1-1`, x86-64 |
| CPython | `3.10.14`, `3.11.9`, `3.12.13`, `3.13.11` |
| Product | `kirin-rewrite-tracer 0.1.0` |
| Kirin | `0.23.0.dev0`, PEP 610 commit and requested revision `7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a` |
| Rich | `15.0.0` |
| Test/build tools | pytest `8.4.2`; Selenium `4.46.0`; build `1.5.0`; Hatchling `1.31.0` |
| Quality tools | uv `0.12.0`; Ruff `0.16.1`; mypy `1.20.2`; pre-commit `4.6.1`; Git `2.55.0` |

The sibling checkout was clean at the same full Kirin SHA. The lockfile pins that VCS
URL and each installed environment's Kirin `direct_url.json` reports the requested and
resolved full SHA; the tracer wheel merely carries the pinned dependency requirement.
No source/API fingerprint was treated as commit proof.

## Commands and results

The source command was expanded once for each exact version:

```console
uv run --isolated --python <3.10.14|3.11.9|3.12.13|3.13.11> \
  --frozen python -m pytest -q -m 'not browser'
```

Each run passed `177` tests, deselected the `41` browser tests, and had no failure or
skip. The candidate distribution command was:

```console
uv build --out-dir /tmp/krt-handoff-final-distributions
```

It successfully built both `kirin_rewrite_tracer-0.1.0.tar.gz` and
`kirin_rewrite_tracer-0.1.0-py3-none-any.whl`, with the wheel built from the candidate
source distribution. For each CPython version, these commands created a fresh
`/tmp/krt-handoff-e807-installed-<310|311|312|313>` venv, installed that exact wheel and
CI acceptance dependencies, proved the import came from its `site-packages`, and ran
the tests:

```console
uv venv --python <exact-version> <fresh-venv>
uv pip install --python <fresh-venv>/bin/python \
  /tmp/krt-handoff-final-distributions/kirin_rewrite_tracer-0.1.0-py3-none-any.whl \
  pytest==8.4.2 selenium==4.46.0 \
  'kirin-toolchain[vmath] @ git+https://github.com/QuEraComputing/kirin.git@7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a'
env -u PYTHONPATH -u VIRTUAL_ENV PYTHONNOUSERSITE=1 \
  <fresh-venv>/bin/python -m pytest -q -m 'not browser' test
```

Each installed run also passed `177`, deselected `41`, and had no failure or skip.
A probe in every environment located `kirin_rewrite_tracer.__file__` inside that
venv's `site-packages`, never under the worktree. Temporary distributions and
environments were removed after inspection.

## Quality gates

| Command | Result |
| --- | --- |
| `uv run --frozen ruff check .` | All checks passed. |
| `uv run --frozen ruff format --check .` | All `89` files were already formatted. |
| `uv run --frozen mypy src test` | No issues in `34` source files. |
| `uv run --frozen pre-commit run --all-files` | Ruff check, Ruff format, mypy, and pytest hooks passed. |
| `python3 ../.agents/skills/document-repository-v-model/scripts/lint_repository_docs.py . --fail-on-warn` | `0` errors and `0` warnings. |
| `git diff --check` | No finding. |

The sibling `kirin/` checkout was clean at the pinned SHA. JavaScript execution was
verified only through the pinned headed-Chrome harness; no Node toolchain was added.

## Action audit

“Passed” below means the action's entire named procedure is covered; a green aggregate
does not strengthen an incomplete action.

| Actions | Durable artifacts | Clause result |
| --- | --- | --- |
| SYSV-001, SYSV-008 | [`test_acceptance.py`](../../../test/test_acceptance.py), [`test_session.py`](../../../test/test_session.py) | Implemented: hierarchy/results are independently checked, but nested pairs lack independent full-payload before/after oracles. |
| SYSV-010 | [`test_acceptance.py`](../../../test/test_acceptance.py), [`test_session.py`](../../../test/test_session.py) | Passed for valid ordinary entries, six pinned overrides, late/pre-bound/unbound/super calls, and same-instance dispatch. SYSV-004 separately fails invalid-use rejection. |
| INTV-001 | [`test_session.py`](../../../test/test_session.py) | Passed: lifecycle, identities, caught/later errors, analysis states, and live-reference release. |
| INTV-005, UNITV-005 | [`test_mutation.py`](../../../test/test_mutation.py), [`test_stack.py`](../../../test/test_stack.py) | Passed: five descriptors, tokens, nesting, binding, exceptions, rollback, bypass, foreign replacement, and frame-free stacks. |
| UNITV-008 | [`test_export.py`](../../../test/test_export.py), [`test_viewer_styling.py`](../../../test/test_viewer_styling.py), [browser ledger](browser-verification.md#action-audit) | Passed: primitive rejection, hostile/raw-text and non-BMP encoding, every Rich projection, CSP/DOM/console/request inactivity. |
| SYSV-002 | [`test_compat.py`](../../../test/test_compat.py), [`test_session.py`](../../../test/test_session.py) | Implemented; theme, indentation, hint, analysis, and highlighter variations do not complete the procedure. |
| SYSV-003 | [`test_acceptance.py`](../../../test/test_acceptance.py), [`test_session.py`](../../../test/test_session.py) | Implemented; no single traced/untraced fixture checks every final order, parent, use, metadata, and styled-snapshot clause. |
| SYSV-005–007 | [`test_snapshot.py`](../../../test/test_snapshot.py), [`test_model.py`](../../../test/test_model.py) | Implemented; the exhaustive inventory, Rich meta-domain, and representation-path procedures remain incomplete. |
| SYSV-012–017 | [`test_mutation.py`](../../../test/test_mutation.py), [`test_stack.py`](../../../test/test_stack.py), [`test_model.py`](../../../test/test_model.py), [`test_acceptance.py`](../../../test/test_acceptance.py) | Implemented; the full identity-reuse, all-cardinality/index, stack, delete/detach/container, and incomplete combinations are not all exercised. |
| SYSV-019 | [`test_export.py`](../../../test/test_export.py), [browser ledger](browser-verification.md#action-audit) | Implemented; empty, complete, aggregate-incomplete, and hostile strings across every canonical free-form domain are not combined as specified. |
| INTV-003, UNITV-001–002 | [`test_model.py`](../../../test/test_model.py) | Implemented; forced object-ID reuse and every graph/equality/normalization injection in the procedures are incomplete. |
| INTV-004, UNITV-003 | [`test_snapshot.py`](../../../test/test_snapshot.py) | Implemented; all capture paths run, but the complete cross-version instrumentation procedure is not durable. |
| INTV-007, UNITV-007, UNITV-009–010 | [`test_model.py`](../../../test/test_model.py), [`test_viewer_projection.py`](../../../test/test_viewer_projection.py), [browser ledger](browser-verification.md#action-audit) | Implemented; all reducer/interleaving/schema-near-miss and rebuild combinations are not fully table-driven. |
| UNITV-006 | [`test_stack.py`](../../../test/test_stack.py) | Implemented; the identical marked-callsite, hostile, deep, lifetime, and incomplete fixture is not executed in every minor as one full procedure. |

The failing detector, publication, and universal-layout actions have dedicated evidence:
[detector inspection](detector-portability-inspection.md),
[browser/export audit](browser-verification.md#known-nonconformances), and
[large-viewport analysis](sysv-025-layout-invariant.md).
