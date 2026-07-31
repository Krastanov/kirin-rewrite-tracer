from __future__ import annotations

import random
import struct
import zlib
from dataclasses import replace
from itertools import pairwise
from math import ceil, floor
from pathlib import Path
from typing import Any, cast

import pytest
from browser_harness import BrowserHarness
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.webdriver import ActionChains, Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from test_viewer_styling import (
    _MONOKAI_STANDARD,
    _WINDOWS_16,
    _XTERM_256,
    _meta,
    _trace_with_styles,
)
from viewer_fixtures import (
    COARSE_PROVENANCE_ENTITY_IDS,
    COARSE_PROVENANCE_EVENT_ID,
    METADATA_EVENT_IDS,
    coarse_provenance_trace,
    metadata_trace,
)

from kirin_rewrite_tracer import Trace, export_html
from kirin_rewrite_tracer._model import (
    ColorRecord,
    EntityOccurrence,
    StyleRecord,
    StyleSpan,
)

_TOKENS = {
    "canvas": "#0B1020",
    "surface": "#111827",
    "raised": "#1F2937",
    "text": "#F3F4F6",
    "muted": "#CBD5E1",
    "border": "#94A3B8",
    "selected": "#1E3A5F",
    "selected-marker": "#93C5FD",
    "metadata": "#7DD3FC",
    "provenance": "#FBBF24",
    "focus": "#F472B6",
    "code-foreground": "#D9D9D9",
    "code-background": "#0C0C0C",
}
_CONTRAST_MATRIX = {
    ("text", "canvas"): 17.2033,
    ("text", "surface"): 16.1195,
    ("text", "raised"): 13.3384,
    ("text", "selected"): 10.4520,
    ("muted", "canvas"): 12.7517,
    ("muted", "surface"): 11.9483,
    ("muted", "raised"): 9.8869,
    ("border", "canvas"): 7.3839,
    ("border", "surface"): 6.9187,
    ("border", "raised"): 5.7250,
    ("selected-marker", "selected"): 6.3787,
    ("selected-marker", "surface"): 9.8375,
    ("provenance", "code-background"): 11.7180,
    ("focus", "canvas"): 7.1484,
    ("focus", "surface"): 6.6980,
    ("focus", "raised"): 5.5424,
    ("focus", "selected"): 4.3431,
    ("metadata", "code-background"): 11.7327,
    ("code-foreground", "code-background"): 13.8584,
}


def _open_trace(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
    trace: Trace,
    name: str,
) -> Chrome:
    source = export_html(trace, tmp_path / f"{name}.html")
    relocated = tmp_path / f"{name}-relocated"
    relocated.mkdir()
    headed_chrome.open_relocated(source, relocated)
    return headed_chrome.driver


def _activate(
    driver: Chrome,
    event_id: str,
    *,
    shift: bool = False,
) -> None:
    driver.execute_script(
        """
        activateEvent(arguments[0], {
          shiftKey: arguments[1],
          ctrlKey: false,
          metaKey: false
        });
        """,
        event_id,
        shift,
    )


def _settle(driver: Chrome) -> None:
    driver.execute_async_script(
        """
        const done = arguments[0];
        requestAnimationFrame(() => requestAnimationFrame(done));
        """
    )


def _rgb(hex_color: str) -> str:
    value = hex_color.removeprefix("#")
    channels = tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))
    return f"rgb({channels[0]}, {channels[1]}, {channels[2]})"


def _luminance(hex_color: str) -> float:
    value = hex_color.removeprefix("#")
    channels = [int(value[index : index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(left: str, right: str) -> float:
    left_luminance = _luminance(left)
    right_luminance = _luminance(right)
    lighter = max(left_luminance, right_luminance)
    darker = min(left_luminance, right_luminance)
    return (lighter + 0.05) / (darker + 0.05)


def _true_tab_to(driver: Chrome, target: WebElement) -> None:
    previous = cast(
        WebElement,
        driver.execute_script(
            """
            const target = arguments[0];
            const controls = Array.from(
              document.querySelectorAll(
                'a[href], button, [tabindex]:not([tabindex="-1"])'
              )
            ).filter(control =>
              !control.hidden &&
              control.closest("[hidden]") === null &&
              !control.disabled &&
              control.tabIndex >= 0
            );
            const index = controls.indexOf(target);
            if (index <= 0) {
              throw new Error("target lacks a preceding sequential control");
            }
            controls[index - 1].focus({preventScroll: true});
            return controls[index - 1];
            """,
            target,
        ),
    )
    assert previous != target
    ActionChains(driver).send_keys(Keys.TAB).perform()
    _settle(driver)
    assert driver.switch_to.active_element == target


def _palette_trace() -> tuple[Trace, dict[str, dict[str, str]]]:
    candidates: list[tuple[StyleRecord, dict[str, str]]] = []
    inherited = {
        "color": _rgb("#D9D9D9"),
        "background": "rgba(0, 0, 0, 0)",
    }

    def add(style: StyleRecord, **overrides: str) -> None:
        candidates.append((style, {**inherited, **overrides}))

    add(StyleRecord(""))
    add(StyleRecord(""))
    add(
        StyleRecord("", color=ColorRecord("default", "default-fg", None, None)),
        color=_rgb("#D9D9D9"),
    )
    add(
        StyleRecord(
            "",
            bgcolor=ColorRecord("default", "default-bg", None, None),
        ),
        background=_rgb("#0C0C0C"),
    )
    for encoding, palette in (
        ("standard", _MONOKAI_STANDARD),
        ("eight_bit", _XTERM_256),
        ("windows", _WINDOWS_16),
    ):
        for number, expected in enumerate(palette):
            color = ColorRecord(encoding, f"{encoding}-{number}", number, None)
            add(StyleRecord("", color=color), color=_rgb(expected))
            add(StyleRecord("", bgcolor=color), background=_rgb(expected))
    for triplet in ((0, 0, 0), (1, 2, 3), (17, 34, 51), (255, 255, 255)):
        expected = f"#{triplet[0]:02X}{triplet[1]:02X}{triplet[2]:02X}"
        color = ColorRecord("truecolor", f"rgb-{expected}", None, triplet)
        add(StyleRecord("", color=color), color=_rgb(expected))
        add(StyleRecord("", bgcolor=color), background=_rgb(expected))
    add(
        StyleRecord(
            "",
            color=ColorRecord("truecolor", "foreground", None, (100, 120, 140)),
            bgcolor=ColorRecord("truecolor", "background", None, (10, 20, 30)),
            reverse=True,
            dim=True,
        ),
        color=_rgb("#0B1015"),
        background=_rgb("#64788C"),
    )
    add(
        StyleRecord(
            "",
            bold=True,
            italic=True,
            underline2=True,
            strike=True,
            overline=True,
        ),
        font_weight="700",
        font_style="italic",
        decoration_style="double",
    )
    hostile = 'https://invalid.example/");animation:krt-unsafe 1s'
    add(
        StyleRecord(
            "",
            blink=True,
            blink2=False,
            conceal=None,
            frame=True,
            encircle=False,
            link=hostile,
            meta=_meta({"unsafe": hostile, "typed": [True, False, None]}),
        ),
        inert="true",
    )

    styles = tuple(
        replace(candidate, id=f"style-{index}")
        for index, (candidate, _) in enumerate(candidates)
    )
    expected_by_id = {
        style.id: candidates[index][1] for index, style in enumerate(styles)
    }
    return _trace_with_styles(styles, include_none=True), expected_by_id


def _with_occurrence_backgrounds(
    trace: Trace,
    snapshot_id: str,
    backgrounds: dict[str, tuple[int, int, int]],
) -> Trace:
    index = trace.index()
    snapshot = index.snapshot(snapshot_id)
    intervals: list[tuple[int, int, str, tuple[int, int, int]]] = []
    styles = list(trace.styles)
    for entity_id, triplet in backgrounds.items():
        occurrences = [
            index.occurrence(occurrence_id)
            for occurrence_id in snapshot.occurrence_ids
            if index.occurrence(occurrence_id).entity_id == entity_id
            and index.occurrence(occurrence_id).role == "definition"
        ]
        assert len(occurrences) == 1
        occurrence = occurrences[0]
        intervals.append(
            (
                occurrence.start,
                occurrence.end,
                entity_id,
                triplet,
            )
        )

    shifted_spans: list[StyleSpan] = []
    replacement_ids: dict[
        tuple[str | None, str, tuple[int, int, int]],
        str,
    ] = {}
    for span in snapshot.style_spans:
        boundaries = {span.start, span.end}
        for start, end, _, _ in intervals:
            if span.start <= start <= span.end:
                boundaries.add(start)
            if span.start <= end <= span.end:
                boundaries.add(end)
        ordered = sorted(boundaries)
        for start, end in pairwise(ordered):
            style_id: str | None = span.style_id
            for interval_start, interval_end, entity_id, triplet in intervals:
                if interval_start <= start and end <= interval_end:
                    key = (span.style_id, entity_id, triplet)
                    style_id = replacement_ids.get(key)
                    if style_id is None:
                        style_id = f"style-{len(styles)}"
                        background = ColorRecord(
                            "truecolor",
                            f"paint-oracle-{entity_id}",
                            None,
                            triplet,
                        )
                        if span.style_id is None:
                            styles.append(
                                StyleRecord(
                                    style_id,
                                    bgcolor=background,
                                )
                            )
                        else:
                            styles.append(
                                replace(
                                    index.style(span.style_id),
                                    id=style_id,
                                    bgcolor=background,
                                )
                            )
                        replacement_ids[key] = style_id
                    break
            shifted_spans.append(StyleSpan(start, end, style_id))

    updated_snapshot = replace(snapshot, style_spans=tuple(shifted_spans))
    return replace(
        trace,
        styles=tuple(styles),
        snapshots=tuple(
            updated_snapshot if candidate.id == snapshot.id else candidate
            for candidate in trace.snapshots
        ),
    )


def _opaque_provenance_trace() -> Trace:
    trace = coarse_provenance_trace()
    event = trace.index().event(COARSE_PROVENANCE_EVENT_ID)
    assert event.after_snapshot_id is not None
    return _with_occurrence_backgrounds(
        trace,
        event.after_snapshot_id,
        {
            COARSE_PROVENANCE_ENTITY_IDS["split_destination_left"]: (
                0,
                55,
                218,
            )
        },
    )


def _adversarial_identity_provenance_trace() -> Trace:
    trace = metadata_trace()
    event = trace.index().event(METADATA_EVENT_IDS["A"])
    assert event.after_snapshot_id is not None
    return _with_occurrence_backgrounds(
        trace,
        event.after_snapshot_id,
        {
            "entity-1": (251, 191, 36),
            "entity-2": (250, 190, 35),
        },
    )


def _extent_counterexample_trace(
    character_count: int = 4_000_000,
    *,
    prefix_run_count: int = 1,
) -> Trace:
    assert 0 < prefix_run_count <= character_count
    trace = metadata_trace()
    snapshot = trace.snapshots[0]
    prefix = "x" * character_count
    shifted_spans = (
        *(
            StyleSpan(
                (character_count * index) // prefix_run_count,
                (character_count * (index + 1)) // prefix_run_count,
                "style-0",
            )
            for index in range(prefix_run_count)
        ),
        *(
            StyleSpan(
                span.start + character_count,
                span.end + character_count,
                span.style_id,
            )
            for span in snapshot.style_spans
        ),
    )
    shifted_occurrences = tuple(
        EntityOccurrence(
            occurrence.id,
            occurrence.snapshot_id,
            occurrence.entity_id,
            occurrence.role,
            (
                0
                if occurrence.snapshot_id == snapshot.id
                and occurrence.role == "container"
                else occurrence.start + character_count
                if occurrence.snapshot_id == snapshot.id
                else occurrence.start
            ),
            (
                occurrence.end + character_count
                if occurrence.snapshot_id == snapshot.id
                else occurrence.end
            ),
        )
        for occurrence in trace.occurrences
    )
    shifted_snapshot = replace(
        snapshot,
        text=prefix + snapshot.text,
        style_spans=shifted_spans,
    )
    return replace(
        trace,
        snapshots=(shifted_snapshot, *trace.snapshots[1:]),
        occurrences=shifted_occurrences,
    )


def _decode_png(encoded: bytes) -> tuple[int, int, tuple[bytes, ...]]:
    assert encoded.startswith(b"\x89PNG\r\n\x1a\n")
    position = 8
    width = 0
    height = 0
    channels = 0
    compressed = bytearray()
    while position < len(encoded):
        length = struct.unpack(">I", encoded[position : position + 4])[0]
        kind = encoded[position + 4 : position + 8]
        data = encoded[position + 8 : position + 8 + length]
        position += 12 + length
        if kind == b"IHDR":
            (
                width,
                height,
                bit_depth,
                color_type,
                compression,
                filtering,
                interlace,
            ) = struct.unpack(">IIBBBBB", data)
            assert bit_depth == 8
            assert color_type in {2, 6}
            assert compression == 0
            assert filtering == 0
            assert interlace == 0
            channels = 3 if color_type == 2 else 4
        elif kind == b"IDAT":
            compressed.extend(data)
        elif kind == b"IEND":
            break
    assert width > 0 and height > 0 and channels > 0

    raw = zlib.decompress(bytes(compressed))
    stride = width * channels
    rows: list[bytes] = []
    previous = bytearray(stride)
    offset = 0

    def paeth(left: int, above: int, upper_left: int) -> int:
        estimate = left + above - upper_left
        left_distance = abs(estimate - left)
        above_distance = abs(estimate - above)
        upper_left_distance = abs(estimate - upper_left)
        if left_distance <= above_distance and left_distance <= upper_left_distance:
            return left
        if above_distance <= upper_left_distance:
            return above
        return upper_left

    for _ in range(height):
        filter_kind = raw[offset]
        offset += 1
        scanline = bytearray(raw[offset : offset + stride])
        offset += stride
        for index, value in enumerate(scanline):
            left = scanline[index - channels] if index >= channels else 0
            above = previous[index]
            upper_left = previous[index - channels] if index >= channels else 0
            if filter_kind == 1:
                scanline[index] = (value + left) & 0xFF
            elif filter_kind == 2:
                scanline[index] = (value + above) & 0xFF
            elif filter_kind == 3:
                scanline[index] = (value + ((left + above) // 2)) & 0xFF
            elif filter_kind == 4:
                scanline[index] = (value + paeth(left, above, upper_left)) & 0xFF
            else:
                assert filter_kind == 0
        rows.append(bytes(scanline))
        previous = scanline
    assert offset == len(raw)
    return width, height, tuple(rows)


def _paint_count(
    rows: tuple[bytes, ...],
    *,
    channels: int,
    bounds: dict[str, float],
    scale: float,
    color: tuple[int, int, int],
) -> int:
    image_height = len(rows)
    image_width = len(rows[0]) // channels
    left = max(0, floor((bounds["left"] - 6) * scale))
    right = min(image_width, ceil((bounds["right"] + 6) * scale))
    top = max(0, floor((bounds["top"] - 6) * scale))
    bottom = min(image_height, ceil((bounds["bottom"] + 6) * scale))
    count = 0
    for row in rows[top:bottom]:
        for column in range(left, right):
            start = column * channels
            if tuple(row[start : start + 3]) == color:
                count += 1
    return count


def _pixel_rgb(
    rows: tuple[bytes, ...],
    *,
    channels: int,
    column: int,
    row: int,
) -> tuple[int, int, int]:
    start = column * channels
    return tuple(rows[row][start : start + 3])  # type: ignore[return-value]


def _vertical_paint_samples(
    rows: tuple[bytes, ...],
    *,
    channels: int,
    bounds: dict[str, float],
    scale: float,
) -> tuple[tuple[float, tuple[int, int, int]], ...]:
    image_height = len(rows)
    image_width = len(rows[0]) // channels
    column = min(
        image_width - 1,
        max(0, floor(((bounds["left"] + bounds["right"]) / 2) * scale)),
    )
    top = max(0, floor(bounds["top"] * scale))
    bottom = min(image_height, ceil(bounds["bottom"] * scale))
    return tuple(
        (
            ((row + 0.5) / scale) - bounds["top"],
            _pixel_rgb(rows, channels=channels, column=column, row=row),
        )
        for row in range(top, bottom)
    )


def _incomplete_metadata_trace() -> Trace:
    trace = metadata_trace()
    before = trace.snapshots[0]
    event = replace(
        trace.events[0],
        completion="incomplete",
        after_snapshot_id=None,
        result=None,
    )
    return replace(
        trace,
        complete=False,
        snapshots=(before,),
        occurrences=tuple(
            occurrence
            for occurrence in trace.occurrences
            if occurrence.snapshot_id == before.id
        ),
        metadata=tuple(
            record for record in trace.metadata if record.snapshot_id == before.id
        ),
        events=(event,),
    )


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_all_rich_palette_classes_compute_from_one_inert_cascade(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    trace, expected = _palette_trace()
    before = repr(trace)
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        trace,
        "viewer-styling-rich-palette",
    )
    assert repr(trace) == before
    _activate(driver, "event-0")

    observed = cast(
        dict[str, Any],
        driver.execute_script(
            """
            const firstColumn = document.querySelector(".state-column");
            const runs = Array.from(
              firstColumn.querySelectorAll(".captured-run")
            ).map(run => {
              const style = getComputedStyle(run);
              return {
                styleId: run.dataset.styleId,
                classes: Array.from(run.classList),
                color: style.color,
                background: style.backgroundColor,
                fontWeight: style.fontWeight,
                fontStyle: style.fontStyle,
                decorationLine: style.textDecorationLine,
                decorationStyle: style.textDecorationStyle,
                animationName: style.animationName,
                visibility: style.visibility,
                display: style.display
              };
            });
            const generatedRules = Array.from(
              document.styleSheets[0].cssRules
            ).filter(rule =>
              rule.selectorText?.startsWith(".kr-captured-style-")
            ).map(rule => rule.selectorText);
            const rootRules = Array.from(
              document.styleSheets[0].cssRules
            ).filter(rule => rule.selectorText === ":root");
            const styleText = document.querySelector("style").textContent;
            const finalStateIndex = styleText.indexOf(
              "/* Final semantic state and keyboard-focus rules. */"
            );
            const generatedIndexes = generatedRules.map(selector =>
              styleText.indexOf(`${selector}{`)
            );
            return {
              runs,
              generatedRules,
              rootRuleCount: rootRules.length,
              stylesheetCount: document.styleSheets.length,
              styleElementCount: document.querySelectorAll("style").length,
              markerCount: styleText.split(
                "/* KRT_GENERATED_RICH_STYLES */"
              ).length - 1,
              generatedBeforeFinal: generatedIndexes.every(
                index => index >= 0 && index < finalStateIndex
              ),
              styleAttributeCount:
                document.querySelectorAll("[style]").length,
              hrefs: Array.from(
                document.querySelectorAll("[href]")
              ).map(element => element.getAttribute("href")),
              resourceElements:
                document.querySelectorAll(
                  "img, iframe, link, audio, video, source, canvas, svg"
                ).length,
              deferredControls: Array.from(
                document.querySelectorAll("button, [role]")
              ).filter(element =>
                /theme|search|filter|graph|print|persist/i.test(
                  `${element.textContent} ${element.getAttribute("aria-label") || ""}`
                )
              ).length,
              canonicalUnchanged:
                JSON.stringify(trace) === JSON.stringify(
                  JSON.parse(
                    document.getElementById("trace-data").textContent
                  ).trace
                ),
              unsafeInStylesheet: styleText.includes("krt-unsafe"),
              activeCapturedLinks:
                document.querySelectorAll("a .captured-run").length
            };
            """
        ),
    )

    runs = cast(list[dict[str, Any]], observed["runs"])
    assert len(runs) == len(trace.styles) + 1
    for run, style in zip(runs[:-1], trace.styles, strict=True):
        style_id = cast(str, run["styleId"])
        assert style_id == style.id
        expectation = expected[style_id]
        assert run["color"] == expectation["color"]
        assert run["background"] == expectation["background"]
        assert run["animationName"] == "none"
        assert run["visibility"] == "visible"
        assert run["display"] == "inline"
        assert run["classes"][0] == "captured-run"
        assert (
            len(
                [
                    name
                    for name in cast(list[str], run["classes"])
                    if name.startswith("kr-captured-style-")
                ]
            )
            == 1
        )
        if "font_weight" in expectation:
            assert run["fontWeight"] == expectation["font_weight"]
            assert run["fontStyle"] == expectation["font_style"]
            assert set(cast(str, run["decorationLine"]).split()) == {
                "underline",
                "line-through",
                "overline",
            }
            assert run["decorationStyle"] == expectation["decoration_style"]
    none_run = runs[-1]
    assert none_run["styleId"] == ""
    assert none_run["classes"] == ["captured-run"]
    assert none_run["color"] == _rgb("#D9D9D9")
    assert none_run["background"] == "rgba(0, 0, 0, 0)"

    generated_rules = cast(list[str], observed["generatedRules"])
    assert len(generated_rules) == len(trace.styles) - 1
    assert generated_rules == [
        f".kr-captured-style-{index}" for index in range(len(generated_rules))
    ]
    projection_classes = cast(
        list[str],
        driver.execute_script(
            "return projection.styles.map(style => style.css_class);"
        ),
    )
    assert projection_classes[0] == projection_classes[1]
    assert len(set(projection_classes)) == len(trace.styles) - 1
    assert observed == {
        **observed,
        "rootRuleCount": 1,
        "stylesheetCount": 1,
        "styleElementCount": 1,
        "markerCount": 1,
        "generatedBeforeFinal": True,
        "styleAttributeCount": 0,
        "hrefs": ["#ssa-workspace"],
        "resourceElements": 0,
        "deferredControls": 0,
        "canonicalUnchanged": True,
        "unsafeInStylesheet": False,
        "activeCapturedLinks": 0,
    }
    observations = headed_chrome.observations()
    assert observations.page_network_requests() == ()
    assert observations.csp_violations == ()
    assert observations.console == ()


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_blink_extent_cap_is_a_reproducible_universal_layout_counterexample(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    cases = (
        (100, 3_400_000, True, 33_554_432),
        (100, 3_600_000, False, 33_554_432),
        (200, 1_700_000, True, 16_777_216),
        (200, 1_800_000, False, 16_777_216),
    )
    observations: list[dict[str, Any]] = []

    try:
        for zoom, character_count, reachable, engine_cap in cases:
            driver = _open_trace(
                headed_chrome,
                tmp_path,
                _extent_counterexample_trace(character_count),
                f"viewer-styling-extent-{zoom}-{character_count}",
            )
            headed_chrome.set_page_zoom(zoom)
            headed_chrome.set_css_viewport(640, 480)
            _activate(driver, METADATA_EVENT_IDS["A"])
            geometry = cast(
                dict[str, Any],
                driver.execute_script(
                    """
                    const workspace = document.querySelector(".workspace");
                    const states = Array.from(
                      document.querySelectorAll(".state-column")
                    );
                    const firstCode = states[0].querySelector(".trace-code");
                    const firstRun =
                      firstCode.querySelector(".captured-run");
                    const controls = Array.from(
                      states[states.length - 1].querySelectorAll(
                        ".ssa-occurrence"
                      )
                    );
                    const finalControl = controls[controls.length - 1];
                    const canvas = document.createElement("canvas");
                    const context = canvas.getContext("2d");
                    const style = getComputedStyle(firstRun);
                    context.font = [
                      style.fontStyle,
                      style.fontVariant,
                      style.fontWeight,
                      style.fontSize,
                      style.fontFamily
                    ].join(" ");
                    const characterAdvance = context.measureText("x").width;
                    workspace.scrollLeft = workspace.scrollWidth;
                    const maximumScrollLeft = workspace.scrollLeft;
                    finalControl.scrollIntoView({
                      block: "nearest",
                      inline: "nearest",
                      behavior: "instant"
                    });
                    const workspaceBox = workspace.getBoundingClientRect();
                    const controlBox = finalControl.getBoundingClientRect();
                    return {
                      clientWidth: workspace.clientWidth,
                      scrollWidth: workspace.scrollWidth,
                      maximumScrollLeft,
                      revealScrollLeft: workspace.scrollLeft,
                      expectedPrefixWidth:
                        characterAdvance * arguments[0],
                      characterAdvance,
                      firstStateWidth:
                        states[0].getBoundingClientRect().width,
                      stateOrder: states.map(state => state.dataset.roles),
                      runCount:
                        firstCode.querySelectorAll(".captured-run").length,
                      noWrap:
                        getComputedStyle(firstCode).whiteSpace === "pre" &&
                        getComputedStyle(
                          document.querySelector(".ssa-columns")
                        ).flexWrap === "nowrap",
                      finalControlNonzero:
                        controlBox.width > 0 && controlBox.height > 0,
                      finalControlHorizontallyVisible:
                        controlBox.left >= workspaceBox.left - 1 &&
                        controlBox.right <= workspaceBox.right + 1
                    };
                    """,
                    character_count,
                ),
            )
            assert geometry["stateOrder"] == [
                "event-0.before",
                "event-0.after",
            ]
            assert geometry["noWrap"] is True
            assert geometry["finalControlNonzero"] is True
            assert geometry["runCount"] >= 3
            assert geometry["maximumScrollLeft"] == pytest.approx(
                geometry["scrollWidth"] - geometry["clientWidth"],
                abs=1,
            )
            final_control = driver.find_elements(
                By.CSS_SELECTOR,
                ".state-column:last-child .ssa-occurrence",
            )[-1]
            if reachable:
                assert geometry["expectedPrefixWidth"] < engine_cap
                assert geometry["scrollWidth"] < engine_cap
                assert geometry["finalControlHorizontallyVisible"] is True
                final_control.click()
                _settle(driver)
                assert driver.find_elements(
                    By.CSS_SELECTOR,
                    ".ssa-metadata-overlay",
                )
                final_control.send_keys(Keys.ESCAPE)
            else:
                assert geometry["expectedPrefixWidth"] > engine_cap
                assert geometry["scrollWidth"] == engine_cap
                assert geometry["finalControlHorizontallyVisible"] is False
                with pytest.raises(ElementClickInterceptedException):
                    final_control.click()
            observations.append(
                {
                    "zoom": zoom,
                    "characterCount": character_count,
                    "reachable": reachable,
                    **geometry,
                }
            )
            page = headed_chrome.observations()
            assert page.page_network_requests() == ()
            assert page.csp_violations == ()
            assert page.console == ()

        driver = _open_trace(
            headed_chrome,
            tmp_path,
            _extent_counterexample_trace(
                4_000_000,
                prefix_run_count=400,
            ),
            "viewer-styling-extent-split-runs",
        )
        headed_chrome.set_page_zoom(100)
        headed_chrome.set_css_viewport(640, 480)
        _activate(driver, METADATA_EVENT_IDS["A"])
        split = cast(
            dict[str, Any],
            driver.execute_script(
                """
                const workspace = document.querySelector(".workspace");
                const states = document.querySelectorAll(".state-column");
                const firstCode = states[0].querySelector(".trace-code");
                const controls = states[states.length - 1].querySelectorAll(
                  ".ssa-occurrence"
                );
                const finalControl = controls[controls.length - 1];
                workspace.scrollLeft = workspace.scrollWidth;
                const maximumScrollLeft = workspace.scrollLeft;
                const runWidths = Array.from(
                  firstCode.querySelectorAll(".captured-run")
                ).map(run => run.getBoundingClientRect().width);
                finalControl.scrollIntoView({
                  block: "nearest",
                  inline: "nearest",
                  behavior: "instant"
                });
                const workspaceBox = workspace.getBoundingClientRect();
                const controlBox = finalControl.getBoundingClientRect();
                return {
                  clientWidth: workspace.clientWidth,
                  scrollWidth: workspace.scrollWidth,
                  runCount: runWidths.length,
                  maximumRunWidth: Math.max(...runWidths),
                  maximumScrollLeft,
                  revealScrollLeft: workspace.scrollLeft,
                  finalControlVisible:
                    controlBox.left >= workspaceBox.left - 1 &&
                    controlBox.right <= workspaceBox.right + 1
                };
                """
            ),
        )
        assert split["runCount"] >= 400
        assert split["maximumRunWidth"] < 100_000
        assert split["scrollWidth"] == 33_554_432
        assert split["maximumScrollLeft"] == pytest.approx(
            split["scrollWidth"] - split["clientWidth"],
            abs=1,
        )
        assert split["revealScrollLeft"] == pytest.approx(
            split["maximumScrollLeft"],
            abs=1,
        )
        assert split["finalControlVisible"] is False
        split_final_control = driver.find_elements(
            By.CSS_SELECTOR,
            ".state-column:last-child .ssa-occurrence",
        )[-1]
        with pytest.raises(ElementClickInterceptedException):
            split_final_control.click()
        page = headed_chrome.observations()
        assert page.page_network_requests() == ()
        assert page.csp_violations == ()
        assert page.console == ()
    finally:
        headed_chrome.set_page_zoom(100)

    assert [
        (
            observation["zoom"],
            observation["characterCount"],
            observation["reachable"],
        )
        for observation in observations
    ] == [(zoom, count, reachable) for zoom, count, reachable, _ in cases]


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_fixed_tokens_contrast_selection_suffix_and_focus_cascade(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        metadata_trace(),
        "viewer-styling-tokens-focus",
    )
    tokens = cast(
        dict[str, str],
        driver.execute_script(
            """
            const style = getComputedStyle(document.documentElement);
            return Object.fromEntries(
              arguments[0].map(name => [
                name,
                style.getPropertyValue(`--${name}`).trim().toUpperCase()
              ])
            );
            """,
            list(_TOKENS),
        ),
    )
    assert tokens == _TOKENS
    for pair, expected in _CONTRAST_MATRIX.items():
        actual = _contrast(tokens[pair[0]], tokens[pair[1]])
        assert actual == pytest.approx(expected, abs=0.00005), pair
        threshold = (
            4.5
            if pair[0]
            in {
                "text",
                "muted",
                "metadata",
                "code-foreground",
            }
            else 3.0
        )
        assert actual >= threshold, pair

    ActionChains(driver).send_keys(Keys.TAB).perform()
    skip = driver.find_element(By.CSS_SELECTOR, ".skip-link")
    assert driver.switch_to.active_element == skip
    skip_focus = cast(
        dict[str, str],
        driver.execute_script(
            """
            const style = getComputedStyle(arguments[0]);
            return {
              color: style.outlineColor,
              width: style.outlineWidth,
              offset: style.outlineOffset,
              kind: style.outlineStyle
            };
            """,
            skip,
        ),
    )
    assert skip_focus == {
        "color": _rgb(_TOKENS["focus"]),
        "width": "2px",
        "offset": "2px",
        "kind": "solid",
    }

    ActionChains(driver).send_keys(Keys.ENTER).perform()
    workspace = driver.find_element(By.ID, "ssa-workspace")
    assert driver.switch_to.active_element == workspace
    assert cast(
        bool,
        driver.execute_script(
            """
            const style = getComputedStyle(arguments[0]);
            return arguments[0].matches(":focus-visible") &&
              style.outlineColor === arguments[1] &&
              style.outlineWidth === "2px" &&
              style.outlineOffset === "2px";
            """,
            workspace,
            _rgb(_TOKENS["focus"]),
        ),
    )

    _activate(driver, METADATA_EVENT_IDS["A"])
    selected = driver.find_element(
        By.CSS_SELECTOR,
        f'.event-button[data-event-id="{METADATA_EVENT_IDS["A"]}"]',
    )
    _true_tab_to(driver, selected)
    selected_style = cast(
        dict[str, str],
        driver.execute_script(
            """
            const style = getComputedStyle(arguments[0]);
            return {
              background: style.backgroundColor,
              shadow: style.boxShadow,
              outline: style.outlineColor,
              outlineWidth: style.outlineWidth,
              outlineOffset: style.outlineOffset
            };
            """,
            selected,
        ),
    )
    assert selected_style["background"] == _rgb(_TOKENS["selected"])
    assert "inset" in selected_style["shadow"]
    assert "3px" in selected_style["shadow"]
    assert _rgb(_TOKENS["selected-marker"]) in selected_style["shadow"]
    assert selected_style["outline"] == _rgb(_TOKENS["focus"])
    assert selected_style["outlineWidth"] == "2px"
    assert selected_style["outlineOffset"] == "2px"

    suffixes = cast(
        list[dict[str, str]],
        driver.execute_script(
            """
            return Array.from(
              document.querySelectorAll(".ssa-metadata-suffix")
            ).map(suffix => {
              const style = getComputedStyle(suffix);
              return {
                text: suffix.textContent,
                color: style.color,
                fontStyle: style.fontStyle,
                whiteSpace: style.whiteSpace
              };
            });
            """
        ),
    )
    assert suffixes
    assert " ⟦⟧" in {suffix["text"] for suffix in suffixes}
    assert all(suffix["text"].startswith(" ⟦") for suffix in suffixes)
    assert all(suffix["text"].endswith("⟧") for suffix in suffixes)
    assert all(suffix["color"] == _rgb(_TOKENS["metadata"]) for suffix in suffixes)
    assert all(suffix["fontStyle"] == "italic" for suffix in suffixes)
    assert all(suffix["whiteSpace"] == "pre" for suffix in suffixes)
    assert not driver.find_elements(
        By.CSS_SELECTOR,
        '.ssa-occurrence[data-occurrence-role="reference"] + .ssa-metadata-suffix',
    )

    occurrence = driver.find_element(
        By.CSS_SELECTOR,
        '.ssa-occurrence[data-occurrence-role="definition"]',
    )
    occurrence.click()
    overlay = driver.find_element(By.CSS_SELECTOR, ".ssa-metadata-overlay")
    _true_tab_to(driver, overlay)
    overlay_scroll_before = cast(
        list[int],
        driver.execute_script(
            """
            return [
              arguments[0].scrollTop,
              arguments[0].scrollHeight,
              arguments[0].clientHeight
            ];
            """,
            overlay,
        ),
    )
    assert overlay_scroll_before[0] == 0
    assert overlay_scroll_before[1] > overlay_scroll_before[2]
    ActionChains(driver).send_keys(Keys.PAGE_DOWN).perform()
    _settle(driver)
    assert (
        cast(
            int,
            driver.execute_script("return arguments[0].scrollTop;", overlay),
        )
        > overlay_scroll_before[0]
    )
    overlay_style = cast(
        dict[str, Any],
        driver.execute_script(
            """
            const overlay = arguments[0];
            const style = getComputedStyle(overlay);
            return {
              background: style.backgroundColor,
              color: style.color,
              border: style.borderColor,
              outline: style.outlineColor,
              outlineWidth: style.outlineWidth,
              outlineOffset: style.outlineOffset,
              inlineStyles: Array.from(overlay.style).sort(),
              allStyled: Array.from(document.querySelectorAll("[style]")).map(
                element => element.className
              )
            };
            """,
            overlay,
        ),
    )
    assert overlay_style == {
        "background": _rgb(_TOKENS["raised"]),
        "color": _rgb(_TOKENS["text"]),
        "border": _rgb(_TOKENS["border"]),
        "outline": _rgb(_TOKENS["focus"]),
        "outlineWidth": "2px",
        "outlineOffset": "2px",
        "inlineStyles": [
            "--overlay-block-start",
            "--overlay-inline-start",
        ],
        "allStyled": ["ssa-metadata-overlay"],
    }
    accessibility = headed_chrome.accessibility_tree()
    assert accessibility.matching(
        role="region",
        name=overlay.accessible_name,
    )
    assert not any(node.role == "tooltip" for node in accessibility.nodes)
    ActionChains(driver).send_keys(Keys.ESCAPE).perform()
    _settle(driver)
    assert not driver.find_elements(By.CSS_SELECTOR, ".ssa-metadata-overlay")
    assert not driver.find_elements(By.CSS_SELECTOR, "[style]")

    observations = headed_chrome.observations()
    assert observations.page_network_requests() == ()
    assert observations.csp_violations == ()
    assert observations.console == ()


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_absent_neighbor_description_is_distinct_and_no_tooltip_role_exists(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        _incomplete_metadata_trace(),
        "viewer-styling-absent-neighbor",
    )
    _activate(driver, METADATA_EVENT_IDS["A"])
    occurrence = driver.find_element(By.CSS_SELECTOR, ".ssa-occurrence")
    description_id = cast(str, occurrence.get_attribute("aria-describedby"))
    description = cast(
        str,
        driver.find_element(By.ID, description_id).get_attribute("textContent"),
    )

    assert "Right neighbor event-0.after" in description
    assert "column roles event-0.after: absent SSA state." in description
    assert "Right neighbor event-0.after; column roles event-0.after: present;" not in (
        description
    )
    accessibility = headed_chrome.accessibility_tree()
    assert not any(node.role == "tooltip" for node in accessibility.nodes)


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_focused_related_occurrence_keeps_captured_style_and_both_cues(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        _opaque_provenance_trace(),
        "viewer-styling-provenance-focus",
    )
    headed_chrome.set_page_zoom(100)
    headed_chrome.set_css_viewport(3400, 900)
    _activate(driver, COARSE_PROVENANCE_EVENT_ID)
    source = driver.find_element(
        By.CSS_SELECTOR,
        (
            ".state-column:nth-of-type(1) .ssa-occurrence"
            f'[data-entity-id="{COARSE_PROVENANCE_ENTITY_IDS["split_source"]}"]'
        ),
    )
    target = driver.find_element(
        By.CSS_SELECTOR,
        (
            ".state-column:nth-of-type(2) .ssa-occurrence"
            f'[data-entity-id="'
            f'{COARSE_PROVENANCE_ENTITY_IDS["split_destination_left"]}"]'
        ),
    )
    initial_boxes = cast(
        dict[str, Any],
        driver.execute_script(
            """
            const box = element => {
              const value = element.getBoundingClientRect();
              return {
                left: value.left,
                right: value.right,
                top: value.top,
                bottom: value.bottom
              };
            };
            return {
              viewport: [
                document.documentElement.clientWidth,
                document.documentElement.clientHeight
              ],
              source: box(arguments[0]),
              target: box(arguments[1]),
              bothVisible: [arguments[0], arguments[1]].every(element => {
                  const box = element.getBoundingClientRect();
                  return (
                    box.left >= 0 &&
                box.right <= document.documentElement.clientWidth &&
                box.top >= 0 &&
                    box.bottom <= document.documentElement.clientHeight
                  );
              })
            };
            """,
            source,
            target,
        ),
    )
    assert initial_boxes["bothVisible"] is True, initial_boxes
    _true_tab_to(driver, target)
    before = cast(
        dict[str, Any],
        driver.execute_script(
            """
            const target = arguments[0];
            const run = target.querySelector(".captured-run");
            const box = target.getBoundingClientRect();
            const style = getComputedStyle(run);
            return {
              box: [box.width, box.height],
              text: target.textContent,
              runStyleId: run.dataset.styleId,
              runClasses: Array.from(run.classList),
              runColor: style.color,
              runBackground: style.backgroundColor
            };
            """,
            target,
        ),
    )

    ActionChains(driver).move_to_element(source).perform()
    _settle(driver)
    assert driver.switch_to.active_element == target
    combined = cast(
        dict[str, Any],
        driver.execute_script(
            """
            const target = arguments[0];
            const run = target.querySelector(".captured-run");
            const box = target.getBoundingClientRect();
            const targetStyle = getComputedStyle(target);
            const cueStyle = getComputedStyle(target, "::after");
            const runStyle = getComputedStyle(run);
            return {
              related: target.dataset.provenanceRelated,
              focusVisible: target.matches(":focus-visible"),
              shadow: cueStyle.boxShadow,
              outline: targetStyle.outlineColor,
              outlineWidth: targetStyle.outlineWidth,
              outlineOffset: targetStyle.outlineOffset,
              box: [box.width, box.height],
              bounds: {
                left: box.left,
                right: box.right,
                top: box.top,
                bottom: box.bottom
              },
              text: target.textContent,
              runStyleId: run.dataset.styleId,
              runClasses: Array.from(run.classList),
              runColor: runStyle.color,
              runBackground: runStyle.backgroundColor
            };
            """,
            target,
        ),
    )
    assert combined["related"] == "true"
    assert combined["focusVisible"] is True
    assert "inset" in combined["shadow"]
    assert "2px" in combined["shadow"]
    assert _rgb(_TOKENS["provenance"]) in combined["shadow"]
    assert combined["outline"] == _rgb(_TOKENS["focus"])
    assert combined["outlineWidth"] == "2px"
    assert combined["outlineOffset"] == "2px"
    assert combined["runBackground"] == _rgb("#0037DA")
    for key in (
        "box",
        "text",
        "runStyleId",
        "runClasses",
        "runColor",
        "runBackground",
    ):
        assert combined[key] == before[key]

    png_width, png_height, pixels = _decode_png(driver.get_screenshot_as_png())
    viewport = cast(
        list[int],
        driver.execute_script("return [window.innerWidth, window.innerHeight];"),
    )
    scale_x = png_width / viewport[0]
    scale_y = png_height / viewport[1]
    assert scale_x == pytest.approx(scale_y, abs=0.01)
    channels = len(pixels[0]) // png_width
    assert channels in {3, 4}
    paint_counts = {
        "opaque-blue": _paint_count(
            pixels,
            channels=channels,
            bounds=cast(dict[str, float], combined["bounds"]),
            scale=scale_x,
            color=(0, 55, 218),
        ),
        "provenance-yellow": _paint_count(
            pixels,
            channels=channels,
            bounds=cast(dict[str, float], combined["bounds"]),
            scale=scale_x,
            color=(251, 191, 36),
        ),
        "focus-pink": _paint_count(
            pixels,
            channels=channels,
            bounds=cast(dict[str, float], combined["bounds"]),
            scale=scale_x,
            color=(244, 114, 182),
        ),
    }
    assert paint_counts["opaque-blue"] > 0
    assert paint_counts["provenance-yellow"] > 0
    assert paint_counts["focus-pink"] > 0
    assert list(tmp_path.rglob("*.png")) == []


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_fixed_surface_moat_isolates_exact_and_near_provenance_backgrounds(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    trace = _adversarial_identity_provenance_trace()
    event = trace.index().event(METADATA_EVENT_IDS["A"])
    assert event.after_snapshot_id is not None
    expected_text = trace.index().snapshot(event.after_snapshot_id).text
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        trace,
        "viewer-styling-adversarial-provenance",
    )
    cases = (
        ("entity-1", (251, 191, 36)),
        ("entity-2", (250, 190, 35)),
    )

    def details(target: WebElement) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            driver.execute_script(
                """
                const target = arguments[0];
                const runs = Array.from(
                  target.querySelectorAll(".captured-run")
                );
                const bounds = element => {
                  const box = element.getBoundingClientRect();
                  return {
                    left: box.left,
                    right: box.right,
                    top: box.top,
                    bottom: box.bottom,
                    width: box.width,
                    height: box.height
                  };
                };
                const targetStyle = getComputedStyle(target);
                return {
                  targetBounds: bounds(target),
                  runs: runs.map(run => {
                    const style = getComputedStyle(run);
                    return {
                      bounds: bounds(run),
                      styleId: run.dataset.styleId,
                      classes: Array.from(run.classList),
                      color: style.color,
                      background: style.backgroundColor
                    };
                  }),
                  text: target.textContent,
                  targetBackground: targetStyle.backgroundColor,
                  display: targetStyle.display,
                  padding: [
                    targetStyle.paddingTop,
                    targetStyle.paddingRight,
                    targetStyle.paddingBottom,
                    targetStyle.paddingLeft
                  ],
                  verticalAlign: targetStyle.verticalAlign,
                  lineHeight: targetStyle.lineHeight,
                  related: target.dataset.provenanceRelated || null,
                  focusVisible: target.matches(":focus-visible"),
                  shadow: getComputedStyle(target, "::after").boxShadow,
                  outline: targetStyle.outlineColor,
                  outlineWidth: targetStyle.outlineWidth,
                  outlineOffset: targetStyle.outlineOffset
                };
                """,
                target,
            ),
        )

    try:
        for zoom in (100, 200):
            headed_chrome.set_page_zoom(zoom)
            headed_chrome.set_css_viewport(1280, 800)
            _activate(driver, METADATA_EVENT_IDS["A"])
            source_column = driver.find_element(
                By.CSS_SELECTOR,
                ".state-column:nth-of-type(1)",
            )
            target_column = driver.find_element(
                By.CSS_SELECTOR,
                ".state-column:nth-of-type(2)",
            )
            driver.execute_script(
                """
                arguments[0].scrollIntoView({
                  block: "nearest",
                  inline: "end",
                  behavior: "instant"
                });
                """,
                target_column,
            )
            _settle(driver)
            projection = cast(
                dict[str, Any],
                driver.execute_script(
                    """
                    const runs = Array.from(
                      arguments[0].querySelectorAll(".captured-run")
                    );
                    const suffixes = Array.from(
                      arguments[0].querySelectorAll(".ssa-metadata-suffix")
                    );
                    return {
                      capturedText: runs.map(run => run.textContent).join(""),
                      suffixes: suffixes.map(suffix => suffix.textContent),
                      runCount: runs.length,
                      occurrenceText: Array.from(
                        arguments[0].querySelectorAll(".ssa-occurrence")
                      ).map(occurrence => occurrence.textContent)
                    };
                    """,
                    target_column,
                ),
            )
            assert projection["capturedText"] == expected_text
            assert projection["runCount"] > len(
                cast(list[str], projection["occurrenceText"])
            )
            assert all(
                suffix.startswith(" \u27e6") and suffix.endswith("\u27e7")
                for suffix in cast(list[str], projection["suffixes"])
            )

            targets: dict[str, WebElement] = {}
            sources: dict[str, WebElement] = {}
            baseline: dict[str, dict[str, Any]] = {}
            for entity_id, background in cases:
                selector = f'.ssa-occurrence[data-entity-id="{entity_id}"]'
                sources[entity_id] = source_column.find_element(
                    By.CSS_SELECTOR,
                    selector,
                )
                targets[entity_id] = target_column.find_element(
                    By.CSS_SELECTOR,
                    selector,
                )
                baseline[entity_id] = details(targets[entity_id])
                baseline_runs = cast(
                    list[dict[str, Any]],
                    baseline[entity_id]["runs"],
                )
                assert baseline_runs
                assert {run["background"] for run in baseline_runs} == {
                    f"rgb({background[0]}, {background[1]}, {background[2]})"
                }
                assert baseline[entity_id]["targetBackground"] == _rgb(
                    _TOKENS["code-background"]
                )
                assert baseline[entity_id]["display"] == "inline-block"
                assert baseline[entity_id]["padding"] == [
                    "3px",
                    "3px",
                    "3px",
                    "3px",
                ]
                assert baseline[entity_id]["verticalAlign"] == "baseline"
                assert baseline[entity_id]["related"] is None

            before_width, before_height, before_pixels = _decode_png(
                driver.get_screenshot_as_png()
            )
            viewport = cast(
                list[int],
                driver.execute_script(
                    "return [window.innerWidth, window.innerHeight];"
                ),
            )
            scale = before_width / viewport[0]
            assert before_height / viewport[1] == pytest.approx(scale, abs=0.01)
            channels = len(before_pixels[0]) // before_width

            for entity_id, _ in cases:
                source = sources[entity_id]
                target = targets[entity_id]
                _true_tab_to(driver, source)
                driver.execute_script(
                    """
                    arguments[0].scrollIntoView({
                      block: "nearest",
                      inline: "end",
                      behavior: "instant"
                    });
                    """,
                    target_column,
                )
                _settle(driver)
                current = details(target)
                assert current["related"] == "true"
                for key in (
                    "targetBounds",
                    "runs",
                    "text",
                    "targetBackground",
                    "display",
                    "padding",
                    "verticalAlign",
                    "lineHeight",
                ):
                    assert current[key] == baseline[entity_id][key]
                assert "inset" in current["shadow"]
                assert "2px" in current["shadow"]
                assert _rgb(_TOKENS["provenance"]) in current["shadow"]

                after_width, after_height, after_pixels = _decode_png(
                    driver.get_screenshot_as_png()
                )
                assert (after_width, after_height) == (before_width, before_height)
                target_bounds = cast(dict[str, float], current["targetBounds"])
                run_bounds = [
                    cast(dict[str, float], run["bounds"])
                    for run in cast(list[dict[str, Any]], current["runs"])
                ]
                left = max(0, floor(target_bounds["left"] * scale))
                right = min(
                    after_width,
                    ceil(target_bounds["right"] * scale),
                )
                top = max(0, floor(target_bounds["top"] * scale))
                bottom = min(
                    after_height,
                    ceil(target_bounds["bottom"] * scale),
                )
                changed: list[
                    tuple[int, int, tuple[int, int, int], tuple[int, int, int]]
                ] = []
                for row in range(top, bottom):
                    y = (row + 0.5) / scale
                    for column in range(left, right):
                        x = (column + 0.5) / scale
                        before_rgb = _pixel_rgb(
                            before_pixels,
                            channels=channels,
                            column=column,
                            row=row,
                        )
                        after_rgb = _pixel_rgb(
                            after_pixels,
                            channels=channels,
                            column=column,
                            row=row,
                        )
                        if before_rgb != after_rgb:
                            changed.append((column, row, before_rgb, after_rgb))
                            assert not (
                                any(
                                    bounds["left"] <= x < bounds["right"]
                                    and bounds["top"] <= y < bounds["bottom"]
                                    for bounds in run_bounds
                                )
                            )
                assert changed
                assert {
                    (before_rgb, after_rgb) for _, _, before_rgb, after_rgb in changed
                } == {
                    (
                        (12, 12, 12),
                        (251, 191, 36),
                    )
                }
                vertical = _vertical_paint_samples(
                    after_pixels,
                    channels=channels,
                    bounds=target_bounds,
                    scale=scale,
                )
                ring = [color for offset, color in vertical if 0.25 <= offset < 1.75]
                separator = [color for offset, color in vertical if 2.0 <= offset < 3.0]
                assert ring and set(ring) == {(251, 191, 36)}
                assert separator and set(separator) == {(12, 12, 12)}

            exact_source = sources["entity-1"]
            exact_target = targets["entity-1"]
            _true_tab_to(driver, exact_target)
            ActionChains(driver).move_to_element(exact_source).perform()
            _settle(driver)
            combined = details(exact_target)
            assert combined["related"] == "true"
            assert combined["focusVisible"] is True
            assert combined["outline"] == _rgb(_TOKENS["focus"])
            assert combined["outlineWidth"] == "2px"
            assert combined["outlineOffset"] == "2px"
            combined_target_bounds = cast(
                dict[str, float],
                combined["targetBounds"],
            )
            baseline_target_bounds = cast(
                dict[str, float],
                baseline["entity-1"]["targetBounds"],
            )
            assert (
                combined_target_bounds["width"],
                combined_target_bounds["height"],
            ) == (
                baseline_target_bounds["width"],
                baseline_target_bounds["height"],
            )
            combined_runs = cast(list[dict[str, Any]], combined["runs"])
            baseline_runs = cast(
                list[dict[str, Any]],
                baseline["entity-1"]["runs"],
            )
            assert len(combined_runs) == len(baseline_runs)
            for combined_run, baseline_run in zip(
                combined_runs,
                baseline_runs,
                strict=True,
            ):
                for key in ("styleId", "classes", "color", "background"):
                    assert combined_run[key] == baseline_run[key]
                combined_bounds = cast(
                    dict[str, float],
                    combined_run["bounds"],
                )
                baseline_bounds = cast(
                    dict[str, float],
                    baseline_run["bounds"],
                )
                assert (
                    combined_bounds["left"] - combined_target_bounds["left"],
                    combined_bounds["top"] - combined_target_bounds["top"],
                    combined_bounds["width"],
                    combined_bounds["height"],
                ) == (
                    baseline_bounds["left"] - baseline_target_bounds["left"],
                    baseline_bounds["top"] - baseline_target_bounds["top"],
                    baseline_bounds["width"],
                    baseline_bounds["height"],
                )
            _, _, combined_pixels = _decode_png(driver.get_screenshot_as_png())
            assert (
                _paint_count(
                    combined_pixels,
                    channels=channels,
                    bounds=cast(dict[str, float], combined["targetBounds"]),
                    scale=scale,
                    color=(251, 191, 36),
                )
                > 0
            )
            assert (
                _paint_count(
                    combined_pixels,
                    channels=channels,
                    bounds=cast(dict[str, float], combined["targetBounds"]),
                    scale=scale,
                    color=(244, 114, 182),
                )
                > 0
            )
    finally:
        headed_chrome.set_page_zoom(100)

    observations = headed_chrome.observations()
    assert observations.page_network_requests() == ()
    assert observations.csp_violations == ()
    assert observations.console == ()
    assert list(tmp_path.rglob("*.png")) == []


def _supported_viewports() -> tuple[tuple[int, int], ...]:
    generator = random.Random(25025)
    generated = tuple(
        (
            generator.randint(641, 1536),
            generator.randint(481, 960),
        )
        for _ in range(4)
    )
    assert generated == (
        (1307, 727),
        (1260, 766),
        (1354, 730),
        (1435, 818),
    )
    return (
        (640, 480),
        (641, 480),
        (640, 481),
        (641, 481),
        (1280, 800),
        (1600, 480),
        (640, 1000),
        *generated,
    )


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_supported_fixture_zoom_no_wrap_layout_matrix_and_floor_exclusions(
    headed_chrome: BrowserHarness,
    tmp_path: Path,
) -> None:
    driver = _open_trace(
        headed_chrome,
        tmp_path,
        metadata_trace(),
        "viewer-styling-layout-matrix",
    )
    reference_order: list[str] | None = None
    measured: list[tuple[int, int, int]] = []
    exclusions: list[tuple[int, int, int]] = []

    try:
        for zoom in (100, 200):
            zoom_measurement = headed_chrome.set_page_zoom(zoom)
            assert zoom_measurement.requested_percent == zoom
            assert zoom_measurement.visual_viewport_scale == 1.0
            _activate(driver, METADATA_EVENT_IDS["A"])
            _activate(driver, METADATA_EVENT_IDS["B"], shift=True)

            for width, height in _supported_viewports():
                viewport = headed_chrome.set_css_viewport(width, height)
                assert (viewport.css_width, viewport.css_height) == (width, height)

                driver.execute_script(
                    'document.querySelector(".workspace").scrollLeft = 0;'
                )
                clear = driver.find_element(By.CSS_SELECTOR, ".clear-selection")
                clear.click()
                assert driver.switch_to.active_element == clear
                assert cast(
                    dict[str, Any],
                    driver.execute_script(
                        """
                        const box = arguments[0].getBoundingClientRect();
                        return {
                          within:
                            box.left >= 0 &&
                            box.right <= document.documentElement.clientWidth &&
                            box.top >= 0 &&
                            box.bottom <= document.documentElement.clientHeight,
                          frontier:
                            document.getElementById("event-tree").dataset.frontier
                        };
                        """,
                        clear,
                    ),
                ) == {"within": True, "frontier": ""}

                _activate(driver, METADATA_EVENT_IDS["A"])
                _activate(driver, METADATA_EVENT_IDS["B"], shift=True)
                geometry = cast(
                    dict[str, Any],
                    driver.execute_script(
                        """
                    const workspace = document.querySelector(".workspace");
                    const eventColumn =
                      workspace.querySelector(".event-column");
                    const ssaWorkspace =
                      workspace.querySelector(".ssa-workspace");
                    const ssaColumns =
                      workspace.querySelector(".ssa-columns");
                    const states = Array.from(
                      workspace.querySelectorAll(".state-column")
                    );
                    const controls = Array.from(
                      workspace.querySelectorAll("button")
                    ).filter(control =>
                      !control.hidden &&
                      control.closest("[hidden]") === null
                    );
                    const codes = Array.from(
                      workspace.querySelectorAll(".trace-code")
                    );
                    const box = element => {
                      const value = element.getBoundingClientRect();
                      return {
                        left: value.left,
                        right: value.right,
                        top: value.top,
                        bottom: value.bottom,
                        width: value.width,
                        height: value.height
                      };
                    };
                    workspace.scrollLeft = 0;
                    const workspaceAtStart = box(workspace);
                    const eventAtStart = box(eventColumn);
                    const initialScrollLeft = workspace.scrollLeft;
                    const maximum =
                      workspace.scrollWidth - workspace.clientWidth;
                    workspace.scrollLeft = workspace.scrollWidth;
                    const maximumScrollLeft = workspace.scrollLeft;
                    const workspaceAtEnd = box(workspace);
                    const finalState = box(states[states.length - 1]);
                    const finalControl = box(
                      states[states.length - 1].querySelector(
                        ".ssa-occurrence"
                      )
                    );
                    const stateBoxes = states.map(box);
                    const workspaceStyle = getComputedStyle(workspace);
                    const ssaStyle = getComputedStyle(ssaColumns);
                    return {
                      clientWidth: workspace.clientWidth,
                      scrollWidth: workspace.scrollWidth,
                      initialScrollLeft,
                      maximum,
                      maximumScrollLeft,
                      order: states.map(state => state.dataset.roles),
                      stateBoxes,
                      stateFlexShrink: states.map(
                        state => getComputedStyle(state).flexShrink
                      ),
                      eventFlexShrink:
                        getComputedStyle(eventColumn).flexShrink,
                      ssaWorkspaceFlexShrink:
                        getComputedStyle(ssaWorkspace).flexShrink,
                      workspaceDisplay: workspaceStyle.display,
                      workspaceFlexWrap: workspaceStyle.flexWrap,
                      workspaceOverflowX: workspaceStyle.overflowX,
                      ssaDisplay: ssaStyle.display,
                      ssaFlexWrap: ssaStyle.flexWrap,
                      codeWhiteSpace: codes.map(
                        code => getComputedStyle(code).whiteSpace
                      ),
                      controlBoxesComplete: controls.every(control =>
                        control.getBoundingClientRect().width > 0 &&
                        control.getBoundingClientRect().height > 0
                      ),
                      eventVisibleAtStart:
                        eventAtStart.left >= workspaceAtStart.left - 1 &&
                        eventAtStart.right <= workspaceAtStart.right + 1,
                      finalVisibleAtEnd:
                        finalState.left >= workspaceAtEnd.left - 1 &&
                        finalState.right <= workspaceAtEnd.right + 1,
                      finalControlVisibleAtEnd:
                        finalControl.left >= workspaceAtEnd.left - 1 &&
                        finalControl.right <= workspaceAtEnd.right + 1 &&
                        finalControl.top >= workspaceAtEnd.top - 1 &&
                        finalControl.bottom <= workspaceAtEnd.bottom + 1
                    };
                        """
                    ),
                )
                order = cast(list[str], geometry["order"])
                if reference_order is None:
                    reference_order = order
                assert order == reference_order
                state_boxes = cast(list[dict[str, float]], geometry["stateBoxes"])
                assert len(state_boxes) == 3
                assert all(
                    box["width"] > 0 and box["height"] > 0 for box in state_boxes
                )
                assert all(
                    state_boxes[index]["right"] < state_boxes[index + 1]["left"]
                    for index in range(len(state_boxes) - 1)
                )
                assert (
                    max(box["top"] for box in state_boxes)
                    - min(box["top"] for box in state_boxes)
                    < 0.5
                )
                assert geometry["stateFlexShrink"] == ["0", "0", "0"]
                assert geometry["eventFlexShrink"] == "0"
                assert geometry["ssaWorkspaceFlexShrink"] == "0"
                assert geometry["workspaceDisplay"] == "flex"
                assert geometry["workspaceFlexWrap"] == "nowrap"
                assert geometry["workspaceOverflowX"] in {"auto", "scroll"}
                assert geometry["ssaDisplay"] == "flex"
                assert geometry["ssaFlexWrap"] == "nowrap"
                assert set(cast(list[str], geometry["codeWhiteSpace"])) == {"pre"}
                assert geometry["controlBoxesComplete"] is True
                assert geometry["eventVisibleAtStart"] is True
                assert geometry["finalVisibleAtEnd"] is True
                assert geometry["finalControlVisibleAtEnd"] is True
                assert geometry["initialScrollLeft"] == 0
                assert geometry["maximum"] >= 0
                assert geometry["maximumScrollLeft"] == pytest.approx(
                    geometry["maximum"],
                    abs=1,
                )
                assert geometry["scrollWidth"] >= geometry["clientWidth"]

                final_control = driver.find_element(
                    By.CSS_SELECTOR,
                    ".state-column:last-child .ssa-occurrence",
                )
                final_control.click()
                _settle(driver)
                assert driver.switch_to.active_element == final_control
                assert driver.find_elements(By.CSS_SELECTOR, ".ssa-metadata-overlay")
                final_visibility = cast(
                    dict[str, Any],
                    driver.execute_script(
                        """
                        const control = arguments[0];
                        const box = control.getBoundingClientRect();
                        return {
                          within:
                            box.left >= 0 &&
                            box.right <= document.documentElement.clientWidth &&
                            box.top >= 0 &&
                            box.bottom <= document.documentElement.clientHeight,
                          nonzero: box.width > 0 && box.height > 0
                        };
                        """,
                        final_control,
                    ),
                )
                assert final_visibility == {"within": True, "nonzero": True}
                final_control.send_keys(Keys.ESCAPE)
                _settle(driver)
                assert not driver.find_elements(
                    By.CSS_SELECTOR, ".ssa-metadata-overlay"
                )
                measured.append((zoom, width, height))

            for width, height in ((639, 480), (640, 479)):
                viewport = headed_chrome.set_css_viewport(width, height)
                assert (viewport.css_width, viewport.css_height) == (width, height)
                exclusions.append((zoom, width, height))
    finally:
        headed_chrome.set_page_zoom(100)

    assert measured == [
        (zoom, width, height)
        for zoom in (100, 200)
        for width, height in _supported_viewports()
    ]
    assert exclusions == [
        (100, 639, 480),
        (100, 640, 479),
        (200, 639, 480),
        (200, 640, 479),
    ]
    observations = headed_chrome.observations()
    assert observations.page_network_requests() == ()
    assert observations.csp_violations == ()
    assert observations.console == ()
