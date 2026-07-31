from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import cast

from kirin_rewrite_tracer import Trace
from kirin_rewrite_tracer._model import (
    CaptureConfiguration,
    EntityEffect,
    EntityOccurrence,
    FrameLocation,
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
    freeze_json,
)

VIEWER_HOSTILE = (
    '</ScRiPt><img src=x onerror="globalThis.viewerPwned=1">'
    "& __proto__ https://invalid.example/\N{GRINNING FACE}"
)

SELECTION_IDS = {
    "R9": "event-0",
    "C4": "event-1",
    "G8": "event-2",
    "C1": "event-3",
    "S7": "event-4",
    "D2": "event-5",
    "T0": "event-6",
}

HANDOFF_IDS = {
    "A": "event-0",
    "B": "event-1",
    "C": "event-2",
    "D": "event-3",
    "E": "event-4",
    "F": "event-5",
    "G": "event-6",
}

COARSE_PROVENANCE_EVENT_ID = "event-1"
COARSE_PROVENANCE_ENTITY_IDS = {
    "root": "entity-0",
    "survivor": "entity-1",
    "split_source": "entity-2",
    "split_destination_left": "entity-3",
    "split_destination_right": "entity-4",
    "merge_source_left": "entity-5",
    "merge_source_right": "entity-6",
    "merge_destination": "entity-7",
    "duplicate_source": "entity-8",
    "duplicate_destination": "entity-9",
    "depth_1_source": "entity-10",
    "depth_1_destination": "entity-11",
    "depth_2_source": "entity-12",
    "depth_2_destination": "entity-13",
    "depth_5_source": "entity-14",
    "depth_5_destination": "entity-15",
    "incomplete_child_source": "entity-16",
    "incomplete_child_destination": "entity-17",
    "ancestor_source": "entity-18",
    "ancestor_destination": "entity-19",
    "sibling_source": "entity-20",
    "sibling_destination": "entity-21",
    "missing_source": "entity-22",
    "missing_destination": "entity-23",
    "reversed_source": "entity-24",
    "reversed_destination": "entity-25",
    "path_source": "entity-26",
    "path_middle": "entity-27",
    "path_destination": "entity-28",
    "zero_use_source": "entity-29",
    "zero_use_destination": "entity-30",
    "incomplete_operation_source": "entity-31",
    "incomplete_operation_destination": "entity-32",
    "similar_before": "entity-33",
    "similar_after": "entity-34",
    "non_ssa_destination": "entity-35",
    "deleted_statement": "entity-36",
}
COARSE_PROVENANCE_RELATION_IDS = {
    "split_left": "relation-0",
    "split_right": "relation-1",
    "merge_left": "relation-2",
    "merge_right": "relation-3",
    "duplicate_first": "relation-4",
    "duplicate_second": "relation-5",
    "depth_1": "relation-6",
    "depth_2": "relation-7",
    "depth_5": "relation-8",
    "incomplete_child": "relation-9",
    "ancestor": "relation-10",
    "sibling": "relation-11",
    "missing": "relation-12",
    "reversed": "relation-13",
    "path_first": "relation-14",
    "path_second": "relation-15",
    "non_ssa": "relation-16",
}

PIPELINE_EVENT_IDS = {
    "A": "event-0",
    "B": "event-1",
    "C": "event-2",
    "D": "event-3",
    "E": "event-4",
    "F": "event-5",
    "G": "event-6",
    "D_CHILD": "event-7",
}
PIPELINE_ENTITY_IDS = {
    "root": "entity-0",
    "left": "entity-1",
    "middle_left": "entity-2",
    "middle_right": "entity-3",
    "right": "entity-4",
    "handoff_survivor": "entity-5",
    "similar_left": "entity-6",
    "similar_right": "entity-7",
    "handoff_relation_source": "entity-8",
    "handoff_relation_destination": "entity-9",
    "barrier_survivor": "entity-10",
    "incomplete_relation_source": "entity-11",
    "incomplete_relation_destination": "entity-12",
}
PIPELINE_RELATION_IDS = {
    "A": "relation-0",
    "B": "relation-1",
    "C": "relation-2",
    "handoff_owner_d": "relation-3",
    "handoff_owner_e": "relation-4",
    "handoff_owner_d_child": "relation-5",
    "handoff_owner_d_ancestor": "relation-6",
    "incomplete_event_must_not_cross": "relation-7",
}

METADATA_EVENT_IDS = {"A": "event-0", "B": "event-1"}
METADATA_ENTITY_IDS = {
    "root": "entity-0",
    "survivor": "entity-1",
    "unnamed": "entity-2",
    "block_argument": "entity-3",
    "pair_left": "entity-4",
    "pair_right": "entity-5",
    "external_owner": "entity-6",
    "external": "entity-7",
    "similar_owner": "entity-8",
    "similar": "entity-9",
}
METADATA_HOSTILE = (
    '</ScRiPt><img src=x onerror="globalThis.metadataPwned=1">'
    "& __proto__ https://metadata.invalid/\N{GRINNING FACE}"
)
METADATA_LONG_TEXT = "long-" + ("0123456789" * 90)
METADATA_MULTILINE_TEXT = "first line\nsecond line\nthird line"


@dataclass(frozen=True, slots=True)
class EventSpec:
    label: str
    parent: str | None
    before: str
    after: str | None


@dataclass(frozen=True, slots=True)
class SSAOccurrenceSpec:
    entity_id: str
    role: str
    text: str


@dataclass(frozen=True, slots=True)
class MetadataSpec:
    entity_id: str
    namespace: str
    key: str
    presence: str
    value: RenderedValue | None


@dataclass(frozen=True, slots=True)
class OperationSpec:
    owner_event_id: str
    api: str
    outcome: str
    source_entity_ids: tuple[str, ...]
    destination_entity_ids: tuple[str, ...]


def selection_trace() -> Trace:
    return event_trace(
        (
            EventSpec("R9", None, "R9 before", None),
            EventSpec("C4", "R9", "C4 before", "C4 after"),
            EventSpec("G8", "C4", "G8 before", "G8 after"),
            EventSpec("C1", None, "C1 before", "C1 after"),
            EventSpec("S7", None, "S7 before", "S7 after"),
            EventSpec("D2", "S7", "D2 before", "D2 after"),
            EventSpec("T0", None, "T0 before", "T0 after"),
        )
    )


def handoff_trace() -> Trace:
    return event_trace(
        (
            EventSpec("A", None, "A before", "shared"),
            EventSpec("B", None, "shared", "shared"),
            EventSpec("C", None, "shared", "C after"),
            EventSpec("D", None, "barrier", None),
            EventSpec("E", None, "barrier", "E after"),
            EventSpec("F", None, "F before", "right incomplete"),
            EventSpec("G", None, "right incomplete", None),
        )
    )


def event_trace(specifications: tuple[EventSpec, ...]) -> Trace:
    configuration = _configuration()
    style = StyleRecord("style-0")
    entities = (TraceEntity("entity-0", "statement", "fixture.Root"),)
    stack = InvocationStack(
        "stack-0", (FrameLocation("viewer_fixture.py", 17, "rewrite"),)
    )
    snapshots: list[Snapshot] = []
    occurrences: list[EntityOccurrence] = []
    events: list[RewriteEvent] = []
    event_id_by_label: dict[str, str] = {}
    sibling_ordinals: defaultdict[str | None, int] = defaultdict(int)

    for sequence, specification in enumerate(specifications):
        event_id = f"event-{sequence}"
        if specification.label in event_id_by_label:
            raise ValueError(f"duplicate fixture event label: {specification.label}")
        parent_id = (
            None
            if specification.parent is None
            else event_id_by_label[specification.parent]
        )
        sibling_ordinal = sibling_ordinals[parent_id]
        sibling_ordinals[parent_id] += 1
        event_id_by_label[specification.label] = event_id

        before_id = _append_snapshot(
            snapshots,
            occurrences,
            event_id=event_id,
            state="before",
            root_entity_id="entity-0",
            text=specification.before,
            entity_ids=("entity-0",),
        )
        after_id = (
            None
            if specification.after is None
            else _append_snapshot(
                snapshots,
                occurrences,
                event_id=event_id,
                state="after",
                root_entity_id="entity-0",
                text=specification.after,
                entity_ids=("entity-0",),
            )
        )
        events.append(
            RewriteEvent(
                id=event_id,
                sequence=sequence,
                parent_id=parent_id,
                sibling_ordinal=sibling_ordinal,
                rule_type=specification.label,
                completion="incomplete" if after_id is None else "complete",
                root_entity_id="entity-0",
                before_snapshot_id=before_id,
                after_snapshot_id=after_id,
                invocation_stack_id="stack-0",
                result=(
                    None
                    if after_id is None
                    else RewriteResultRecord(
                        False,
                        specification.before != specification.after,
                        False,
                    )
                ),
            )
        )

    return Trace(
        schema_version=1,
        complete=all(event.completion == "complete" for event in events),
        configurations=(configuration,),
        styles=(style,),
        entities=entities,
        snapshots=tuple(snapshots),
        occurrences=tuple(occurrences),
        stacks=(stack,),
        events=tuple(events),
    )


def facts_trace() -> Trace:
    configuration = _configuration()
    child_configuration = CaptureConfiguration(
        "configuration-1",
        configuration.kirin_commit,
        configuration.rich_version,
        "child-only-theme",
        False,
        f"child-only-hint-{VIEWER_HOSTILE}",
        False,
        "child-only-highlighter",
    )
    style = StyleRecord(
        "style-0",
        meta=cast(FrozenMap, freeze_json({"owner": "parent"})),
    )
    child_style = StyleRecord(
        "style-1",
        bold=True,
        meta=cast(
            FrozenMap,
            freeze_json({"owner": "child", "hostile": VIEWER_HOSTILE}),
        ),
    )
    entities = (
        TraceEntity("entity-0", "statement", "fixture.ParentRoot"),
        TraceEntity("entity-1", "ssa", "fixture.ParentValue", "entity-0"),
        TraceEntity("entity-2", "statement", "fixture.ChildRoot"),
        TraceEntity("entity-3", "ssa", "fixture.ChildValue", "entity-2"),
        TraceEntity("entity-4", "statement", "fixture.ExternalOwner"),
        TraceEntity("entity-5", "ssa", "fixture.TransientValue", "entity-4"),
        TraceEntity("entity-6", "statement", "fixture.TransientStatement"),
        TraceEntity("entity-7", "statement", "fixture.ParentTransientStatement"),
    )
    snapshots: list[Snapshot] = []
    occurrences: list[EntityOccurrence] = []
    metadata: list[MetadataRecord] = []

    parent_before = _append_detailed_snapshot(
        snapshots,
        occurrences,
        metadata,
        event_id="event-0",
        state="before",
        root_entity_id="entity-0",
        value_entity_id="entity-1",
        text=f"parent before {VIEWER_HOSTILE}",
        metadata_text=f"parent metadata before {VIEWER_HOSTILE}",
    )
    parent_after = _append_detailed_snapshot(
        snapshots,
        occurrences,
        metadata,
        event_id="event-0",
        state="after",
        root_entity_id="entity-0",
        value_entity_id="entity-1",
        text=f"parent after {VIEWER_HOSTILE}",
        metadata_text=f"parent metadata after {VIEWER_HOSTILE}",
    )
    child_before = _append_detailed_snapshot(
        snapshots,
        occurrences,
        metadata,
        event_id="event-1",
        state="before",
        root_entity_id="entity-2",
        value_entity_id="entity-3",
        text=f"child before {VIEWER_HOSTILE}",
        metadata_text=f"child metadata {VIEWER_HOSTILE}",
        configuration_id="configuration-1",
        style_id="style-1",
    )
    sibling_before = _append_snapshot(
        snapshots,
        occurrences,
        event_id="event-2",
        state="before",
        root_entity_id="entity-0",
        text="sibling before",
        entity_ids=("entity-0",),
    )
    sibling_after = _append_snapshot(
        snapshots,
        occurrences,
        event_id="event-2",
        state="after",
        root_entity_id="entity-0",
        text="sibling after",
        entity_ids=("entity-0",),
    )

    stacks = tuple(
        InvocationStack(
            f"stack-{index}",
            (
                FrameLocation(
                    f"owner-{index}-{VIEWER_HOSTILE}",
                    100 + index,
                    f"call-{index}-{VIEWER_HOSTILE}",
                ),
            ),
        )
        for index in range(7)
    )
    events = (
        RewriteEvent(
            "event-0",
            0,
            None,
            0,
            f"ParentRule{VIEWER_HOSTILE}",
            "complete",
            "entity-0",
            parent_before,
            parent_after,
            "stack-0",
            RewriteResultRecord(False, True, False),
        ),
        RewriteEvent(
            "event-1",
            1,
            "event-0",
            0,
            f"ChildRule{VIEWER_HOSTILE}",
            "incomplete",
            "entity-2",
            child_before,
            None,
            "stack-1",
            None,
        ),
        RewriteEvent(
            "event-2",
            2,
            None,
            1,
            "SiblingRule",
            "complete",
            "entity-0",
            sibling_before,
            sibling_after,
            "stack-6",
            RewriteResultRecord(False, True, False),
        ),
    )
    operations = (
        MutationOperation(
            "operation-0",
            0,
            "event-0",
            None,
            "Statement.delete",
            "completed",
            ("entity-7",),
            (),
            "stack-2",
        ),
        MutationOperation(
            "operation-1",
            1,
            "event-1",
            None,
            "SSAValue.replace_by",
            "completed",
            ("entity-1",),
            ("entity-5",),
            "stack-3",
        ),
        MutationOperation(
            "operation-2",
            2,
            "event-1",
            "operation-1",
            "Statement.from_stmt",
            "incomplete",
            ("entity-6",),
            (),
            "stack-4",
        ),
        MutationOperation(
            "operation-3",
            3,
            "event-1",
            None,
            "Statement.delete",
            "completed",
            ("entity-6",),
            (),
            "stack-5",
        ),
    )
    relation = ProvenanceRelation(
        "relation-0",
        "ssa_uses_retargeted_to",
        "entity-1",
        "entity-5",
        "operation-1",
    )
    effects = (
        EntityEffect(
            "effect-0",
            "statement_delete_completed",
            "entity-7",
            "operation-0",
        ),
        EntityEffect(
            "effect-1",
            "statement_delete_completed",
            "entity-6",
            "operation-3",
        ),
    )
    return Trace(
        schema_version=1,
        complete=False,
        configurations=(configuration, child_configuration),
        styles=(style, child_style),
        entities=entities,
        snapshots=tuple(snapshots),
        occurrences=tuple(occurrences),
        metadata=tuple(metadata),
        stacks=stacks,
        events=events,
        operations=operations,
        relations=(relation,),
        effects=effects,
    )


def metadata_trace() -> Trace:
    entity_ids = METADATA_ENTITY_IDS
    configuration = _configuration()
    styles = (StyleRecord("style-0"), StyleRecord("style-1", bold=True))
    entities = (
        TraceEntity(entity_ids["root"], "statement", "fixture.MetadataRoot"),
        TraceEntity(
            entity_ids["survivor"],
            "ssa",
            "fixture.SurvivorValue",
            entity_ids["root"],
        ),
        TraceEntity(
            entity_ids["unnamed"],
            "ssa",
            "fixture.UnnamedValue",
            entity_ids["root"],
        ),
        TraceEntity(
            entity_ids["block_argument"],
            "ssa",
            "fixture.BlockArgument",
            entity_ids["root"],
        ),
        TraceEntity(
            entity_ids["pair_left"],
            "ssa",
            "fixture.PairValueLeft",
            entity_ids["root"],
        ),
        TraceEntity(
            entity_ids["pair_right"],
            "ssa",
            "fixture.PairValueRight",
            entity_ids["root"],
        ),
        TraceEntity(
            entity_ids["external_owner"],
            "statement",
            "fixture.ExternalOwner",
        ),
        TraceEntity(
            entity_ids["external"],
            "ssa",
            "fixture.ExternalValue",
            entity_ids["external_owner"],
        ),
        TraceEntity(
            entity_ids["similar_owner"],
            "statement",
            "fixture.SimilarOwner",
        ),
        TraceEntity(
            entity_ids["similar"],
            "ssa",
            "fixture.SimilarValue",
            entity_ids["similar_owner"],
        ),
    )
    snapshots: list[Snapshot] = []
    occurrences: list[EntityOccurrence] = []
    metadata: list[MetadataRecord] = []
    repeated_survivor = tuple(
        SSAOccurrenceSpec(entity_ids["survivor"], "reference", "%survive😀")
        for _ in range(10)
    )
    rich_values = (
        SSAOccurrenceSpec(entity_ids["survivor"], "definition", "%survive😀"),
        SSAOccurrenceSpec(entity_ids["survivor"], "reference", "%survive😀"),
        SSAOccurrenceSpec(entity_ids["unnamed"], "definition", "%0"),
        SSAOccurrenceSpec(entity_ids["block_argument"], "definition", "%arg"),
        SSAOccurrenceSpec(entity_ids["pair_left"], "definition", "%pair:0"),
        SSAOccurrenceSpec(entity_ids["pair_right"], "definition", "%pair:1"),
        SSAOccurrenceSpec(entity_ids["external"], "reference", "%same"),
        SSAOccurrenceSpec(entity_ids["similar"], "definition", "%same"),
        *repeated_survivor,
    )
    before_metadata = _metadata_specs("before", "!fixture.before")
    shared_metadata = _metadata_specs("shared", "!fixture.after")
    final_metadata = _metadata_specs("final", "!fixture.final")
    all_snapshot_entities = tuple(entity.id for entity in entities)

    a_before = _append_metadata_snapshot(
        snapshots,
        occurrences,
        metadata,
        event_id=METADATA_EVENT_IDS["A"],
        state="before",
        root_entity_id=entity_ids["root"],
        values=rich_values,
        entity_ids=all_snapshot_entities,
        metadata_specs=before_metadata,
        split_first_occurrence=True,
    )
    a_after = _append_metadata_snapshot(
        snapshots,
        occurrences,
        metadata,
        event_id=METADATA_EVENT_IDS["A"],
        state="after",
        root_entity_id=entity_ids["root"],
        values=rich_values,
        entity_ids=all_snapshot_entities,
        metadata_specs=shared_metadata,
        split_first_occurrence=True,
    )
    b_before = _append_metadata_snapshot(
        snapshots,
        occurrences,
        metadata,
        event_id=METADATA_EVENT_IDS["B"],
        state="before",
        root_entity_id=entity_ids["root"],
        values=rich_values,
        entity_ids=all_snapshot_entities,
        metadata_specs=shared_metadata,
        split_first_occurrence=True,
    )
    b_after = _append_metadata_snapshot(
        snapshots,
        occurrences,
        metadata,
        event_id=METADATA_EVENT_IDS["B"],
        state="after",
        root_entity_id=entity_ids["root"],
        values=(
            SSAOccurrenceSpec(
                entity_ids["survivor"],
                "definition",
                "%survive😀",
            ),
            SSAOccurrenceSpec(entity_ids["unnamed"], "definition", "%0"),
            SSAOccurrenceSpec(entity_ids["external"], "reference", "%same"),
        ),
        entity_ids=all_snapshot_entities,
        metadata_specs=final_metadata,
    )
    stack = InvocationStack(
        "stack-0", (FrameLocation("metadata_viewer.py", 17, "rewrite"),)
    )
    events = (
        _fixture_event(
            METADATA_EVENT_IDS["A"],
            0,
            None,
            0,
            "MetadataARule",
            entity_ids["root"],
            a_before,
            a_after,
        ),
        _fixture_event(
            METADATA_EVENT_IDS["B"],
            1,
            None,
            1,
            "MetadataBRule",
            entity_ids["root"],
            b_before,
            b_after,
        ),
    )
    operation = MutationOperation(
        "operation-0",
        0,
        METADATA_EVENT_IDS["A"],
        None,
        "SSAValue.replace_by",
        "completed",
        (entity_ids["external"],),
        (entity_ids["survivor"],),
        "stack-0",
    )
    relation = ProvenanceRelation(
        "relation-0",
        "ssa_uses_retargeted_to",
        entity_ids["external"],
        entity_ids["survivor"],
        "operation-0",
    )
    return Trace(
        schema_version=1,
        complete=True,
        configurations=(configuration,),
        styles=styles,
        entities=entities,
        snapshots=tuple(snapshots),
        occurrences=tuple(occurrences),
        metadata=tuple(metadata),
        stacks=(stack,),
        events=events,
        operations=(operation,),
        relations=(relation,),
    )


def _metadata_specs(label: str, survivor_type: str) -> tuple[MetadataSpec, ...]:
    entity_ids = METADATA_ENTITY_IDS

    def present(
        entity_label: str,
        namespace: str,
        key: str,
        qualified_type: str,
        text: str,
        path: str,
    ) -> MetadataSpec:
        return MetadataSpec(
            entity_ids[entity_label],
            namespace,
            key,
            "present",
            RenderedValue(qualified_type, text, path),
        )

    records = [
        present("survivor", "ssa", "name", "builtins.str", "'survivor'", "repr"),
        present(
            "survivor",
            "ssa",
            "type",
            "fixture.PrintableType",
            survivor_type,
            "printable",
        ),
        present(
            "survivor",
            "hint",
            "phase",
            "builtins.str",
            label,
            "repr",
        ),
        present(
            "survivor",
            "hint",
            "long",
            "builtins.str",
            METADATA_LONG_TEXT,
            "repr",
        ),
        present(
            "survivor",
            "hint",
            "multiline",
            "builtins.str",
            METADATA_MULTILINE_TEXT,
            "repr",
        ),
        present(
            "survivor",
            "analysis",
            "value",
            "builtins.bool",
            "False",
            "repr",
        ),
        MetadataSpec(
            entity_ids["unnamed"],
            "ssa",
            "name",
            "absent",
            None,
        ),
        present(
            "unnamed",
            "ssa",
            "type",
            "fixture.EmptyPrintable",
            "",
            "printable",
        ),
        present(
            "unnamed",
            "analysis",
            "value",
            "builtins.str",
            "",
            "printable",
        ),
        present(
            "block_argument",
            "ssa",
            "name",
            "builtins.str",
            "'arg'",
            "repr",
        ),
        present(
            "block_argument",
            "ssa",
            "type",
            "fixture.FailingPrintable",
            "  spaced\n type  ",
            "repr",
        ),
        present(
            "block_argument",
            "analysis",
            "value",
            "builtins.NoneType",
            "None",
            "repr",
        ),
        present(
            "pair_left",
            "ssa",
            "name",
            "builtins.str",
            "'pair-left'",
            "repr",
        ),
        present(
            "pair_left",
            "ssa",
            "type",
            "fixture.EqualTextA",
            "same-type",
            "printable",
        ),
        present(
            "pair_left",
            "analysis",
            "value",
            "builtins.dict",
            "{}",
            "repr",
        ),
        present(
            "pair_right",
            "ssa",
            "name",
            "builtins.str",
            "'pair-right'",
            "repr",
        ),
        present(
            "pair_right",
            "ssa",
            "type",
            "fixture.EqualTextB",
            "same-type",
            "repr",
        ),
        present(
            "pair_right",
            "analysis",
            "value",
            "builtins.bool",
            "True",
            "repr",
        ),
        present(
            "external",
            "ssa",
            "name",
            "builtins.str",
            "'external'",
            "repr",
        ),
        present(
            "external",
            "ssa",
            "type",
            "fixture.ExternalType",
            "external-type",
            "printable",
        ),
        present(
            "external",
            "hint",
            METADATA_HOSTILE,
            "builtins.str",
            f"{METADATA_HOSTILE}\n{METADATA_LONG_TEXT}",
            "repr",
        ),
        present(
            "similar",
            "ssa",
            "name",
            "builtins.str",
            "'same'",
            "repr",
        ),
        present(
            "similar",
            "ssa",
            "type",
            "fixture.HostileType",
            METADATA_HOSTILE,
            "printable",
        ),
        present(
            "similar",
            "analysis",
            "value",
            "builtins.int",
            "0",
            "repr",
        ),
    ]
    return tuple(records)


def coarse_provenance_trace() -> Trace:
    configuration = _configuration()
    styles = (StyleRecord("style-0"), StyleRecord("style-1", bold=True))
    entity_ids = COARSE_PROVENANCE_ENTITY_IDS
    entities = [TraceEntity(entity_ids["root"], "statement", "fixture.Root")]
    for index in range(1, 35):
        qualified_type = (
            "fixture.SimilarValue" if index in {33, 34} else f"fixture.Value{index}"
        )
        entities.append(
            TraceEntity(
                f"entity-{index}",
                "ssa",
                qualified_type,
                entity_ids["root"],
            )
        )
    entities.extend(
        (
            TraceEntity(
                entity_ids["non_ssa_destination"],
                "statement",
                "fixture.NonSSA",
            ),
            TraceEntity(
                entity_ids["deleted_statement"],
                "statement",
                "fixture.Deleted",
            ),
        )
    )

    snapshots: list[Snapshot] = []
    occurrences: list[EntityOccurrence] = []
    ancestor_before = _append_snapshot(
        snapshots,
        occurrences,
        event_id="event-0",
        state="before",
        root_entity_id=entity_ids["root"],
        text="ancestor before",
        entity_ids=(entity_ids["root"],),
    )
    ancestor_after = _append_snapshot(
        snapshots,
        occurrences,
        event_id="event-0",
        state="after",
        root_entity_id=entity_ids["root"],
        text="ancestor after",
        entity_ids=(entity_ids["root"],),
    )
    parent_before = _append_ssa_snapshot(
        snapshots,
        occurrences,
        event_id=COARSE_PROVENANCE_EVENT_ID,
        state="before",
        root_entity_id=entity_ids["root"],
        values=(
            SSAOccurrenceSpec(entity_ids["survivor"], "definition", "%stay😀"),
            SSAOccurrenceSpec(entity_ids["survivor"], "reference", "%stay😀"),
            SSAOccurrenceSpec(entity_ids["split_source"], "definition", "%split"),
            SSAOccurrenceSpec(
                entity_ids["merge_source_left"], "definition", "%merge-left"
            ),
            SSAOccurrenceSpec(
                entity_ids["merge_source_left"], "reference", "%merge-left"
            ),
            SSAOccurrenceSpec(
                entity_ids["merge_source_right"], "definition", "%merge-right"
            ),
            SSAOccurrenceSpec(
                entity_ids["duplicate_source"], "definition", "%duplicate"
            ),
            SSAOccurrenceSpec(entity_ids["depth_1_source"], "definition", "%depth-one"),
            SSAOccurrenceSpec(entity_ids["depth_2_source"], "definition", "%depth-two"),
            SSAOccurrenceSpec(
                entity_ids["depth_5_source"], "definition", "%depth-five"
            ),
            SSAOccurrenceSpec(
                entity_ids["incomplete_child_source"],
                "definition",
                "%caught-incomplete",
            ),
            SSAOccurrenceSpec(entity_ids["ancestor_source"], "definition", "%ancestor"),
            SSAOccurrenceSpec(entity_ids["sibling_source"], "definition", "%sibling"),
            SSAOccurrenceSpec(entity_ids["missing_source"], "definition", "%missing"),
            SSAOccurrenceSpec(
                entity_ids["reversed_destination"], "definition", "%reversed"
            ),
            SSAOccurrenceSpec(entity_ids["path_source"], "definition", "%two-edge"),
            SSAOccurrenceSpec(
                entity_ids["path_middle"], "reference", "%two-edge-middle"
            ),
            SSAOccurrenceSpec(entity_ids["zero_use_source"], "definition", "%zero-use"),
            SSAOccurrenceSpec(
                entity_ids["incomplete_operation_source"],
                "definition",
                "%incomplete-operation",
            ),
            SSAOccurrenceSpec(
                entity_ids["similar_before"], "definition", "%looks-the-same"
            ),
        ),
        split_first_occurrence=True,
    )
    parent_after = _append_ssa_snapshot(
        snapshots,
        occurrences,
        event_id=COARSE_PROVENANCE_EVENT_ID,
        state="after",
        root_entity_id=entity_ids["root"],
        values=(
            SSAOccurrenceSpec(entity_ids["survivor"], "reference", "%stay😀"),
            SSAOccurrenceSpec(entity_ids["survivor"], "reference", "%stay😀"),
            SSAOccurrenceSpec(
                entity_ids["split_destination_left"], "definition", "%split-left"
            ),
            SSAOccurrenceSpec(
                entity_ids["split_destination_left"], "reference", "%split-left"
            ),
            SSAOccurrenceSpec(
                entity_ids["split_destination_right"],
                "definition",
                "%split-right",
            ),
            SSAOccurrenceSpec(entity_ids["merge_destination"], "definition", "%merged"),
            SSAOccurrenceSpec(entity_ids["merge_destination"], "reference", "%merged"),
            SSAOccurrenceSpec(
                entity_ids["duplicate_destination"], "definition", "%duplicate"
            ),
            SSAOccurrenceSpec(
                entity_ids["depth_1_destination"], "definition", "%depth-one"
            ),
            SSAOccurrenceSpec(
                entity_ids["depth_2_destination"], "definition", "%depth-two"
            ),
            SSAOccurrenceSpec(
                entity_ids["depth_5_destination"], "definition", "%depth-five"
            ),
            SSAOccurrenceSpec(
                entity_ids["incomplete_child_destination"],
                "definition",
                "%caught-incomplete",
            ),
            SSAOccurrenceSpec(
                entity_ids["ancestor_destination"], "definition", "%ancestor"
            ),
            SSAOccurrenceSpec(
                entity_ids["sibling_destination"], "definition", "%sibling"
            ),
            SSAOccurrenceSpec(entity_ids["reversed_source"], "definition", "%reversed"),
            SSAOccurrenceSpec(
                entity_ids["path_destination"], "definition", "%two-edge"
            ),
            SSAOccurrenceSpec(
                entity_ids["path_middle"], "reference", "%two-edge-middle"
            ),
            SSAOccurrenceSpec(
                entity_ids["zero_use_destination"], "definition", "%zero-use"
            ),
            SSAOccurrenceSpec(
                entity_ids["incomplete_operation_destination"],
                "definition",
                "%incomplete-operation",
            ),
            SSAOccurrenceSpec(
                entity_ids["similar_after"], "definition", "%looks-the-same"
            ),
        ),
        container_entity_ids=(entity_ids["non_ssa_destination"],),
    )

    minimal_bindings: list[tuple[str, str, str | None]] = []
    for event_index, label in (
        (2, "depth one"),
        (3, "depth two"),
        (4, "depth three"),
        (5, "depth four"),
        (6, "depth five"),
    ):
        before = _append_snapshot(
            snapshots,
            occurrences,
            event_id=f"event-{event_index}",
            state="before",
            root_entity_id=entity_ids["root"],
            text=f"{label} before",
            entity_ids=(entity_ids["root"],),
        )
        after = _append_snapshot(
            snapshots,
            occurrences,
            event_id=f"event-{event_index}",
            state="after",
            root_entity_id=entity_ids["root"],
            text=f"{label} after",
            entity_ids=(entity_ids["root"],),
        )
        minimal_bindings.append((f"event-{event_index}", before, after))
    incomplete_before = _append_snapshot(
        snapshots,
        occurrences,
        event_id="event-7",
        state="before",
        root_entity_id=entity_ids["root"],
        text="caught incomplete descendant",
        entity_ids=(entity_ids["root"],),
    )
    sibling_before = _append_snapshot(
        snapshots,
        occurrences,
        event_id="event-8",
        state="before",
        root_entity_id=entity_ids["root"],
        text="sibling before",
        entity_ids=(entity_ids["root"],),
    )
    sibling_after = _append_snapshot(
        snapshots,
        occurrences,
        event_id="event-8",
        state="after",
        root_entity_id=entity_ids["root"],
        text="sibling after",
        entity_ids=(entity_ids["root"],),
    )

    events = (
        _fixture_event(
            "event-0",
            0,
            None,
            0,
            "AncestorRule",
            entity_ids["root"],
            ancestor_before,
            ancestor_after,
        ),
        _fixture_event(
            COARSE_PROVENANCE_EVENT_ID,
            1,
            "event-0",
            0,
            "CoarseParentRule",
            entity_ids["root"],
            parent_before,
            parent_after,
        ),
        _fixture_event(
            "event-2",
            2,
            COARSE_PROVENANCE_EVENT_ID,
            0,
            "DepthOneRule",
            entity_ids["root"],
            minimal_bindings[0][1],
            minimal_bindings[0][2],
        ),
        _fixture_event(
            "event-3",
            3,
            "event-2",
            0,
            "DepthTwoRule",
            entity_ids["root"],
            minimal_bindings[1][1],
            minimal_bindings[1][2],
        ),
        _fixture_event(
            "event-4",
            4,
            "event-3",
            0,
            "DepthThreeRule",
            entity_ids["root"],
            minimal_bindings[2][1],
            minimal_bindings[2][2],
        ),
        _fixture_event(
            "event-5",
            5,
            "event-4",
            0,
            "DepthFourRule",
            entity_ids["root"],
            minimal_bindings[3][1],
            minimal_bindings[3][2],
        ),
        _fixture_event(
            "event-6",
            6,
            "event-5",
            0,
            "DepthFiveRule",
            entity_ids["root"],
            minimal_bindings[4][1],
            minimal_bindings[4][2],
        ),
        _fixture_event(
            "event-7",
            7,
            COARSE_PROVENANCE_EVENT_ID,
            1,
            "CaughtIncompleteRule",
            entity_ids["root"],
            incomplete_before,
            None,
        ),
        _fixture_event(
            "event-8",
            8,
            "event-0",
            1,
            "SiblingRule",
            entity_ids["root"],
            sibling_before,
            sibling_after,
        ),
    )
    operation_specs = (
        OperationSpec(
            COARSE_PROVENANCE_EVENT_ID,
            "SSAValue.replace_by",
            "completed",
            (entity_ids["split_source"],),
            (entity_ids["split_destination_left"],),
        ),
        OperationSpec(
            COARSE_PROVENANCE_EVENT_ID,
            "SSAValue.replace_by",
            "completed",
            (entity_ids["split_source"],),
            (entity_ids["split_destination_right"],),
        ),
        OperationSpec(
            COARSE_PROVENANCE_EVENT_ID,
            "SSAValue.replace_by",
            "completed",
            (entity_ids["merge_source_left"],),
            (entity_ids["merge_destination"],),
        ),
        OperationSpec(
            COARSE_PROVENANCE_EVENT_ID,
            "SSAValue.replace_by",
            "completed",
            (entity_ids["merge_source_right"],),
            (entity_ids["merge_destination"],),
        ),
        OperationSpec(
            COARSE_PROVENANCE_EVENT_ID,
            "SSAValue.replace_by",
            "completed",
            (entity_ids["duplicate_source"],),
            (entity_ids["duplicate_destination"],),
        ),
        OperationSpec(
            COARSE_PROVENANCE_EVENT_ID,
            "SSAValue.replace_by",
            "completed",
            (entity_ids["duplicate_source"],),
            (entity_ids["duplicate_destination"],),
        ),
        OperationSpec(
            "event-2",
            "SSAValue.replace_by",
            "completed",
            (entity_ids["depth_1_source"],),
            (entity_ids["depth_1_destination"],),
        ),
        OperationSpec(
            "event-3",
            "SSAValue.replace_by",
            "completed",
            (entity_ids["depth_2_source"],),
            (entity_ids["depth_2_destination"],),
        ),
        OperationSpec(
            "event-6",
            "SSAValue.replace_by",
            "completed",
            (entity_ids["depth_5_source"],),
            (entity_ids["depth_5_destination"],),
        ),
        OperationSpec(
            "event-7",
            "SSAValue.replace_by",
            "completed",
            (entity_ids["incomplete_child_source"],),
            (entity_ids["incomplete_child_destination"],),
        ),
        OperationSpec(
            "event-0",
            "SSAValue.replace_by",
            "completed",
            (entity_ids["ancestor_source"],),
            (entity_ids["ancestor_destination"],),
        ),
        OperationSpec(
            "event-8",
            "SSAValue.replace_by",
            "completed",
            (entity_ids["sibling_source"],),
            (entity_ids["sibling_destination"],),
        ),
        OperationSpec(
            COARSE_PROVENANCE_EVENT_ID,
            "SSAValue.replace_by",
            "completed",
            (entity_ids["missing_source"],),
            (entity_ids["missing_destination"],),
        ),
        OperationSpec(
            COARSE_PROVENANCE_EVENT_ID,
            "SSAValue.replace_by",
            "completed",
            (entity_ids["reversed_source"],),
            (entity_ids["reversed_destination"],),
        ),
        OperationSpec(
            COARSE_PROVENANCE_EVENT_ID,
            "SSAValue.replace_by",
            "completed",
            (entity_ids["path_source"],),
            (entity_ids["path_middle"],),
        ),
        OperationSpec(
            COARSE_PROVENANCE_EVENT_ID,
            "SSAValue.replace_by",
            "completed",
            (entity_ids["path_middle"],),
            (entity_ids["path_destination"],),
        ),
        OperationSpec(
            COARSE_PROVENANCE_EVENT_ID,
            "Statement.replace_by",
            "completed",
            (entity_ids["root"],),
            (entity_ids["non_ssa_destination"],),
        ),
        OperationSpec(
            COARSE_PROVENANCE_EVENT_ID,
            "SSAValue.replace_by",
            "completed",
            (entity_ids["zero_use_source"],),
            (entity_ids["zero_use_destination"],),
        ),
        OperationSpec(
            COARSE_PROVENANCE_EVENT_ID,
            "SSAValue.replace_by",
            "incomplete",
            (entity_ids["incomplete_operation_source"],),
            (entity_ids["incomplete_operation_destination"],),
        ),
        OperationSpec(
            COARSE_PROVENANCE_EVENT_ID,
            "Statement.delete",
            "completed",
            (entity_ids["deleted_statement"],),
            (),
        ),
    )
    operations = tuple(
        MutationOperation(
            f"operation-{sequence}",
            sequence,
            specification.owner_event_id,
            None,
            specification.api,
            specification.outcome,
            specification.source_entity_ids,
            specification.destination_entity_ids,
            "stack-0",
        )
        for sequence, specification in enumerate(operation_specs)
    )
    relation_specs = (
        ("ssa_uses_retargeted_to", "split_source", "split_destination_left", 0),
        ("ssa_uses_retargeted_to", "split_source", "split_destination_right", 1),
        ("ssa_uses_retargeted_to", "merge_source_left", "merge_destination", 2),
        ("ssa_uses_retargeted_to", "merge_source_right", "merge_destination", 3),
        ("ssa_uses_retargeted_to", "duplicate_source", "duplicate_destination", 4),
        ("ssa_uses_retargeted_to", "duplicate_source", "duplicate_destination", 5),
        ("ssa_uses_retargeted_to", "depth_1_source", "depth_1_destination", 6),
        ("ssa_uses_retargeted_to", "depth_2_source", "depth_2_destination", 7),
        ("ssa_uses_retargeted_to", "depth_5_source", "depth_5_destination", 8),
        (
            "ssa_uses_retargeted_to",
            "incomplete_child_source",
            "incomplete_child_destination",
            9,
        ),
        ("ssa_uses_retargeted_to", "ancestor_source", "ancestor_destination", 10),
        ("ssa_uses_retargeted_to", "sibling_source", "sibling_destination", 11),
        ("ssa_uses_retargeted_to", "missing_source", "missing_destination", 12),
        ("ssa_uses_retargeted_to", "reversed_source", "reversed_destination", 13),
        ("ssa_uses_retargeted_to", "path_source", "path_middle", 14),
        ("ssa_uses_retargeted_to", "path_middle", "path_destination", 15),
        ("statement_replaced_by", "root", "non_ssa_destination", 16),
    )
    relations = tuple(
        ProvenanceRelation(
            f"relation-{sequence}",
            basis,
            entity_ids[source_label],
            entity_ids[destination_label],
            f"operation-{operation_index}",
        )
        for sequence, (
            basis,
            source_label,
            destination_label,
            operation_index,
        ) in enumerate(relation_specs)
    )
    effect = EntityEffect(
        "effect-0",
        "statement_delete_completed",
        entity_ids["deleted_statement"],
        "operation-19",
    )
    stack = InvocationStack(
        "stack-0", (FrameLocation("coarse_provenance.py", 17, "rewrite"),)
    )
    return Trace(
        schema_version=1,
        complete=False,
        configurations=(configuration,),
        styles=styles,
        entities=tuple(entities),
        snapshots=tuple(snapshots),
        occurrences=tuple(occurrences),
        stacks=(stack,),
        events=events,
        operations=operations,
        relations=relations,
        effects=(effect,),
    )


def pipeline_provenance_trace() -> Trace:
    configuration = _configuration()
    style = StyleRecord("style-0")
    entity_ids = PIPELINE_ENTITY_IDS
    entities = (
        TraceEntity(entity_ids["root"], "statement", "fixture.PipelineRoot"),
        *(
            TraceEntity(
                f"entity-{index}",
                "ssa",
                (
                    "fixture.SimilarValue"
                    if index in {6, 7}
                    else f"fixture.PipelineValue{index}"
                ),
                entity_ids["root"],
            )
            for index in range(1, 13)
        ),
    )
    snapshots: list[Snapshot] = []
    occurrences: list[EntityOccurrence] = []
    a_before = _append_ssa_snapshot(
        snapshots,
        occurrences,
        event_id=PIPELINE_EVENT_IDS["A"],
        state="before",
        root_entity_id=entity_ids["root"],
        values=(SSAOccurrenceSpec(entity_ids["left"], "definition", "%left"),),
    )
    a_after = _append_ssa_snapshot(
        snapshots,
        occurrences,
        event_id=PIPELINE_EVENT_IDS["A"],
        state="after",
        root_entity_id=entity_ids["root"],
        values=(
            SSAOccurrenceSpec(entity_ids["middle_left"], "reference", "%middle-left"),
            SSAOccurrenceSpec(entity_ids["middle_left"], "reference", "%middle-left"),
        ),
    )
    b_before = _append_ssa_snapshot(
        snapshots,
        occurrences,
        event_id=PIPELINE_EVENT_IDS["B"],
        state="before",
        root_entity_id=entity_ids["root"],
        values=(
            SSAOccurrenceSpec(entity_ids["middle_left"], "reference", "%middle-left"),
            SSAOccurrenceSpec(entity_ids["middle_left"], "reference", "%middle-left"),
        ),
    )
    b_after = _append_ssa_snapshot(
        snapshots,
        occurrences,
        event_id=PIPELINE_EVENT_IDS["B"],
        state="after",
        root_entity_id=entity_ids["root"],
        values=(
            SSAOccurrenceSpec(entity_ids["middle_right"], "reference", "%middle-right"),
            SSAOccurrenceSpec(entity_ids["middle_right"], "reference", "%middle-right"),
        ),
    )
    c_before = _append_ssa_snapshot(
        snapshots,
        occurrences,
        event_id=PIPELINE_EVENT_IDS["C"],
        state="before",
        root_entity_id=entity_ids["root"],
        values=(
            SSAOccurrenceSpec(entity_ids["middle_right"], "reference", "%middle-right"),
            SSAOccurrenceSpec(entity_ids["middle_right"], "reference", "%middle-right"),
        ),
    )
    c_after = _append_ssa_snapshot(
        snapshots,
        occurrences,
        event_id=PIPELINE_EVENT_IDS["C"],
        state="after",
        root_entity_id=entity_ids["root"],
        values=(SSAOccurrenceSpec(entity_ids["right"], "definition", "%right"),),
    )
    d_before = _append_ssa_snapshot(
        snapshots,
        occurrences,
        event_id=PIPELINE_EVENT_IDS["D"],
        state="before",
        root_entity_id=entity_ids["root"],
        values=(
            SSAOccurrenceSpec(
                entity_ids["handoff_relation_source"],
                "definition",
                "%handoff-source",
            ),
        ),
    )
    d_after = _append_ssa_snapshot(
        snapshots,
        occurrences,
        event_id=PIPELINE_EVENT_IDS["D"],
        state="after",
        root_entity_id=entity_ids["root"],
        values=(
            SSAOccurrenceSpec(entity_ids["handoff_survivor"], "reference", "%survivor"),
            SSAOccurrenceSpec(entity_ids["handoff_survivor"], "reference", "%survivor"),
            SSAOccurrenceSpec(
                entity_ids["handoff_relation_source"],
                "reference",
                "%handoff-source",
            ),
            SSAOccurrenceSpec(
                entity_ids["handoff_relation_destination"],
                "definition",
                "%handoff-destination",
            ),
            SSAOccurrenceSpec(
                entity_ids["similar_left"], "definition", "%looks-the-same"
            ),
        ),
    )
    e_before = _append_ssa_snapshot(
        snapshots,
        occurrences,
        event_id=PIPELINE_EVENT_IDS["E"],
        state="before",
        root_entity_id=entity_ids["root"],
        values=(
            SSAOccurrenceSpec(entity_ids["handoff_survivor"], "reference", "%survivor"),
            SSAOccurrenceSpec(entity_ids["handoff_survivor"], "reference", "%survivor"),
            SSAOccurrenceSpec(
                entity_ids["handoff_relation_destination"],
                "reference",
                "%handoff-destination",
            ),
            SSAOccurrenceSpec(
                entity_ids["similar_right"], "definition", "%looks-the-same"
            ),
        ),
    )
    e_after = _append_ssa_snapshot(
        snapshots,
        occurrences,
        event_id=PIPELINE_EVENT_IDS["E"],
        state="after",
        root_entity_id=entity_ids["root"],
        values=(
            SSAOccurrenceSpec(
                entity_ids["handoff_relation_destination"],
                "reference",
                "%handoff-destination",
            ),
            SSAOccurrenceSpec(entity_ids["barrier_survivor"], "reference", "%barrier"),
            SSAOccurrenceSpec(
                entity_ids["incomplete_relation_source"],
                "reference",
                "%incomplete-source",
            ),
        ),
    )
    f_before = _append_ssa_snapshot(
        snapshots,
        occurrences,
        event_id=PIPELINE_EVENT_IDS["F"],
        state="before",
        root_entity_id=entity_ids["root"],
        values=(
            SSAOccurrenceSpec(
                entity_ids["handoff_relation_destination"],
                "reference",
                "%handoff-destination",
            ),
            SSAOccurrenceSpec(entity_ids["barrier_survivor"], "reference", "%barrier"),
            SSAOccurrenceSpec(
                entity_ids["incomplete_relation_source"],
                "reference",
                "%incomplete-source",
            ),
        ),
    )
    g_before = _append_ssa_snapshot(
        snapshots,
        occurrences,
        event_id=PIPELINE_EVENT_IDS["G"],
        state="before",
        root_entity_id=entity_ids["root"],
        values=(
            SSAOccurrenceSpec(entity_ids["barrier_survivor"], "reference", "%barrier"),
            SSAOccurrenceSpec(
                entity_ids["incomplete_relation_destination"],
                "reference",
                "%incomplete-destination",
            ),
        ),
    )
    g_after = _append_ssa_snapshot(
        snapshots,
        occurrences,
        event_id=PIPELINE_EVENT_IDS["G"],
        state="after",
        root_entity_id=entity_ids["root"],
        values=(
            SSAOccurrenceSpec(entity_ids["barrier_survivor"], "reference", "%barrier"),
            SSAOccurrenceSpec(
                entity_ids["incomplete_relation_destination"],
                "reference",
                "%incomplete-destination",
            ),
        ),
    )
    d_child_before = _append_snapshot(
        snapshots,
        occurrences,
        event_id=PIPELINE_EVENT_IDS["D_CHILD"],
        state="before",
        root_entity_id=entity_ids["root"],
        text="D child before",
        entity_ids=(entity_ids["root"],),
    )
    d_child_after = _append_snapshot(
        snapshots,
        occurrences,
        event_id=PIPELINE_EVENT_IDS["D_CHILD"],
        state="after",
        root_entity_id=entity_ids["root"],
        text="D child after",
        entity_ids=(entity_ids["root"],),
    )
    bindings = (
        ("A", None, 0, a_before, a_after),
        ("B", None, 1, b_before, b_after),
        ("C", None, 2, c_before, c_after),
        ("D", PIPELINE_EVENT_IDS["C"], 0, d_before, d_after),
        ("E", None, 3, e_before, e_after),
        ("F", None, 4, f_before, None),
        ("G", None, 5, g_before, g_after),
        (
            "D_CHILD",
            PIPELINE_EVENT_IDS["D"],
            0,
            d_child_before,
            d_child_after,
        ),
    )
    events = tuple(
        _fixture_event(
            PIPELINE_EVENT_IDS[label],
            sequence,
            parent_id,
            sibling_ordinal,
            f"Pipeline{label}Rule",
            entity_ids["root"],
            before_snapshot_id,
            after_snapshot_id,
        )
        for sequence, (
            label,
            parent_id,
            sibling_ordinal,
            before_snapshot_id,
            after_snapshot_id,
        ) in enumerate(bindings)
    )
    operation_specs = (
        OperationSpec(
            PIPELINE_EVENT_IDS["A"],
            "SSAValue.replace_by",
            "completed",
            (entity_ids["left"],),
            (entity_ids["middle_left"],),
        ),
        OperationSpec(
            PIPELINE_EVENT_IDS["B"],
            "SSAValue.replace_by",
            "completed",
            (entity_ids["middle_left"],),
            (entity_ids["middle_right"],),
        ),
        OperationSpec(
            PIPELINE_EVENT_IDS["C"],
            "SSAValue.replace_by",
            "completed",
            (entity_ids["middle_right"],),
            (entity_ids["right"],),
        ),
        OperationSpec(
            PIPELINE_EVENT_IDS["D"],
            "SSAValue.replace_by",
            "completed",
            (entity_ids["handoff_relation_source"],),
            (entity_ids["handoff_relation_destination"],),
        ),
        OperationSpec(
            PIPELINE_EVENT_IDS["E"],
            "SSAValue.replace_by",
            "completed",
            (entity_ids["handoff_relation_source"],),
            (entity_ids["handoff_relation_destination"],),
        ),
        OperationSpec(
            PIPELINE_EVENT_IDS["D_CHILD"],
            "SSAValue.replace_by",
            "completed",
            (entity_ids["handoff_relation_source"],),
            (entity_ids["handoff_relation_destination"],),
        ),
        OperationSpec(
            PIPELINE_EVENT_IDS["C"],
            "SSAValue.replace_by",
            "completed",
            (entity_ids["handoff_relation_source"],),
            (entity_ids["handoff_relation_destination"],),
        ),
        OperationSpec(
            PIPELINE_EVENT_IDS["F"],
            "SSAValue.replace_by",
            "completed",
            (entity_ids["incomplete_relation_source"],),
            (entity_ids["incomplete_relation_destination"],),
        ),
    )
    operations = tuple(
        MutationOperation(
            f"operation-{sequence}",
            sequence,
            specification.owner_event_id,
            None,
            specification.api,
            specification.outcome,
            specification.source_entity_ids,
            specification.destination_entity_ids,
            "stack-0",
        )
        for sequence, specification in enumerate(operation_specs)
    )
    relation_endpoints = (
        ("left", "middle_left"),
        ("middle_left", "middle_right"),
        ("middle_right", "right"),
        ("handoff_relation_source", "handoff_relation_destination"),
        ("handoff_relation_source", "handoff_relation_destination"),
        ("handoff_relation_source", "handoff_relation_destination"),
        ("handoff_relation_source", "handoff_relation_destination"),
        ("incomplete_relation_source", "incomplete_relation_destination"),
    )
    relations = tuple(
        ProvenanceRelation(
            f"relation-{sequence}",
            "ssa_uses_retargeted_to",
            entity_ids[source_label],
            entity_ids[destination_label],
            f"operation-{sequence}",
        )
        for sequence, (source_label, destination_label) in enumerate(relation_endpoints)
    )
    stack = InvocationStack(
        "stack-0", (FrameLocation("pipeline_provenance.py", 17, "rewrite"),)
    )
    return Trace(
        schema_version=1,
        complete=False,
        configurations=(configuration,),
        styles=(style,),
        entities=entities,
        snapshots=tuple(snapshots),
        occurrences=tuple(occurrences),
        stacks=(stack,),
        events=events,
        operations=operations,
        relations=relations,
    )


def _configuration() -> CaptureConfiguration:
    return CaptureConfiguration(
        "configuration-0",
        "7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a",
        "15.0.0",
        "dark",
        True,
        None,
        False,
        "rich.default",
    )


def _append_snapshot(
    snapshots: list[Snapshot],
    occurrences: list[EntityOccurrence],
    *,
    event_id: str,
    state: str,
    root_entity_id: str,
    text: str,
    entity_ids: tuple[str, ...],
) -> str:
    snapshot_id = f"snapshot-{len(snapshots)}"
    occurrence_id = f"occurrence-{len(occurrences)}"
    occurrences.append(
        EntityOccurrence(
            occurrence_id,
            snapshot_id,
            root_entity_id,
            "container",
            0,
            len(text),
        )
    )
    snapshots.append(
        Snapshot(
            snapshot_id,
            event_id,
            state,
            1,
            "configuration-0",
            root_entity_id,
            text,
            (StyleSpan(0, len(text), "style-0"),),
            entity_ids,
            (occurrence_id,),
            (),
            False,
        )
    )
    return snapshot_id


def _fixture_event(
    event_id: str,
    sequence: int,
    parent_id: str | None,
    sibling_ordinal: int,
    rule_type: str,
    root_entity_id: str,
    before_snapshot_id: str,
    after_snapshot_id: str | None,
) -> RewriteEvent:
    return RewriteEvent(
        id=event_id,
        sequence=sequence,
        parent_id=parent_id,
        sibling_ordinal=sibling_ordinal,
        rule_type=rule_type,
        completion="incomplete" if after_snapshot_id is None else "complete",
        root_entity_id=root_entity_id,
        before_snapshot_id=before_snapshot_id,
        after_snapshot_id=after_snapshot_id,
        invocation_stack_id="stack-0",
        result=(
            None
            if after_snapshot_id is None
            else RewriteResultRecord(False, True, False)
        ),
    )


def _append_ssa_snapshot(
    snapshots: list[Snapshot],
    occurrences: list[EntityOccurrence],
    *,
    event_id: str,
    state: str,
    root_entity_id: str,
    values: tuple[SSAOccurrenceSpec, ...],
    container_entity_ids: tuple[str, ...] = (),
    split_first_occurrence: bool = False,
) -> str:
    snapshot_id = f"snapshot-{len(snapshots)}"
    text_parts: list[str] = []
    value_intervals: list[tuple[SSAOccurrenceSpec, int, int]] = []
    cursor = 0
    for specification in values:
        if text_parts:
            text_parts.append(" ")
            cursor += 1
        start = cursor
        text_parts.append(specification.text)
        cursor += len(specification.text)
        value_intervals.append((specification, start, cursor))
    text = "".join(text_parts)

    occurrence_ids: list[str] = []

    def append_occurrence(entity_id: str, role: str, start: int, end: int) -> None:
        occurrence_id = f"occurrence-{len(occurrences)}"
        occurrences.append(
            EntityOccurrence(
                occurrence_id,
                snapshot_id,
                entity_id,
                role,
                start,
                end,
            )
        )
        occurrence_ids.append(occurrence_id)

    append_occurrence(root_entity_id, "container", 0, len(text))
    for entity_id in container_entity_ids:
        append_occurrence(entity_id, "container", 0, len(text))
    for specification, start, end in value_intervals:
        append_occurrence(specification.entity_id, specification.role, start, end)

    entity_ids = [root_entity_id]
    for entity_id in container_entity_ids:
        if entity_id not in entity_ids:
            entity_ids.append(entity_id)
    for specification in values:
        if specification.entity_id not in entity_ids:
            entity_ids.append(specification.entity_id)

    style_spans: tuple[StyleSpan, ...]
    if not text:
        style_spans = ()
    elif split_first_occurrence:
        first_start, first_end = value_intervals[0][1:]
        split = first_start + (first_end - first_start) // 2
        if split <= 0 or split >= len(text):
            raise ValueError("the split fixture requires text on both sides")
        style_spans = (
            StyleSpan(0, split, "style-0"),
            StyleSpan(split, len(text), "style-1"),
        )
    else:
        style_spans = (StyleSpan(0, len(text), "style-0"),)

    snapshots.append(
        Snapshot(
            id=snapshot_id,
            event_id=event_id,
            state=state,
            schema_version=1,
            configuration_id="configuration-0",
            root_entity_id=root_entity_id,
            text=text,
            style_spans=style_spans,
            entity_ids=tuple(entity_ids),
            occurrence_ids=tuple(occurrence_ids),
            metadata_ids=(),
            analysis_supplied=False,
        )
    )
    return snapshot_id


def _append_metadata_snapshot(
    snapshots: list[Snapshot],
    occurrences: list[EntityOccurrence],
    metadata: list[MetadataRecord],
    *,
    event_id: str,
    state: str,
    root_entity_id: str,
    values: tuple[SSAOccurrenceSpec, ...],
    entity_ids: tuple[str, ...],
    metadata_specs: tuple[MetadataSpec, ...],
    split_first_occurrence: bool = False,
) -> str:
    snapshot_id = f"snapshot-{len(snapshots)}"
    text_parts: list[str] = []
    value_intervals: list[tuple[SSAOccurrenceSpec, int, int]] = []
    cursor = 0
    for occurrence_specification in values:
        if text_parts:
            text_parts.append("\n")
            cursor += 1
        start = cursor
        text_parts.append(occurrence_specification.text)
        cursor += len(occurrence_specification.text)
        value_intervals.append((occurrence_specification, start, cursor))
    text = "".join(text_parts)

    occurrence_ids: list[str] = []

    def append_occurrence(entity_id: str, role: str, start: int, end: int) -> None:
        occurrence_id = f"occurrence-{len(occurrences)}"
        occurrences.append(
            EntityOccurrence(
                occurrence_id,
                snapshot_id,
                entity_id,
                role,
                start,
                end,
            )
        )
        occurrence_ids.append(occurrence_id)

    append_occurrence(root_entity_id, "container", 0, len(text))
    for occurrence_specification, start, end in value_intervals:
        append_occurrence(
            occurrence_specification.entity_id,
            occurrence_specification.role,
            start,
            end,
        )

    metadata_ids: list[str] = []
    for metadata_specification in metadata_specs:
        metadata_id = f"metadata-{len(metadata)}"
        metadata.append(
            MetadataRecord(
                metadata_id,
                snapshot_id,
                metadata_specification.entity_id,
                metadata_specification.namespace,
                metadata_specification.key,
                metadata_specification.presence,
                metadata_specification.value,
            )
        )
        metadata_ids.append(metadata_id)

    style_spans: tuple[StyleSpan, ...]
    if split_first_occurrence:
        first_start, first_end = value_intervals[0][1:]
        split = first_start + (first_end - first_start) // 2
        style_spans = (
            StyleSpan(0, split, "style-0"),
            StyleSpan(split, len(text), "style-1"),
        )
    else:
        style_spans = (StyleSpan(0, len(text), "style-0"),)
    snapshots.append(
        Snapshot(
            id=snapshot_id,
            event_id=event_id,
            state=state,
            schema_version=1,
            configuration_id="configuration-0",
            root_entity_id=root_entity_id,
            text=text,
            style_spans=style_spans,
            entity_ids=entity_ids,
            occurrence_ids=tuple(occurrence_ids),
            metadata_ids=tuple(metadata_ids),
            analysis_supplied=True,
        )
    )
    return snapshot_id


def _append_detailed_snapshot(
    snapshots: list[Snapshot],
    occurrences: list[EntityOccurrence],
    metadata: list[MetadataRecord],
    *,
    event_id: str,
    state: str,
    root_entity_id: str,
    value_entity_id: str,
    text: str,
    metadata_text: str,
    configuration_id: str = "configuration-0",
    style_id: str = "style-0",
) -> str:
    snapshot_id = f"snapshot-{len(snapshots)}"
    container_id = f"occurrence-{len(occurrences)}"
    value_id = f"occurrence-{len(occurrences) + 1}"
    occurrences.extend(
        (
            EntityOccurrence(
                container_id,
                snapshot_id,
                root_entity_id,
                "container",
                0,
                len(text),
            ),
            EntityOccurrence(
                value_id,
                snapshot_id,
                value_entity_id,
                "definition" if state == "before" else "reference",
                0,
                1,
            ),
        )
    )
    metadata_ids = tuple(f"metadata-{len(metadata) + index}" for index in range(3))
    metadata.extend(
        (
            MetadataRecord(
                metadata_ids[0],
                snapshot_id,
                value_entity_id,
                "ssa",
                "name",
                "present" if state == "before" else "absent",
                (
                    RenderedValue("builtins.str", f"name-{state}", "repr")
                    if state == "before"
                    else None
                ),
            ),
            MetadataRecord(
                metadata_ids[1],
                snapshot_id,
                value_entity_id,
                "ssa",
                "type",
                "present",
                RenderedValue(
                    "fixture.Type",
                    f"type-{state}-{VIEWER_HOSTILE}",
                    "printable" if state == "before" else "repr",
                ),
            ),
            MetadataRecord(
                metadata_ids[2],
                snapshot_id,
                value_entity_id,
                "analysis",
                f"key-{state}-{VIEWER_HOSTILE}",
                "present",
                RenderedValue(
                    "builtins.str",
                    metadata_text,
                    "repr" if state == "before" else "printable",
                ),
            ),
        )
    )
    snapshots.append(
        Snapshot(
            snapshot_id,
            event_id,
            state,
            1,
            configuration_id,
            root_entity_id,
            text,
            (StyleSpan(0, len(text), style_id),),
            (root_entity_id, value_entity_id),
            (container_id, value_id),
            metadata_ids,
            True,
        )
    )
    return snapshot_id
