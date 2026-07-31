from __future__ import annotations

import re
from dataclasses import replace
from importlib.resources import files
from typing import Any, cast

import pytest
from viewer_fixtures import EventSpec, event_trace

import kirin_rewrite_tracer._export as export_module
from kirin_rewrite_tracer import Trace
from kirin_rewrite_tracer._encoding import (
    PrimitiveObject,
    _style_rule,
    encode_trace,
    generated_style_rules,
)
from kirin_rewrite_tracer._model import (
    ColorRecord,
    EntityOccurrence,
    FrozenMap,
    StyleRecord,
    StyleSpan,
    freeze_json,
)

_ASSETS = files("kirin_rewrite_tracer.assets")

# Literal independent Rich 15.0.0 / xterm reference tables. These constants do not
# call Rich or any production color resolver.
_MONOKAI_STANDARD = (
    "#1A1A1A",
    "#F4005F",
    "#98E024",
    "#FD971F",
    "#9D65FF",
    "#F4005F",
    "#58D1EB",
    "#C4C5B5",
    "#625E4C",
    "#F4005F",
    "#98E024",
    "#E0D561",
    "#9D65FF",
    "#F4005F",
    "#58D1EB",
    "#F6F6EF",
)
_WINDOWS_16 = (
    "#0C0C0C",
    "#C50F1F",
    "#13A10E",
    "#C19C00",
    "#0037DA",
    "#881798",
    "#3A96DD",
    "#CCCCCC",
    "#767676",
    "#E74856",
    "#16C60C",
    "#F9F1A5",
    "#3B78FF",
    "#B4009E",
    "#61D6D6",
    "#F2F2F2",
)
_XTERM_256 = tuple(
    """
    #000000 #800000 #008000 #808000 #000080 #800080 #008080 #C0C0C0
    #808080 #FF0000 #00FF00 #FFFF00 #0000FF #FF00FF #00FFFF #FFFFFF
    #000000 #00005F #000087 #0000AF #0000D7 #0000FF #005F00 #005F5F
    #005F87 #005FAF #005FD7 #005FFF #008700 #00875F #008787 #0087AF
    #0087D7 #0087FF #00AF00 #00AF5F #00AF87 #00AFAF #00AFD7 #00AFFF
    #00D700 #00D75F #00D787 #00D7AF #00D7D7 #00D7FF #00FF00 #00FF5F
    #00FF87 #00FFAF #00FFD7 #00FFFF #5F0000 #5F005F #5F0087 #5F00AF
    #5F00D7 #5F00FF #5F5F00 #5F5F5F #5F5F87 #5F5FAF #5F5FD7 #5F5FFF
    #5F8700 #5F875F #5F8787 #5F87AF #5F87D7 #5F87FF #5FAF00 #5FAF5F
    #5FAF87 #5FAFAF #5FAFD7 #5FAFFF #5FD700 #5FD75F #5FD787 #5FD7AF
    #5FD7D7 #5FD7FF #5FFF00 #5FFF5F #5FFF87 #5FFFAF #5FFFD7 #5FFFFF
    #870000 #87005F #870087 #8700AF #8700D7 #8700FF #875F00 #875F5F
    #875F87 #875FAF #875FD7 #875FFF #878700 #87875F #878787 #8787AF
    #8787D7 #8787FF #87AF00 #87AF5F #87AF87 #87AFAF #87AFD7 #87AFFF
    #87D700 #87D75F #87D787 #87D7AF #87D7D7 #87D7FF #87FF00 #87FF5F
    #87FF87 #87FFAF #87FFD7 #87FFFF #AF0000 #AF005F #AF0087 #AF00AF
    #AF00D7 #AF00FF #AF5F00 #AF5F5F #AF5F87 #AF5FAF #AF5FD7 #AF5FFF
    #AF8700 #AF875F #AF8787 #AF87AF #AF87D7 #AF87FF #AFAF00 #AFAF5F
    #AFAF87 #AFAFAF #AFAFD7 #AFAFFF #AFD700 #AFD75F #AFD787 #AFD7AF
    #AFD7D7 #AFD7FF #AFFF00 #AFFF5F #AFFF87 #AFFFAF #AFFFD7 #AFFFFF
    #D70000 #D7005F #D70087 #D700AF #D700D7 #D700FF #D75F00 #D75F5F
    #D75F87 #D75FAF #D75FD7 #D75FFF #D78700 #D7875F #D78787 #D787AF
    #D787D7 #D787FF #D7AF00 #D7AF5F #D7AF87 #D7AFAF #D7AFD7 #D7AFFF
    #D7D700 #D7D75F #D7D787 #D7D7AF #D7D7D7 #D7D7FF #D7FF00 #D7FF5F
    #D7FF87 #D7FFAF #D7FFD7 #D7FFFF #FF0000 #FF005F #FF0087 #FF00AF
    #FF00D7 #FF00FF #FF5F00 #FF5F5F #FF5F87 #FF5FAF #FF5FD7 #FF5FFF
    #FF8700 #FF875F #FF8787 #FF87AF #FF87D7 #FF87FF #FFAF00 #FFAF5F
    #FFAF87 #FFAFAF #FFAFD7 #FFAFFF #FFD700 #FFD75F #FFD787 #FFD7AF
    #FFD7D7 #FFD7FF #FFFF00 #FFFF5F #FFFF87 #FFFFAF #FFFFD7 #FFFFFF
    #080808 #121212 #1C1C1C #262626 #303030 #3A3A3A #444444 #4E4E4E
    #585858 #626262 #6C6C6C #767676 #808080 #8A8A8A #949494 #9E9E9E
    #A8A8A8 #B2B2B2 #BCBCBC #C6C6C6 #D0D0D0 #DADADA #E4E4E4 #EEEEEE
    """.split()  # noqa: SIM905 - the enumerated palette is reviewable by rows.
)
_TRISTATE_FIELDS = (
    "bold",
    "dim",
    "italic",
    "underline",
    "blink",
    "blink2",
    "reverse",
    "conceal",
    "strike",
    "underline2",
    "frame",
    "encircle",
    "overline",
)


def _style_projection(trace: Trace) -> list[PrimitiveObject]:
    projection = encode_trace(trace)["projection"]
    assert isinstance(projection, dict)
    styles = projection["styles"]
    assert isinstance(styles, list)
    return [cast(PrimitiveObject, item) for item in styles]


def _trace_with_styles(
    styles: tuple[StyleRecord, ...], *, include_none: bool = False
) -> Trace:
    trace = event_trace((EventSpec("Only", None, "before", "after"),))
    width = len(styles) + int(include_none)
    text = "x" * width
    spans = tuple(
        StyleSpan(index, index + 1, style.id) for index, style in enumerate(styles)
    )
    if include_none:
        spans = (*spans, StyleSpan(len(styles), len(styles) + 1, None))
    before = replace(trace.snapshots[0], text=text, style_spans=spans)
    root_occurrence = trace.occurrences[0]
    occurrence = EntityOccurrence(
        root_occurrence.id,
        root_occurrence.snapshot_id,
        root_occurrence.entity_id,
        root_occurrence.role,
        0,
        len(text),
    )
    return replace(
        trace,
        styles=styles,
        snapshots=(before, trace.snapshots[1]),
        occurrences=(occurrence, trace.occurrences[1]),
    )


def _meta(value: object) -> FrozenMap:
    frozen = freeze_json(value)
    assert isinstance(frozen, FrozenMap)
    return frozen


def test_projection_interns_complete_typed_style_tuples_only() -> None:
    hostile = '</style><a href="https://invalid.example/">unsafe</a>'
    candidates = [StyleRecord(""), StyleRecord("")]
    for field in _TRISTATE_FIELDS:
        candidates.append(cast(Any, replace)(StyleRecord(""), **{field: False}))
        candidates.append(cast(Any, replace)(StyleRecord(""), **{field: True}))
    candidates.extend(
        (
            StyleRecord("", link=""),
            StyleRecord("", link=hostile),
            StyleRecord("", meta=_meta({"typed": [False]})),
            StyleRecord("", meta=_meta({"typed": [0]})),
            StyleRecord("", meta=_meta({"a": 1, "b": 2})),
            StyleRecord("", meta=_meta({"b": 2, "a": 1})),
            StyleRecord(
                "",
                color=ColorRecord("standard", "standard-one", 1, None),
            ),
            StyleRecord(
                "",
                bgcolor=ColorRecord("standard", "standard-one", 1, None),
            ),
            StyleRecord(
                "",
                color=ColorRecord("truecolor", "same-visual", None, (244, 0, 95)),
            ),
            StyleRecord(
                "",
                color=ColorRecord(
                    "truecolor",
                    "different-name",
                    None,
                    (244, 0, 95),
                ),
            ),
        )
    )
    styles = tuple(
        replace(style, id=f"style-{index}") for index, style in enumerate(candidates)
    )
    trace = _trace_with_styles(styles, include_none=True)
    before = repr(trace)

    associations = _style_projection(trace)
    classes = {
        cast(str, association["style_id"]): cast(str, association["css_class"])
        for association in associations
    }
    rules = generated_style_rules(trace).splitlines()
    payload = encode_trace(trace)
    canonical = cast(PrimitiveObject, payload["trace"])
    canonical_styles = cast(list[object], canonical["styles"])

    assert classes["style-0"] == classes["style-1"]
    assert len(set(classes.values())) == len(styles) - 1
    assert len(rules) == len(styles) - 1
    assert [rule.split("{", 1)[0][1:] for rule in rules] == [
        f"kr-captured-style-{index}" for index in range(len(styles) - 1)
    ]
    assert hostile not in "\n".join(rules)
    assert [cast(PrimitiveObject, item)["id"] for item in canonical_styles] == [
        style.id for style in styles
    ]
    for field in _TRISTATE_FIELDS:
        encoded_values = [
            cast(PrimitiveObject, item)[field] for item in canonical_styles
        ]
        assert None in encoded_values
        assert False in encoded_values
        assert True in encoded_values
    snapshots = cast(PrimitiveObject, payload["projection"])["snapshots"]
    assert isinstance(snapshots, list)
    first = cast(PrimitiveObject, snapshots[0])
    runs = cast(list[PrimitiveObject], first["render_runs"])
    assert runs[-1]["style_id"] is None
    assert repr(trace) == before


def test_literal_monokai_default_and_standard_palette_projection() -> None:
    default = ColorRecord("default", "ignored-name", None, None)
    assert _style_rule(0, StyleRecord("style-0", color=default)) == (
        ".kr-captured-style-0{color:#D9D9D9;}"
    )
    assert _style_rule(0, StyleRecord("style-0", bgcolor=default)) == (
        ".kr-captured-style-0{background-color:#0C0C0C;}"
    )
    for number, expected in enumerate(_MONOKAI_STANDARD):
        color = ColorRecord("standard", f"literal-{number}", number, None)
        assert _style_rule(0, StyleRecord("style-0", color=color)) == (
            f".kr-captured-style-0{{color:{expected};}}"
        )
        assert _style_rule(0, StyleRecord("style-0", bgcolor=color)) == (
            f".kr-captured-style-0{{background-color:{expected};}}"
        )


def test_literal_full_xterm_256_palette_projection() -> None:
    assert len(_XTERM_256) == 256
    for number, expected in enumerate(_XTERM_256):
        color = ColorRecord("eight_bit", f"literal-{number}", number, None)
        assert _style_rule(0, StyleRecord("style-0", color=color)) == (
            f".kr-captured-style-0{{color:{expected};}}"
        )
        assert _style_rule(0, StyleRecord("style-0", bgcolor=color)) == (
            f".kr-captured-style-0{{background-color:{expected};}}"
        )


def test_literal_windows_16_and_truecolor_projection() -> None:
    for number, expected in enumerate(_WINDOWS_16):
        color = ColorRecord("windows", f"literal-{number}", number, None)
        assert _style_rule(0, StyleRecord("style-0", color=color)) == (
            f".kr-captured-style-0{{color:{expected};}}"
        )
        assert _style_rule(0, StyleRecord("style-0", bgcolor=color)) == (
            f".kr-captured-style-0{{background-color:{expected};}}"
        )
    for triplet in ((0, 0, 0), (1, 2, 3), (17, 34, 51), (255, 255, 255)):
        expected = f"#{triplet[0]:02X}{triplet[1]:02X}{triplet[2]:02X}"
        color = ColorRecord("truecolor", "literal", None, triplet)
        assert _style_rule(0, StyleRecord("style-0", color=color)) == (
            f".kr-captured-style-0{{color:{expected};}}"
        )
        assert _style_rule(0, StyleRecord("style-0", bgcolor=color)) == (
            f".kr-captured-style-0{{background-color:{expected};}}"
        )


def test_reverse_precedes_integer_truncating_dim_and_defaults_missing_sides() -> None:
    foreground = ColorRecord("truecolor", None, None, (100, 120, 140))
    background = ColorRecord("truecolor", None, None, (10, 20, 30))

    assert _style_rule(
        0,
        StyleRecord(
            "style-0",
            color=foreground,
            bgcolor=background,
            reverse=True,
            dim=True,
        ),
    ) == (".kr-captured-style-0{color:#0B1015;background-color:#64788C;}")
    assert _style_rule(
        0,
        StyleRecord("style-0", color=foreground, reverse=True),
    ) == (".kr-captured-style-0{color:#0C0C0C;background-color:#64788C;}")
    assert _style_rule(
        0,
        StyleRecord("style-0", bgcolor=background, reverse=True),
    ) == (".kr-captured-style-0{color:#0A141E;background-color:#D9D9D9;}")
    assert _style_rule(0, StyleRecord("style-0", dim=True)) == (
        ".kr-captured-style-0{color:#727272;}"
    )


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("style", "expected"),
    [
        (
            StyleRecord("style-0", bold=True, italic=True),
            "font-weight:700;font-style:italic;",
        ),
        (
            StyleRecord("style-0", underline=True, strike=True, overline=True),
            (
                "text-decoration-line:underline line-through overline;"
                "text-decoration-style:solid;"
            ),
        ),
        (
            StyleRecord("style-0", underline2=True, strike=True, overline=True),
            (
                "text-decoration-line:underline line-through overline;"
                "text-decoration-style:double;"
            ),
        ),
    ],
)
def test_literal_weight_italic_and_composed_decoration_projection(
    style: StyleRecord, expected: str
) -> None:
    assert _style_rule(0, style) == f".kr-captured-style-0{{{expected}}}"


def test_inert_fields_retain_typed_payload_without_active_css() -> None:
    hostile = 'https://invalid.example/");animation:spin 1s'
    style = StyleRecord(
        "style-0",
        blink=True,
        blink2=False,
        conceal=None,
        frame=True,
        encircle=False,
        link=hostile,
        meta=_meta({"unsafe": hostile, "typed": [True, False, None]}),
    )
    trace = _trace_with_styles((style,))

    assert generated_style_rules(trace) == ".kr-captured-style-0{}"
    canonical = cast(PrimitiveObject, encode_trace(trace)["trace"])
    encoded = cast(PrimitiveObject, cast(list[object], canonical["styles"])[0])
    assert encoded["blink"] is True
    assert encoded["blink2"] is False
    assert encoded["conceal"] is None
    assert encoded["frame"] is True
    assert encoded["encircle"] is False
    assert encoded["link"] == hostile
    assert encoded["meta"] == {
        "kind": "ordered-map",
        "entries": [
            ["unsafe", {"kind": "str", "value": hostile}],
            [
                "typed",
                [
                    {"kind": "bool", "value": True},
                    {"kind": "bool", "value": False},
                    {"kind": "none"},
                ],
            ],
        ],
    }


def test_stylesheet_marker_is_unique_ordered_and_fails_closed() -> None:
    static_css = _ASSETS.joinpath("viewer.css").read_text(encoding="utf-8")
    marker = export_module._GENERATED_STYLE_MARKER
    generated = ".kr-captured-style-0{color:#010203;}"

    composed = export_module._compose_stylesheet(static_css, generated)

    assert static_css.count(marker) == 1
    assert composed.count(marker) == 1
    assert composed.index("/* Reusable viewer components. */") < composed.index(marker)
    assert composed.index(marker) < composed.index(generated)
    assert composed.index(generated) < composed.index(
        "/* Final semantic state and keyboard-focus rules. */"
    )
    with pytest.raises(RuntimeError, match="exactly one"):
        export_module._compose_stylesheet(static_css.replace(marker, ""), generated)
    with pytest.raises(RuntimeError, match="exactly one"):
        export_module._compose_stylesheet(
            static_css.replace(marker, f"{marker}\n{marker}"),
            generated,
        )


def test_static_cascade_and_script_have_one_geometry_path_and_style_exception() -> None:
    css = _ASSETS.joinpath("viewer.css").read_text(encoding="utf-8")
    javascript = _ASSETS.joinpath("viewer.js").read_text(encoding="utf-8")

    assert css.count(":root {") == 1
    assert "@media" not in css
    assert "@container" not in css
    assert "!important" not in css
    assert "flex-flow: row nowrap" in css
    assert "inline-size: max-content" in css
    assert "white-space: pre" in css
    assert re.findall(
        r'\.style\.setProperty\(\s*"([^"]+)"',
        javascript,
    ) == [
        "--overlay-inline-start",
        "--overlay-block-start",
        "--overlay-inline-start",
        "--overlay-block-start",
    ]
    without_allowed = re.sub(
        r'overlay\.style\.setProperty\(\s*"--overlay-(?:inline|block)-start"'
        r",[\s\S]*?\);",
        "",
        javascript,
    )
    assert ".style." not in without_allowed
    assert ".style =" not in javascript
