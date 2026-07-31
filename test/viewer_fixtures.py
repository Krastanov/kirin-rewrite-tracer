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


@dataclass(frozen=True, slots=True)
class EventSpec:
    label: str
    parent: str | None
    before: str
    after: str | None


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
    metadata_id = f"metadata-{len(metadata)}"
    metadata.append(
        MetadataRecord(
            metadata_id,
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
            (metadata_id,),
            True,
        )
    )
    return snapshot_id
