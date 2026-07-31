"""Explicit, one-way encoding of immutable traces for the HTML viewer."""

from __future__ import annotations

import math
from itertools import pairwise
from typing import TypeAlias, cast

from rich.color import Color, ColorType
from rich.color_triplet import ColorTriplet
from rich.terminal_theme import MONOKAI

from ._model import (
    CaptureConfiguration,
    ColorRecord,
    EntityEffect,
    EntityOccurrence,
    FrameLocation,
    FrozenList,
    FrozenMap,
    FrozenValue,
    InvocationStack,
    MetadataRecord,
    MutationOperation,
    ProvenanceRelation,
    RenderedValue,
    RewriteEvent,
    RewriteResultRecord,
    Snapshot,
    StyleRecord,
    StyleSpan,
    Trace,
    TraceEntity,
    _snapshot_semantic_key,
)

Primitive: TypeAlias = (
    bool | int | float | str | list["Primitive"] | dict[str, "Primitive"] | None
)
PrimitiveObject: TypeAlias = dict[str, Primitive]

_SAFE_INTEGER_MAX = 9_007_199_254_740_991
_STYLE_CLASS_PREFIX = "kr-captured-style-"


class TraceEncodingError(ValueError):
    """The immutable trace contains a value outside the document data domain."""


def encode_trace(trace: Trace) -> PrimitiveObject:
    """Copy a validated trace into explicit inert JSON primitives."""

    if type(trace) is not Trace:
        raise TypeError("trace must be an immutable Trace")

    encoded: PrimitiveObject = {
        "export_schema_version": 1,
        "trace": {
            "schema_version": trace.schema_version,
            "complete": trace.complete,
            "configurations": [
                _encode_configuration(item) for item in trace.configurations
            ],
            "styles": [_encode_style(item) for item in trace.styles],
            "entities": [_encode_entity(item) for item in trace.entities],
            "snapshots": [_encode_snapshot(item) for item in trace.snapshots],
            "occurrences": [_encode_occurrence(item) for item in trace.occurrences],
            "metadata": [_encode_metadata(item) for item in trace.metadata],
            "stacks": [_encode_stack(item) for item in trace.stacks],
            "events": [_encode_event(item) for item in trace.events],
            "operations": [_encode_operation(item) for item in trace.operations],
            "relations": [_encode_relation(item) for item in trace.relations],
            "effects": [_encode_effect(item) for item in trace.effects],
        },
        "projection": _encode_projection(trace),
    }
    _validate_primitive(encoded)
    return encoded


def generated_style_rules(trace: Trace) -> str:
    """Generate fixed-selector CSS from validated normalized Rich fields."""

    if type(trace) is not Trace:
        raise TypeError("trace must be an immutable Trace")
    return "\n".join(
        _style_rule(index, style) for index, style in enumerate(trace.styles)
    )


def _encode_configuration(item: CaptureConfiguration) -> PrimitiveObject:
    return {
        "id": item.id,
        "kirin_commit": item.kirin_commit,
        "rich_version": item.rich_version,
        "theme": item.theme,
        "show_indent_mark": item.show_indent_mark,
        "hint": item.hint,
        "printer_analysis": item.printer_analysis,
        "highlighter": item.highlighter,
    }


def _encode_color(item: ColorRecord | None) -> Primitive:
    if item is None:
        return None
    triplet: Primitive
    if item.triplet is None:
        triplet = None
    else:
        triplet = [item.triplet[0], item.triplet[1], item.triplet[2]]
    return {
        "encoding": item.encoding,
        "name": item.name,
        "number": item.number,
        "triplet": triplet,
    }


def _encode_style(item: StyleRecord) -> PrimitiveObject:
    return {
        "id": item.id,
        "color": _encode_color(item.color),
        "bgcolor": _encode_color(item.bgcolor),
        "bold": item.bold,
        "dim": item.dim,
        "italic": item.italic,
        "underline": item.underline,
        "blink": item.blink,
        "blink2": item.blink2,
        "reverse": item.reverse,
        "conceal": item.conceal,
        "strike": item.strike,
        "underline2": item.underline2,
        "frame": item.frame,
        "encircle": item.encircle,
        "overline": item.overline,
        "link": item.link,
        "meta": _encode_frozen(item.meta),
    }


def _encode_entity(item: TraceEntity) -> PrimitiveObject:
    return {
        "id": item.id,
        "kind": item.kind,
        "qualified_type": item.qualified_type,
        "defining_owner_id": item.defining_owner_id,
    }


def _encode_style_span(item: StyleSpan) -> PrimitiveObject:
    return {"start": item.start, "end": item.end, "style_id": item.style_id}


def _encode_snapshot(item: Snapshot) -> PrimitiveObject:
    return {
        "id": item.id,
        "event_id": item.event_id,
        "state": item.state,
        "schema_version": item.schema_version,
        "configuration_id": item.configuration_id,
        "root_entity_id": item.root_entity_id,
        "text": item.text,
        "style_spans": [_encode_style_span(span) for span in item.style_spans],
        "entity_ids": list(item.entity_ids),
        "occurrence_ids": list(item.occurrence_ids),
        "metadata_ids": list(item.metadata_ids),
        "analysis_supplied": item.analysis_supplied,
    }


def _encode_occurrence(item: EntityOccurrence) -> PrimitiveObject:
    return {
        "id": item.id,
        "snapshot_id": item.snapshot_id,
        "entity_id": item.entity_id,
        "role": item.role,
        "start": item.start,
        "end": item.end,
    }


def _encode_rendered_value(item: RenderedValue | None) -> Primitive:
    if item is None:
        return None
    return {
        "qualified_type": item.qualified_type,
        "text": item.text,
        "path": item.path,
    }


def _encode_metadata(item: MetadataRecord) -> PrimitiveObject:
    return {
        "id": item.id,
        "snapshot_id": item.snapshot_id,
        "owner_entity_id": item.owner_entity_id,
        "namespace": item.namespace,
        "key": item.key,
        "presence": item.presence,
        "value": _encode_rendered_value(item.value),
    }


def _encode_frame(item: FrameLocation) -> PrimitiveObject:
    return {
        "filename": item.filename,
        "line": item.line,
        "function": item.function,
    }


def _encode_stack(item: InvocationStack) -> PrimitiveObject:
    return {"id": item.id, "frames": [_encode_frame(frame) for frame in item.frames]}


def _encode_result(item: RewriteResultRecord | None) -> Primitive:
    if item is None:
        return None
    return {
        "terminated": item.terminated,
        "has_done_something": item.has_done_something,
        "exceeded_max_iter": item.exceeded_max_iter,
    }


def _encode_event(item: RewriteEvent) -> PrimitiveObject:
    return {
        "id": item.id,
        "sequence": item.sequence,
        "parent_id": item.parent_id,
        "sibling_ordinal": item.sibling_ordinal,
        "rule_type": item.rule_type,
        "completion": item.completion,
        "root_entity_id": item.root_entity_id,
        "before_snapshot_id": item.before_snapshot_id,
        "after_snapshot_id": item.after_snapshot_id,
        "invocation_stack_id": item.invocation_stack_id,
        "result": _encode_result(item.result),
    }


def _encode_operation(item: MutationOperation) -> PrimitiveObject:
    return {
        "id": item.id,
        "sequence": item.sequence,
        "owner_event_id": item.owner_event_id,
        "parent_operation_id": item.parent_operation_id,
        "api": item.api,
        "outcome": item.outcome,
        "source_entity_ids": list(item.source_entity_ids),
        "destination_entity_ids": list(item.destination_entity_ids),
        "invocation_stack_id": item.invocation_stack_id,
    }


def _encode_relation(item: ProvenanceRelation) -> PrimitiveObject:
    return {
        "id": item.id,
        "basis": item.basis,
        "source_entity_id": item.source_entity_id,
        "destination_entity_id": item.destination_entity_id,
        "mutation_operation_id": item.mutation_operation_id,
    }


def _encode_effect(item: EntityEffect) -> PrimitiveObject:
    return {
        "id": item.id,
        "kind": item.kind,
        "affected_entity_id": item.affected_entity_id,
        "mutation_operation_id": item.mutation_operation_id,
    }


def _encode_projection(trace: Trace) -> PrimitiveObject:
    index = trace.index()
    semantic_classes: dict[object, str] = {}
    style_classes: list[Primitive] = [
        {
            "style_id": style.id,
            "css_class": f"{_STYLE_CLASS_PREFIX}{style_index}",
        }
        for style_index, style in enumerate(trace.styles)
    ]
    snapshots: list[Primitive] = []
    occurrence_text: list[Primitive] = []
    for snapshot in trace.snapshots:
        semantic_key = _snapshot_semantic_key(trace, index, snapshot)
        semantic_class = semantic_classes.get(semantic_key)
        if semantic_class is None:
            semantic_class = f"snapshot-semantic-{len(semantic_classes)}"
            semantic_classes[semantic_key] = semantic_class
        occurrences = tuple(
            index.occurrence(item_id) for item_id in snapshot.occurrence_ids
        )
        snapshots.append(
            {
                "snapshot_id": snapshot.id,
                "semantic_class": semantic_class,
                "render_runs": _render_runs(snapshot, occurrences),
            }
        )
        occurrence_text.extend(
            {
                "occurrence_id": occurrence.id,
                "text": snapshot.text[occurrence.start : occurrence.end],
            }
            for occurrence in occurrences
        )
    return {
        "styles": style_classes,
        "snapshots": snapshots,
        "occurrences": occurrence_text,
    }


def _render_runs(
    snapshot: Snapshot, occurrences: tuple[EntityOccurrence, ...]
) -> list[Primitive]:
    if not snapshot.text:
        return []

    boundaries = {0, len(snapshot.text)}
    for span in snapshot.style_spans:
        boundaries.add(span.start)
        boundaries.add(span.end)
    for occurrence in occurrences:
        boundaries.add(occurrence.start)
        boundaries.add(occurrence.end)

    ordered = sorted(boundaries)
    runs: list[Primitive] = []
    span_index = 0
    for start, end in pairwise(ordered):
        if start == end:
            continue
        while snapshot.style_spans[span_index].end <= start:
            span_index += 1
        span = snapshot.style_spans[span_index]
        active_occurrences: list[Primitive] = [
            occurrence.id
            for occurrence in occurrences
            if occurrence.start <= start and end <= occurrence.end
        ]
        runs.append(
            {
                "start": start,
                "end": end,
                "text": snapshot.text[start:end],
                "style_id": span.style_id,
                "occurrence_ids": active_occurrences,
            }
        )
    return runs


def _encode_frozen(item: FrozenValue) -> Primitive:
    if item is None:
        return {"kind": "none"}
    if type(item) is bool:
        return {"kind": "bool", "value": item}
    if type(item) is int:
        return {"kind": "int", "value": item}
    if type(item) is float:
        return {"kind": "float", "hex": item.hex()}
    if type(item) is str:
        return {"kind": "str", "value": item}
    if type(item) is FrozenList:
        return [_encode_frozen(value) for value in item.items]
    if type(item) is FrozenMap:
        entries: list[Primitive] = [
            [key, _encode_frozen(value)] for key, value in item.entries
        ]
        return {"kind": "ordered-map", "entries": entries}
    raise TraceEncodingError("unsupported frozen value")


def _validate_primitive(item: object, active: set[int] | None = None) -> None:
    if item is None or type(item) in {bool, str}:
        return
    if type(item) is int:
        if not -_SAFE_INTEGER_MAX <= item <= _SAFE_INTEGER_MAX:
            raise TraceEncodingError("integer is outside the JavaScript-safe range")
        return
    if type(item) is float:
        if not math.isfinite(item):
            raise TraceEncodingError("non-finite float is unsupported")
        return

    containers = set() if active is None else active
    marker = id(item)
    if marker in containers:
        raise TraceEncodingError("cyclic primitive container is unsupported")
    containers.add(marker)
    try:
        if type(item) is list:
            for value in cast(list[object], item):
                _validate_primitive(value, containers)
            return
        if type(item) is dict:
            for key, value in cast(dict[object, object], item).items():
                if type(key) is not str:
                    raise TraceEncodingError("primitive map keys must be strings")
                _validate_primitive(value, containers)
            return
    finally:
        containers.remove(marker)
    raise TraceEncodingError("unsupported document primitive")


def _style_rule(index: int, style: StyleRecord) -> str:
    foreground = (
        _resolve_color(style.color, foreground=True)
        if style.color is not None
        else None
    )
    background = (
        _resolve_color(style.bgcolor, foreground=False)
        if style.bgcolor is not None
        else None
    )

    if style.reverse is True:
        if foreground is None:
            foreground = _theme_rgb(foreground=True)
        if background is None:
            background = _theme_rgb(foreground=False)
        foreground, background = background, foreground

    if style.dim is True:
        if foreground is None:
            foreground = _theme_rgb(foreground=True)
        theme_background = _theme_rgb(foreground=False)
        foreground = (
            int(foreground[0] + (theme_background[0] - foreground[0]) * 0.5),
            int(foreground[1] + (theme_background[1] - foreground[1]) * 0.5),
            int(foreground[2] + (theme_background[2] - foreground[2]) * 0.5),
        )

    declarations: list[str] = []
    if foreground is not None:
        declarations.append(f"color:{_hex(foreground)}")
    if background is not None:
        declarations.append(f"background-color:{_hex(background)}")
    if style.bold is True:
        declarations.append("font-weight:700")
    if style.italic is True:
        declarations.append("font-style:italic")

    lines: list[str] = []
    if style.underline is True or style.underline2 is True:
        lines.append("underline")
    if style.strike is True:
        lines.append("line-through")
    if style.overline is True:
        lines.append("overline")
    if lines:
        declarations.append(f"text-decoration-line:{' '.join(lines)}")
        declarations.append(
            "text-decoration-style:double"
            if style.underline2 is True
            else "text-decoration-style:solid"
        )

    body = ";".join(declarations)
    if body:
        body += ";"
    return f".{_STYLE_CLASS_PREFIX}{index}{{{body}}}"


def _resolve_color(item: ColorRecord, *, foreground: bool) -> tuple[int, int, int]:
    if item.encoding == "default":
        if item.number is not None or item.triplet is not None:
            raise TraceEncodingError("default colors cannot carry a number or triplet")
        color = Color("default", ColorType.DEFAULT)
    elif item.encoding in {"standard", "windows"}:
        if (
            item.number is None
            or not 0 <= item.number <= 15
            or item.triplet is not None
        ):
            raise TraceEncodingError(
                f"{item.encoding} colors require a number in [0, 15]"
            )
        color_type = (
            ColorType.STANDARD if item.encoding == "standard" else ColorType.WINDOWS
        )
        color = Color(item.encoding, color_type, number=item.number)
    elif item.encoding == "eight_bit":
        if (
            item.number is None
            or not 0 <= item.number <= 255
            or item.triplet is not None
        ):
            raise TraceEncodingError("eight-bit colors require a number in [0, 255]")
        color = Color("eight_bit", ColorType.EIGHT_BIT, number=item.number)
    elif item.encoding == "truecolor":
        if item.triplet is None or item.number is not None:
            raise TraceEncodingError("truecolor requires exactly one RGB triplet")
        color = Color(
            "truecolor",
            ColorType.TRUECOLOR,
            triplet=ColorTriplet(*item.triplet),
        )
    else:
        raise TraceEncodingError(f"unsupported color encoding: {item.encoding!r}")

    resolved = color.get_truecolor(MONOKAI, foreground=foreground)
    return resolved.red, resolved.green, resolved.blue


def _theme_rgb(*, foreground: bool) -> tuple[int, int, int]:
    color = MONOKAI.foreground_color if foreground else MONOKAI.background_color
    return color.red, color.green, color.blue


def _hex(rgb: tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
