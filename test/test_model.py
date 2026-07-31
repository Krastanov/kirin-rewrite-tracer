from __future__ import annotations

import gc
import weakref
from dataclasses import FrozenInstanceError, replace
from typing import Any, cast

import pytest

from kirin_rewrite_tracer import Trace
from kirin_rewrite_tracer._builder import (
    _EntityRegistry,
    _IdAllocator,
    _TraceBuilder,
)
from kirin_rewrite_tracer._model import (
    CaptureConfiguration,
    ColorRecord,
    EntityEffect,
    EntityOccurrence,
    FrameLocation,
    FrozenList,
    FrozenMap,
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
    TraceEntity,
    TraceValidationError,
    freeze_json,
)


def _configuration() -> CaptureConfiguration:
    return CaptureConfiguration(
        id="configuration-0",
        kirin_commit="7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a",
        rich_version="15.0.0",
        theme="dark",
        show_indent_mark=True,
        hint=None,
        printer_analysis=False,
        highlighter="rich.default",
    )


def _valid_trace() -> Trace:
    configuration = _configuration()
    style = StyleRecord(
        id="style-0",
        color=ColorRecord("truecolor", None, None, (17, 34, 51)),
        bold=False,
        meta=cast(FrozenMap, freeze_json({"ordered": [False, 0, ""]})),
    )
    entities = (
        TraceEntity("entity-0", "statement", "fixture.Root"),
        TraceEntity("entity-1", "ssa", "fixture.Value", "entity-0"),
    )
    occurrences = (
        EntityOccurrence("occurrence-0", "snapshot-0", "entity-0", "container", 0, 3),
        EntityOccurrence("occurrence-1", "snapshot-0", "entity-1", "definition", 0, 2),
        EntityOccurrence("occurrence-2", "snapshot-1", "entity-0", "container", 0, 3),
        EntityOccurrence("occurrence-3", "snapshot-1", "entity-1", "definition", 0, 2),
    )
    metadata = (
        MetadataRecord(
            "metadata-0",
            "snapshot-0",
            "entity-1",
            "ssa",
            "name",
            "absent",
            None,
        ),
        MetadataRecord(
            "metadata-1",
            "snapshot-0",
            "entity-1",
            "analysis",
            "falsey",
            "present",
            RenderedValue("builtins.bool", "False", "repr"),
        ),
        MetadataRecord(
            "metadata-2",
            "snapshot-1",
            "entity-1",
            "ssa",
            "name",
            "absent",
            None,
        ),
        MetadataRecord(
            "metadata-3",
            "snapshot-1",
            "entity-1",
            "analysis",
            "falsey",
            "present",
            RenderedValue("builtins.bool", "False", "repr"),
        ),
    )
    snapshots = (
        Snapshot(
            id="snapshot-0",
            event_id="event-0",
            state="before",
            schema_version=1,
            configuration_id="configuration-0",
            root_entity_id="entity-0",
            text="%0\n",
            style_spans=(StyleSpan(0, 3, "style-0"),),
            entity_ids=("entity-0", "entity-1"),
            occurrence_ids=("occurrence-0", "occurrence-1"),
            metadata_ids=("metadata-0", "metadata-1"),
            analysis_supplied=True,
        ),
        Snapshot(
            id="snapshot-1",
            event_id="event-0",
            state="after",
            schema_version=1,
            configuration_id="configuration-0",
            root_entity_id="entity-0",
            text="%0\n",
            style_spans=(StyleSpan(0, 3, "style-0"),),
            entity_ids=("entity-0", "entity-1"),
            occurrence_ids=("occurrence-2", "occurrence-3"),
            metadata_ids=("metadata-2", "metadata-3"),
            analysis_supplied=True,
        ),
    )
    stack = InvocationStack("stack-0", (FrameLocation("fixture.py", 41, "rewrite"),))
    event = RewriteEvent(
        id="event-0",
        sequence=0,
        parent_id=None,
        sibling_ordinal=0,
        rule_type="fixture.Rule",
        completion="complete",
        root_entity_id="entity-0",
        before_snapshot_id="snapshot-0",
        after_snapshot_id="snapshot-1",
        invocation_stack_id="stack-0",
        result=RewriteResultRecord(False, True, False),
    )
    return Trace(
        schema_version=1,
        complete=True,
        configurations=(configuration,),
        styles=(style,),
        entities=entities,
        snapshots=snapshots,
        occurrences=occurrences,
        metadata=metadata,
        stacks=(stack,),
        events=(event,),
    )


def test_empty_trace_is_valid_and_deeply_immutable() -> None:
    trace = Trace(schema_version=1, complete=True)

    assert trace.index() is not trace.index()
    with pytest.raises(FrozenInstanceError):
        trace.complete = False  # type: ignore[misc]


def test_valid_trace_is_deeply_immutable() -> None:
    trace = _valid_trace()

    with pytest.raises(FrozenInstanceError):
        trace.events[0].rule_type = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        trace.styles[0].meta.entries = ()  # type: ignore[misc]


def test_public_trace_rejects_mutable_or_forged_nested_values() -> None:
    with pytest.raises(TraceValidationError, match="must be a tuple"):
        Trace(
            schema_version=1,
            complete=True,
            events=cast(Any, []),
        )

    trace = _valid_trace()
    bad_style = replace(
        trace.styles[0],
        meta=FrozenMap((("bad", cast(Any, [])),)),
    )
    with pytest.raises(TraceValidationError, match="unsupported frozen value"):
        replace(trace, styles=(bad_style,))


def test_freeze_json_rejects_unsupported_values() -> None:
    values: list[object] = [
        (1, 2),
        {1: "bad"},
        9_007_199_254_740_992,
        float("inf"),
        float("nan"),
        object(),
    ]
    for value in values:
        with pytest.raises(TraceValidationError):
            freeze_json(value)


def test_freeze_json_preserves_order_and_falsey_types() -> None:
    frozen = freeze_json(
        {"none": None, "false": False, "zero": 0, "empty": "", "list": []}
    )

    assert isinstance(frozen, FrozenMap)
    assert frozen == FrozenMap(
        (
            ("none", None),
            ("false", False),
            ("zero", 0),
            ("empty", ""),
            ("list", FrozenList(())),
        )
    )
    assert type(frozen.entries[1][1]) is bool
    assert type(frozen.entries[2][1]) is int


def test_frozen_metadata_equality_preserves_nested_scalar_types() -> None:
    false_value = freeze_json({"nested": [False]})
    zero_value = freeze_json({"nested": [0]})
    integer_value = freeze_json({"nested": [1]})
    float_value = freeze_json({"nested": [1.0]})

    assert false_value != zero_value
    assert integer_value != float_value

    builder = _TraceBuilder()
    assert builder.intern_style(
        StyleRecord(id="", meta=cast(FrozenMap, false_value))
    ) != builder.intern_style(StyleRecord(id="", meta=cast(FrozenMap, zero_value)))


def test_freeze_json_rejects_cycles_but_allows_shared_acyclic_values() -> None:
    cyclic: list[object] = []
    cyclic.append(cyclic)
    with pytest.raises(TraceValidationError, match="cyclic"):
        freeze_json(cyclic)

    shared = [1]
    assert freeze_json([shared, shared]) == FrozenList(
        (FrozenList((1,)), FrozenList((1,)))
    )


def test_ids_are_monotonic_and_registry_uses_object_identity() -> None:
    allocator = _IdAllocator()
    assert allocator.allocate("event") == "event-0"
    assert allocator.allocate("entity") == "entity-0"
    assert allocator.allocate("event") == "event-1"

    class EqualSentinel:
        def __eq__(self, other: object) -> bool:
            return isinstance(other, EqualSentinel)

    registry = _EntityRegistry()
    first = EqualSentinel()
    second = EqualSentinel()
    first_id, first_created = registry.register(first)
    repeated_id, repeated_created = registry.register(first)
    second_id, second_created = registry.register(second)

    assert (first_id, first_created) == ("entity-0", True)
    assert (repeated_id, repeated_created) == ("entity-0", False)
    assert (second_id, second_created) == ("entity-1", True)
    assert "id(" not in repr((first_id, second_id))


def test_registry_holds_objects_only_until_release() -> None:
    class Sentinel:
        pass

    registry = _EntityRegistry()
    sentinel = Sentinel()
    reference = weakref.ref(sentinel)
    registry.register(sentinel)
    del sentinel
    gc.collect()
    assert reference() is not None

    registry.release()
    gc.collect()
    assert reference() is None


def test_trace_rejects_broken_owners_and_illegal_event_states() -> None:
    trace = _valid_trace()
    bad_entity = replace(trace.entities[1], defining_owner_id="entity-99")
    with pytest.raises(TraceValidationError, match="SSA defining owner"):
        replace(trace, entities=(trace.entities[0], bad_entity))

    incomplete = replace(
        trace.events[0],
        completion="incomplete",
        result=None,
    )
    with pytest.raises(TraceValidationError, match="incomplete events"):
        replace(trace, complete=False, events=(incomplete,))


def test_external_ssa_owner_need_not_be_in_snapshot_inventory() -> None:
    trace = _valid_trace()
    external_owner = TraceEntity("entity-2", "statement", "fixture.External")
    external_ssa = TraceEntity("entity-3", "ssa", "fixture.ExternalValue", "entity-2")
    occurrence = EntityOccurrence(
        "occurrence-4", "snapshot-0", "entity-3", "reference", 2, 3
    )
    before = replace(
        trace.snapshots[0],
        entity_ids=("entity-0", "entity-1", "entity-3"),
        occurrence_ids=("occurrence-0", "occurrence-1", "occurrence-4"),
    )
    changed = replace(
        trace,
        entities=(*trace.entities, external_owner, external_ssa),
        snapshots=(before, trace.snapshots[1]),
        occurrences=(*trace.occurrences, occurrence),
    )

    assert changed.index().entity("entity-3").defining_owner_id == "entity-2"
    assert "entity-2" not in before.entity_ids


def test_snapshot_equality_expands_and_coalesces_styles() -> None:
    trace = _valid_trace()
    duplicate_style = replace(trace.styles[0], id="style-1")
    after = replace(
        trace.snapshots[1],
        style_spans=(
            StyleSpan(0, 1, "style-1"),
            StyleSpan(1, 3, "style-1"),
        ),
    )
    equivalent = replace(
        trace,
        styles=(trace.styles[0], duplicate_style),
        snapshots=(trace.snapshots[0], after),
    )

    assert equivalent.snapshots_semantically_equal("snapshot-0", "snapshot-1")

    different_metadata = replace(
        equivalent.metadata[3],
        value=RenderedValue("builtins.bool", "0", "repr"),
    )
    near_miss = replace(
        equivalent,
        metadata=(*equivalent.metadata[:3], different_metadata),
    )
    assert not near_miss.snapshots_semantically_equal("snapshot-0", "snapshot-1")

    false_style = replace(
        trace.styles[0],
        meta=cast(FrozenMap, freeze_json({"typed": [False]})),
    )
    zero_style = replace(
        trace.styles[0],
        id="style-1",
        meta=cast(FrozenMap, freeze_json({"typed": [0]})),
    )
    typed_after = replace(trace.snapshots[1], style_spans=(StyleSpan(0, 3, "style-1"),))
    typed_near_miss = replace(
        trace,
        styles=(false_style, zero_style),
        snapshots=(trace.snapshots[0], typed_after),
    )
    assert not typed_near_miss.snapshots_semantically_equal("snapshot-0", "snapshot-1")


def test_index_rebuilds_from_canonical_relations_effects_and_occurrences() -> None:
    trace = _valid_trace()
    replacement = TraceEntity("entity-2", "statement", "fixture.Replacement")
    unexplained = TraceEntity("entity-3", "statement", "fixture.Unexplained")
    operations = (
        MutationOperation(
            "operation-0",
            0,
            "event-0",
            None,
            "Statement.replace_by",
            "completed",
            ("entity-0",),
            ("entity-2",),
            "stack-0",
        ),
        MutationOperation(
            "operation-1",
            1,
            "event-0",
            "operation-0",
            "Statement.delete",
            "completed",
            ("entity-2",),
            (),
            "stack-0",
        ),
        MutationOperation(
            "operation-2",
            2,
            "event-0",
            None,
            "Statement.delete",
            "incomplete",
            ("entity-3",),
            (),
            "stack-0",
        ),
    )
    relation = ProvenanceRelation(
        "relation-0",
        "statement_replaced_by",
        "entity-0",
        "entity-2",
        "operation-0",
    )
    effect = EntityEffect(
        "effect-0",
        "statement_delete_completed",
        "entity-2",
        "operation-1",
    )
    populated = replace(
        trace,
        entities=(*trace.entities, replacement, unexplained),
        operations=operations,
        relations=(relation,),
        effects=(effect,),
    )

    first = populated.index()
    second = populated.index()
    assert first is not second
    assert first.relations_from("entity-0")[0] is populated.relations[0]
    assert first.relations_to("entity-2")[0] is populated.relations[0]
    assert first.effects_for_entity("entity-2")[0] is populated.effects[0]
    assert first.effects_for_operation("operation-1")[0] is populated.effects[0]
    assert first.operations_for_event("event-0") == operations
    assert not first.is_unmatched("entity-1")
    assert first.is_unmatched("entity-3")
    assert first.identity_match(
        "entity-1", "snapshot-0", "snapshot-1"
    ).left_occurrence_ids == ("occurrence-1",)
    assert first.projected_lines("snapshot-0", "entity-1") == (1,)
    assert second.relations_from("entity-0") == first.relations_from("entity-0")


def test_empty_container_occurrence_projects_to_no_lines() -> None:
    trace = _valid_trace()
    empty = replace(trace.occurrences[0], start=2, end=2)
    changed = replace(trace, occurrences=(empty, *trace.occurrences[1:]))

    assert changed.index().lines_for_occurrence("occurrence-0") == ()
