from __future__ import annotations

from dataclasses import replace
from typing import cast

import pytest
from viewer_fixtures import (
    EventSpec,
    event_trace,
    facts_trace,
    handoff_trace,
    selection_trace,
)

from kirin_rewrite_tracer import Trace
from kirin_rewrite_tracer._encoding import PrimitiveObject, encode_trace
from kirin_rewrite_tracer._model import (
    CaptureConfiguration,
    EntityOccurrence,
    FrameLocation,
    FrozenMap,
    InvocationStack,
    MetadataRecord,
    MutationOperation,
    RenderedValue,
    StyleRecord,
    StyleSpan,
    TraceEntity,
    freeze_json,
)


def _semantic_classes(trace: Trace) -> dict[str, str]:
    payload = encode_trace(trace)
    projection = payload["projection"]
    assert isinstance(projection, dict)
    snapshots = projection["snapshots"]
    assert isinstance(snapshots, list)
    classes: dict[str, str] = {}
    for value in snapshots:
        item = cast(PrimitiveObject, value)
        snapshot_id = item["snapshot_id"]
        semantic_class = item["semantic_class"]
        assert isinstance(snapshot_id, str)
        assert isinstance(semantic_class, str)
        classes[snapshot_id] = semantic_class
    return classes


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "trace",
    [selection_trace(), handoff_trace(), facts_trace()],
)
def test_projected_semantic_classes_are_pairwise_equivalent_to_model_equality(
    trace: Trace,
) -> None:
    before = repr(trace)
    classes = _semantic_classes(trace)

    for left in trace.snapshots:
        for right in trace.snapshots:
            assert (
                classes[left.id] == classes[right.id]
            ) is trace.snapshots_semantically_equal(left.id, right.id)

    first_seen: dict[str, int] = {}
    for snapshot in trace.snapshots:
        first_seen.setdefault(classes[snapshot.id], len(first_seen))
    assert first_seen == {
        f"snapshot-semantic-{index}": index for index in range(len(first_seen))
    }
    assert repr(trace) == before


def _equal_boundary_trace() -> Trace:
    return event_trace(
        (
            EventSpec("Left", None, "left", "same"),
            EventSpec("Right", None, "same", "right"),
        )
    )


def _root_near_miss() -> Trace:
    trace = _equal_boundary_trace()
    second_root = TraceEntity("entity-1", "statement", "fixture.SecondRoot")
    left_after = replace(
        trace.snapshots[1],
        entity_ids=("entity-0", "entity-1"),
    )
    right_before = replace(
        trace.snapshots[2],
        root_entity_id="entity-1",
        entity_ids=("entity-0", "entity-1"),
    )
    right_after = replace(
        trace.snapshots[3],
        root_entity_id="entity-1",
        entity_ids=("entity-0", "entity-1"),
    )
    right_event = replace(trace.events[1], root_entity_id="entity-1")
    return replace(
        trace,
        entities=(trace.entities[0], second_root),
        snapshots=(
            trace.snapshots[0],
            left_after,
            right_before,
            right_after,
        ),
        events=(trace.events[0], right_event),
    )


def _entity_inventory_near_miss() -> Trace:
    trace = _equal_boundary_trace()
    extra = TraceEntity("entity-1", "statement", "fixture.Extra")
    right_before = replace(
        trace.snapshots[2],
        entity_ids=("entity-0", "entity-1"),
    )
    return replace(
        trace,
        entities=(trace.entities[0], extra),
        snapshots=(*trace.snapshots[:2], right_before, trace.snapshots[3]),
    )


def _text_near_miss() -> Trace:
    trace = _equal_boundary_trace()
    right_before = replace(trace.snapshots[2], text="sAme")
    return replace(
        trace,
        snapshots=(*trace.snapshots[:2], right_before, trace.snapshots[3]),
    )


def _occurrence_near_miss(
    *,
    left_role: str = "definition",
    right_role: str = "definition",
    left_interval: tuple[int, int] = (0, 1),
    right_intervals: tuple[tuple[int, int], ...] = ((0, 1),),
) -> Trace:
    trace = _equal_boundary_trace()
    value = TraceEntity("entity-1", "ssa", "fixture.Value", "entity-0")
    appended = [
        EntityOccurrence(
            "occurrence-4",
            "snapshot-1",
            "entity-1",
            left_role,
            *left_interval,
        )
    ]
    right_ids: list[str] = []
    for index, interval in enumerate(right_intervals, start=5):
        occurrence_id = f"occurrence-{index}"
        right_ids.append(occurrence_id)
        appended.append(
            EntityOccurrence(
                occurrence_id,
                "snapshot-2",
                "entity-1",
                right_role,
                *interval,
            )
        )
    left_after = replace(
        trace.snapshots[1],
        entity_ids=("entity-0", "entity-1"),
        occurrence_ids=("occurrence-1", "occurrence-4"),
    )
    right_before = replace(
        trace.snapshots[2],
        entity_ids=("entity-0", "entity-1"),
        occurrence_ids=("occurrence-2", *right_ids),
    )
    return replace(
        trace,
        entities=(trace.entities[0], value),
        snapshots=(
            trace.snapshots[0],
            left_after,
            right_before,
            trace.snapshots[3],
        ),
        occurrences=(*trace.occurrences, *appended),
    )


def _metadata_near_miss(
    left_presence: str,
    left_value: RenderedValue | None,
    right_presence: str,
    right_value: RenderedValue | None,
) -> Trace:
    trace = _equal_boundary_trace()
    records = (
        MetadataRecord(
            "metadata-0",
            "snapshot-1",
            "entity-0",
            "fixture",
            "key",
            left_presence,
            left_value,
        ),
        MetadataRecord(
            "metadata-1",
            "snapshot-2",
            "entity-0",
            "fixture",
            "key",
            right_presence,
            right_value,
        ),
    )
    left_after = replace(trace.snapshots[1], metadata_ids=("metadata-0",))
    right_before = replace(trace.snapshots[2], metadata_ids=("metadata-1",))
    return replace(
        trace,
        snapshots=(
            trace.snapshots[0],
            left_after,
            right_before,
            trace.snapshots[3],
        ),
        metadata=records,
    )


def _analysis_near_miss() -> Trace:
    trace = _equal_boundary_trace()
    right_before = replace(trace.snapshots[2], analysis_supplied=True)
    return replace(
        trace,
        snapshots=(*trace.snapshots[:2], right_before, trace.snapshots[3]),
    )


_PRINTED = RenderedValue("builtins.str", "value", "printable")
_REPR = RenderedValue("builtins.str", "value", "repr")
_OTHER_VALUE = RenderedValue("builtins.str", "other", "printable")


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("difference", "trace"),
    [
        ("root", _root_near_miss()),
        ("entity inventory", _entity_inventory_near_miss()),
        ("text", _text_near_miss()),
        (
            "occurrence role",
            _occurrence_near_miss(right_role="reference"),
        ),
        (
            "occurrence interval",
            _occurrence_near_miss(right_intervals=((1, 2),)),
        ),
        (
            "occurrence multiplicity",
            _occurrence_near_miss(right_intervals=((0, 1), (1, 2))),
        ),
        (
            "metadata presence",
            _metadata_near_miss("absent", None, "present", _PRINTED),
        ),
        (
            "metadata value",
            _metadata_near_miss(
                "present",
                _PRINTED,
                "present",
                _OTHER_VALUE,
            ),
        ),
        (
            "metadata render path",
            _metadata_near_miss("present", _PRINTED, "present", _REPR),
        ),
        ("analysis supplied", _analysis_near_miss()),
    ],
)
def test_semantic_classes_reject_each_isolated_payload_near_miss(
    difference: str,
    trace: Trace,
) -> None:
    classes = _semantic_classes(trace)

    assert classes["snapshot-1"] != classes["snapshot-2"], difference


def test_semantic_classes_normalize_style_layout_and_configuration_ids() -> None:
    trace = _equal_boundary_trace()
    duplicate_style = replace(trace.styles[0], id="style-1")
    duplicate_configuration = replace(trace.configurations[0], id="configuration-1")
    right_before = replace(
        trace.snapshots[2],
        configuration_id="configuration-1",
        style_spans=(
            StyleSpan(0, 2, "style-1"),
            StyleSpan(2, len(trace.snapshots[2].text), "style-1"),
        ),
    )
    normalized = replace(
        trace,
        configurations=(trace.configurations[0], duplicate_configuration),
        styles=(trace.styles[0], duplicate_style),
        snapshots=(*trace.snapshots[:2], right_before, trace.snapshots[3]),
    )

    classes = _semantic_classes(normalized)

    assert classes["snapshot-1"] == classes["snapshot-2"]


def test_semantic_classes_reject_typed_style_near_miss_alone() -> None:
    trace = _equal_boundary_trace()
    false_meta = cast(FrozenMap, freeze_json({"typed": [False]}))
    zero_meta = cast(FrozenMap, freeze_json({"typed": [0]}))
    left_style = replace(trace.styles[0], meta=false_meta)
    right_style = StyleRecord("style-1", meta=zero_meta)
    equal_configuration = replace(trace.configurations[0], id="configuration-1")
    right_before = replace(
        trace.snapshots[2],
        configuration_id="configuration-1",
        style_spans=(StyleSpan(0, len(trace.snapshots[2].text), "style-1"),),
    )
    near_miss = replace(
        trace,
        configurations=(trace.configurations[0], equal_configuration),
        styles=(left_style, right_style),
        snapshots=(*trace.snapshots[:2], right_before, trace.snapshots[3]),
    )

    classes = _semantic_classes(near_miss)

    assert classes["snapshot-1"] != classes["snapshot-2"]
    assert not near_miss.snapshots_semantically_equal("snapshot-1", "snapshot-2")


def test_semantic_classes_reject_configuration_value_near_miss_alone() -> None:
    trace = _equal_boundary_trace()
    duplicate_style = replace(trace.styles[0], id="style-1")
    changed_configuration = CaptureConfiguration(
        "configuration-1",
        trace.configurations[0].kirin_commit,
        trace.configurations[0].rich_version,
        "different-theme",
        trace.configurations[0].show_indent_mark,
        trace.configurations[0].hint,
        trace.configurations[0].printer_analysis,
        trace.configurations[0].highlighter,
    )
    right_before = replace(
        trace.snapshots[2],
        configuration_id="configuration-1",
        style_spans=(
            StyleSpan(0, 2, "style-1"),
            StyleSpan(2, len(trace.snapshots[2].text), "style-1"),
        ),
    )
    near_miss = replace(
        trace,
        configurations=(trace.configurations[0], changed_configuration),
        styles=(trace.styles[0], duplicate_style),
        snapshots=(*trace.snapshots[:2], right_before, trace.snapshots[3]),
    )

    classes = _semantic_classes(near_miss)

    assert classes["snapshot-1"] != classes["snapshot-2"]
    assert not near_miss.snapshots_semantically_equal("snapshot-1", "snapshot-2")


def test_event_stacks_and_operations_do_not_change_snapshot_semantic_class() -> None:
    trace = _equal_boundary_trace()
    second_stack = InvocationStack(
        "stack-1", (FrameLocation("other.py", 91, "different_entry"),)
    )
    right_event = replace(trace.events[1], invocation_stack_id="stack-1")
    operation = MutationOperation(
        "operation-0",
        0,
        "event-0",
        None,
        "Statement.from_stmt",
        "incomplete",
        ("entity-0",),
        (),
        "stack-1",
    )
    event_level_difference = replace(
        trace,
        stacks=(trace.stacks[0], second_stack),
        events=(trace.events[0], right_event),
        operations=(operation,),
    )

    classes = _semantic_classes(event_level_difference)

    assert classes["snapshot-1"] == classes["snapshot-2"]
