from __future__ import annotations

import hashlib
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_EVIDENCE = _ROOT / ".agents" / "v-model" / "evidence" / "sysv-025-layout-invariant.md"
_VERIFICATION = _ROOT / ".agents" / "v-model" / "verification" / "viewer-styling.md"
_REVIEWED = {
    "src/kirin_rewrite_tracer/assets/viewer.css": (
        "9146e62939e9f76ff2a0d6bfe112a67ca512775c4ec4ad11f3f44868f4f06a11"
    ),
    "src/kirin_rewrite_tracer/assets/viewer.js": (
        "97ddeb29073909709fd204ee7dc3b61e3ad8ba64b367278406f048a9f76568ac"
    ),
    "src/kirin_rewrite_tracer/_export.py": (
        "d8acfd848a1043e08658349c71cd8cf470042d2be25c9123d97474dc2c796260"
    ),
    "src/kirin_rewrite_tracer/_encoding.py": (
        "434d433816772498a7de53e7c970f87cc93da955d7790fe3be5fe5fcc383f8aa"
    ),
    "src/kirin_rewrite_tracer/_model.py": (
        "a9f1a5298dc1fd94f0b3229a09110fda6389785e6138c99a004b01cdda88e4f3"
    ),
    "test/test_viewer_styling_browser.py": (
        "129bd134144c2974ddb3a5e7fbbc653238e2d58a36bbec9ccd040cd42398deb1"
    ),
    "test/browser_harness.py": (
        "de14b9538590bcd2dd68c490e5a117cb50ee14b138d905925dc8f8103e6650f7"
    ),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rule_bodies(css: str, selector: str) -> tuple[str, ...]:
    return tuple(re.findall(rf"(?m)^{re.escape(selector)}\s*\{{([^}}]+)\}}", css))


def _rule_body(css: str, selector: str) -> str:
    bodies = _rule_bodies(css, selector)
    assert bodies, selector
    return bodies[0]


def test_sysv_025_analysis_records_complete_inventory_and_counterexample() -> None:
    evidence = _EVIDENCE.read_text(encoding="utf-8")
    css = (_ROOT / "src/kirin_rewrite_tracer/assets/viewer.css").read_text(
        encoding="utf-8"
    )
    javascript = (_ROOT / "src/kirin_rewrite_tracer/assets/viewer.js").read_text(
        encoding="utf-8"
    )
    exporter = (_ROOT / "src/kirin_rewrite_tracer/_export.py").read_text(
        encoding="utf-8"
    )
    encoding = (_ROOT / "src/kirin_rewrite_tracer/_encoding.py").read_text(
        encoding="utf-8"
    )
    model = (_ROOT / "src/kirin_rewrite_tracer/_model.py").read_text(encoding="utf-8")
    browser_test = (_ROOT / "test/test_viewer_styling_browser.py").read_text(
        encoding="utf-8"
    )
    verification = _VERIFICATION.read_text(encoding="utf-8")

    for relative, expected in _REVIEWED.items():
        assert _sha256(_ROOT / relative) == expected
        assert f"| `{relative}` | `{expected}` |" in evidence

    workspace = _rule_body(css, ".workspace")
    assert "display: flex" in workspace
    assert "flex-flow: row nowrap" in workspace
    assert "align-items: stretch" in workspace
    assert "gap: 0.75rem" in workspace
    assert "inline-size: 100%" in workspace
    assert "max-inline-size: 100%" in workspace
    assert "overflow: auto" in workspace
    assert "padding: 0.75rem" in workspace
    assert "font-family: system-ui, sans-serif" in _rule_body(css, "html")
    assert "margin: 0" in _rule_body(css, "body")
    assert "font: inherit" in _rule_body(css, "button,\n.skip-link")
    heading_margins = _rule_body(
        css,
        "h1,\nh2,\nh3,\nh4,\nh5,\nh6,\np",
    )
    assert "margin-block-start: 0" in heading_margins

    outer_columns = _rule_body(css, ".event-column,\n.ssa-workspace")
    assert "flex: 0 0 auto" in outer_columns
    assert "inline-size: max-content" in outer_columns
    component_columns = _rule_body(
        css,
        ".event-column,\n.state-column,\n.ssa-workspace",
    )
    assert "padding: 0.75rem" in component_columns
    assert "border: 1px solid var(--border)" in component_columns
    assert "min-inline-size: 24rem" in _rule_body(css, ".event-column")
    assert any(
        "min-inline-size: 22rem" in body for body in _rule_bodies(css, ".ssa-workspace")
    )

    state = _rule_body(css, ".state-column")
    assert "flex: 0 0 auto" in state
    assert "inline-size: max-content" in state
    assert "min-inline-size: 20rem" in state
    ssa_columns = _rule_body(css, ".ssa-columns")
    assert "display: flex" in ssa_columns
    assert "flex-flow: row nowrap" in ssa_columns
    assert "align-items: stretch" in ssa_columns
    assert "gap: 0.75rem" in ssa_columns
    assert "inline-size: max-content" in ssa_columns
    assert "min-inline-size: 100%" in ssa_columns

    event_tree = _rule_body(css, ".event-tree,\n.event-tree ol")
    assert "padding-inline-start: 1rem" in event_tree
    event_button = _rule_body(css, ".event-button")
    assert "inline-size: 100%" in event_button
    assert "white-space: nowrap" in event_button
    generic_button = _rule_body(css, "button")
    assert "padding: 0.4rem 0.6rem" in generic_button
    assert "border: 1px solid var(--border)" in css
    heading = _rule_body(css, ".column-heading")
    assert "display: flex" in heading
    assert "flex-flow: row nowrap" in heading
    assert "gap: 0.75rem" in heading
    assert "white-space: nowrap" in heading

    code = _rule_body(css, ".trace-code")
    assert "font-family: ui-monospace, monospace" in code
    assert "background: var(--code-background)" in code
    assert "white-space: pre" in css
    occurrence = _rule_body(css, ".ssa-occurrence")
    assert "position: relative" in occurrence
    assert "isolation: isolate" in occurrence
    assert "display: inline-block" in occurrence
    assert "margin: 0" in occurrence
    assert "padding: 3px" in occurrence
    assert "background: var(--code-background)" in occurrence
    assert "border: 0" in occurrence
    assert "font: inherit" in occurrence
    assert "line-height: inherit" in occurrence
    assert "vertical-align: baseline" in occurrence
    suffix = _rule_body(css, ".ssa-metadata-suffix")
    assert "color: var(--metadata)" in suffix
    assert "font-style: italic" in suffix
    assert "white-space: pre" in suffix

    cue = _rule_body(
        css,
        '.ssa-occurrence[data-provenance-related="true"]::after',
    )
    assert "position: absolute" in cue
    assert "z-index: 1" in cue
    assert "inset: 0" in cue
    assert "pointer-events: none" in cue
    assert "box-shadow: inset 0 0 0 2px var(--provenance)" in cue
    assert "position: fixed" in _rule_body(css, ".ssa-metadata-overlay")
    assert any("position: absolute" in body for body in _rule_bodies(css, ".skip-link"))

    assert "font-weight:700" in encoding
    assert "font-style:italic" in encoding
    assert "text-decoration-line:" in encoding
    assert "text-decoration-style:" in encoding
    assert "@media" not in css
    assert "@container" not in css
    assert "flex-wrap: wrap" not in css
    assert re.search(r"(?m)^\s*order\s*:", css) is None
    assert "!important" not in css

    assert javascript.count("columns.replaceChildren(") == 1
    assert "reducedColumns.map((column, index) => renderColumn(column, index))" in (
        javascript
    )
    assert ".hidden =" in javascript
    assert "emptyWorkspace.hidden = state.frontier.length !== 0" in javascript
    assert re.findall(
        r'\.style\.setProperty\(\s*"([^"]+)"',
        javascript,
    ) == [
        "--overlay-inline-start",
        "--overlay-block-start",
        "--overlay-inline-start",
        "--overlay-block-start",
    ]
    assert exporter.index('<section class="event-column"') < exporter.index(
        '<section class="ssa-workspace"'
    )
    assert exporter.count('<main class="workspace"') == 1
    assert exporter.count('<div class="ssa-columns"') == 1

    snapshot_model = model[
        model.index("class Snapshot:") : model.index("class MutationOperation:")
    ]
    assert "text: str" in snapshot_model
    assert "max_length" not in snapshot_model
    assert "size_limit" not in snapshot_model

    assert (
        "def test_blink_extent_cap_is_a_reproducible_universal_layout_counterexample"
        in browser_test
    )
    for literal in (
        "(100, 3_400_000, True, 33_554_432)",
        "(100, 3_600_000, False, 33_554_432)",
        "(200, 1_700_000, True, 16_777_216)",
        "(200, 1_800_000, False, 16_777_216)",
        "prefix_run_count=400",
        'split["maximumRunWidth"] < 100_000',
        "ElementClickInterceptedException",
    ):
        assert literal in browser_test
    assert (
        "def test_supported_fixture_zoom_no_wrap_layout_matrix_and_floor_exclusions"
        in browser_test
    )

    separator = "\N{MULTIPLICATION SIGN}"
    for width, height in (
        (640, 480),
        (641, 480),
        (640, 481),
        (641, 481),
        (1280, 800),
        (1600, 480),
        (640, 1000),
        (1307, 727),
        (1260, 766),
        (1354, 730),
        (1435, 818),
        (639, 480),
        (640, 479),
    ):
        assert f"`{width} {separator} {height}`" in evidence

    for statement in (
        "**Analysis result: failing.**",
        "`scrollWidth` caps at `33,554,432`",
        "`scrollWidth` caps at `16,777,216`",
        "splits four million characters across 400 style spans",
        "when it reproduces this known nonconformance",
        "It is not passing evidence",
        "They establish no compatibility result.",
        "cannot be reported as passing",
    ):
        assert statement in evidence
    assert "100% and 200%" in evidence
    assert "below-floor" in evidence
    assert "exclusions" in evidence

    sysv_025 = verification[verification.index("## SYSV-025") :]
    assert "- **Status:** failing" in sysv_025
    assert "../evidence/sysv-025-layout-invariant.md" in sysv_025
    assert "`33,554,432`" in sysv_025
    assert "`16,777,216`" in sysv_025
