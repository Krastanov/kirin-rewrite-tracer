from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from itertools import pairwise
from typing import TypeAlias, cast

SAFE_INTEGER_MAX = 9_007_199_254_740_991


class TraceValidationError(ValueError):
    """Raised when canonical trace facts are internally inconsistent."""


@dataclass(eq=False, frozen=True, slots=True)
class FrozenList:
    items: tuple[FrozenValue, ...]

    def __eq__(self, other: object) -> bool:
        return type(other) is FrozenList and _frozen_value_key(
            self
        ) == _frozen_value_key(other)

    def __hash__(self) -> int:
        return hash(_frozen_value_key(self))


@dataclass(eq=False, frozen=True, slots=True)
class FrozenMap:
    entries: tuple[tuple[str, FrozenValue], ...]

    def __eq__(self, other: object) -> bool:
        return type(other) is FrozenMap and _frozen_value_key(
            self
        ) == _frozen_value_key(other)

    def __hash__(self) -> int:
        return hash(_frozen_value_key(self))


FrozenValue: TypeAlias = bool | int | float | str | FrozenList | FrozenMap | None


def _frozen_value_key(value: FrozenValue) -> object:
    if value is None:
        return ("none",)
    if type(value) is bool:
        return ("bool", value)
    if type(value) is int:
        return ("int", value)
    if type(value) is float:
        return ("float", value.hex())
    if type(value) is str:
        return ("str", value)
    if type(value) is FrozenList:
        return (
            "list",
            tuple(_frozen_value_key(item) for item in value.items),
        )
    if type(value) is FrozenMap:
        return (
            "map",
            tuple((key, _frozen_value_key(item)) for key, item in value.entries),
        )
    raise TraceValidationError("unsupported frozen metadata value")


def freeze_json(value: object, _active: set[int] | None = None) -> FrozenValue:
    """Freeze the deliberately small JSON-safe style metadata domain."""

    if value is None:
        return value
    if type(value) in {bool, str}:
        return cast(bool | str, value)
    if type(value) is int:
        if not -SAFE_INTEGER_MAX <= value <= SAFE_INTEGER_MAX:
            raise TraceValidationError("integer is outside the JavaScript-safe range")
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise TraceValidationError("non-finite floats are unsupported")
        return value

    active = set() if _active is None else _active
    marker = id(value)
    if marker in active:
        raise TraceValidationError("cyclic metadata is unsupported")

    if type(value) is list:
        active.add(marker)
        try:
            return FrozenList(tuple(freeze_json(item, active) for item in value))
        finally:
            active.remove(marker)

    if type(value) is dict:
        active.add(marker)
        try:
            entries: list[tuple[str, FrozenValue]] = []
            for key, item in value.items():
                if type(key) is not str:
                    raise TraceValidationError("metadata map keys must be strings")
                entries.append((key, freeze_json(item, active)))
            return FrozenMap(tuple(entries))
        finally:
            active.remove(marker)

    raise TraceValidationError(
        f"unsupported metadata value type: {type(value).__module__}."
        f"{type(value).__qualname__}"
    )


def _validate_frozen_value(
    value: object, description: str, _active: set[int] | None = None
) -> None:
    if value is None or type(value) in {bool, str}:
        return
    if type(value) is int:
        if not -SAFE_INTEGER_MAX <= value <= SAFE_INTEGER_MAX:
            raise TraceValidationError(
                f"{description} integer is outside the JavaScript-safe range"
            )
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise TraceValidationError(f"{description} float must be finite")
        return
    if type(value) is FrozenList:
        active = set() if _active is None else _active
        marker = id(value)
        if marker in active:
            raise TraceValidationError(f"{description} cannot contain a cycle")
        active.add(marker)
        if type(value.items) is not tuple:
            raise TraceValidationError(f"{description} list storage must be a tuple")
        try:
            for item in value.items:
                _validate_frozen_value(item, description, active)
        finally:
            active.remove(marker)
        return
    if type(value) is FrozenMap:
        active = set() if _active is None else _active
        marker = id(value)
        if marker in active:
            raise TraceValidationError(f"{description} cannot contain a cycle")
        active.add(marker)
        if type(value.entries) is not tuple:
            raise TraceValidationError(f"{description} map storage must be a tuple")
        try:
            keys: set[str] = set()
            for entry in value.entries:
                if (
                    type(entry) is not tuple
                    or len(entry) != 2
                    or type(entry[0]) is not str
                ):
                    raise TraceValidationError(
                        f"{description} map entries must be string-keyed pairs"
                    )
                if entry[0] in keys:
                    raise TraceValidationError(f"{description} map keys must be unique")
                keys.add(entry[0])
                _validate_frozen_value(entry[1], description, active)
        finally:
            active.remove(marker)
        return
    raise TraceValidationError(f"{description} has an unsupported frozen value")


@dataclass(frozen=True, slots=True)
class CaptureConfiguration:
    id: str
    kirin_commit: str
    rich_version: str
    theme: str
    show_indent_mark: bool
    hint: str | None
    printer_analysis: bool
    highlighter: str


@dataclass(frozen=True, slots=True)
class ColorRecord:
    encoding: str
    name: str | None
    number: int | None
    triplet: tuple[int, int, int] | None


@dataclass(frozen=True, slots=True)
class StyleRecord:
    id: str
    color: ColorRecord | None = None
    bgcolor: ColorRecord | None = None
    bold: bool | None = None
    dim: bool | None = None
    italic: bool | None = None
    underline: bool | None = None
    blink: bool | None = None
    blink2: bool | None = None
    reverse: bool | None = None
    conceal: bool | None = None
    strike: bool | None = None
    underline2: bool | None = None
    frame: bool | None = None
    encircle: bool | None = None
    overline: bool | None = None
    link: str | None = None
    meta: FrozenMap = FrozenMap(())


@dataclass(frozen=True, slots=True)
class StyleSpan:
    start: int
    end: int
    style_id: str | None


@dataclass(frozen=True, slots=True)
class TraceEntity:
    id: str
    kind: str
    qualified_type: str
    defining_owner_id: str | None = None


@dataclass(frozen=True, slots=True)
class EntityOccurrence:
    id: str
    snapshot_id: str
    entity_id: str
    role: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class RenderedValue:
    qualified_type: str
    text: str
    path: str


@dataclass(frozen=True, slots=True)
class MetadataRecord:
    id: str
    snapshot_id: str
    owner_entity_id: str
    namespace: str
    key: str
    presence: str
    value: RenderedValue | None


@dataclass(frozen=True, slots=True)
class FrameLocation:
    filename: str
    line: int
    function: str


@dataclass(frozen=True, slots=True)
class InvocationStack:
    id: str
    frames: tuple[FrameLocation, ...]


@dataclass(frozen=True, slots=True)
class RewriteResultRecord:
    terminated: bool
    has_done_something: bool
    exceeded_max_iter: bool


@dataclass(frozen=True, slots=True)
class RewriteEvent:
    id: str
    sequence: int
    parent_id: str | None
    sibling_ordinal: int
    rule_type: str
    completion: str
    root_entity_id: str
    before_snapshot_id: str
    after_snapshot_id: str | None
    invocation_stack_id: str
    result: RewriteResultRecord | None


@dataclass(frozen=True, slots=True)
class Snapshot:
    id: str
    event_id: str
    state: str
    schema_version: int
    configuration_id: str
    root_entity_id: str
    text: str
    style_spans: tuple[StyleSpan, ...]
    entity_ids: tuple[str, ...]
    occurrence_ids: tuple[str, ...]
    metadata_ids: tuple[str, ...]
    analysis_supplied: bool


@dataclass(frozen=True, slots=True)
class MutationOperation:
    id: str
    sequence: int
    owner_event_id: str
    parent_operation_id: str | None
    api: str
    outcome: str
    source_entity_ids: tuple[str, ...]
    destination_entity_ids: tuple[str, ...]
    invocation_stack_id: str


@dataclass(frozen=True, slots=True)
class ProvenanceRelation:
    id: str
    basis: str
    source_entity_id: str
    destination_entity_id: str
    mutation_operation_id: str


@dataclass(frozen=True, slots=True)
class EntityEffect:
    id: str
    kind: str
    affected_entity_id: str
    mutation_operation_id: str


@dataclass(frozen=True, slots=True)
class IdentityMatch:
    entity_id: str
    left_occurrence_ids: tuple[str, ...]
    right_occurrence_ids: tuple[str, ...]


_RELATION_KINDS = {
    "statement_replaced_by": ("statement", "statement"),
    "ssa_uses_retargeted_to": ("ssa", "ssa"),
    "statement_copied_to": ("statement", "statement"),
    "result_copied_to": ("ssa", "ssa"),
    "region_cloned_to": ("region", "region"),
    "block_cloned_to": ("block", "block"),
    "block_argument_cloned_to": ("ssa", "ssa"),
}

_RELATIONS_BY_API = {
    "Statement.replace_by": {"statement_replaced_by"},
    "SSAValue.replace_by": {"ssa_uses_retargeted_to"},
    "Statement.from_stmt": {"statement_copied_to", "result_copied_to"},
    "Region.clone": {
        "region_cloned_to",
        "block_cloned_to",
        "block_argument_cloned_to",
    },
    "Statement.delete": set(),
}


@dataclass(frozen=True, slots=True)
class Trace:
    schema_version: int
    complete: bool
    configurations: tuple[CaptureConfiguration, ...] = ()
    styles: tuple[StyleRecord, ...] = ()
    entities: tuple[TraceEntity, ...] = ()
    snapshots: tuple[Snapshot, ...] = ()
    occurrences: tuple[EntityOccurrence, ...] = ()
    metadata: tuple[MetadataRecord, ...] = ()
    stacks: tuple[InvocationStack, ...] = ()
    events: tuple[RewriteEvent, ...] = ()
    operations: tuple[MutationOperation, ...] = ()
    relations: tuple[ProvenanceRelation, ...] = ()
    effects: tuple[EntityEffect, ...] = ()

    def __post_init__(self) -> None:
        _validate_trace(self)

    def index(self) -> TraceIndex:
        """Build a disposable index from canonical facts."""

        return TraceIndex(self)

    def snapshots_semantically_equal(
        self, left_snapshot_id: str, right_snapshot_id: str
    ) -> bool:
        index = self.index()
        left = index.snapshot(left_snapshot_id)
        right = index.snapshot(right_snapshot_id)
        return _snapshot_semantic_key(self, index, left) == _snapshot_semantic_key(
            self, index, right
        )


class TraceIndex:
    """Disposable reverse and projection indexes over an immutable Trace."""

    __slots__ = (
        "_children_by_parent",
        "_configurations",
        "_effects_by_entity",
        "_effects_by_operation",
        "_entities",
        "_events",
        "_metadata",
        "_occurrences",
        "_occurrences_by_entity_snapshot",
        "_operations",
        "_operations_by_event",
        "_relations_by_destination",
        "_relations_by_source",
        "_snapshots",
        "_stacks",
        "_styles",
        "trace",
    )

    def __init__(self, trace: Trace) -> None:
        self.trace = trace
        self._configurations = {item.id: item for item in trace.configurations}
        self._styles = {item.id: item for item in trace.styles}
        self._entities = {item.id: item for item in trace.entities}
        self._snapshots = {item.id: item for item in trace.snapshots}
        self._occurrences = {item.id: item for item in trace.occurrences}
        self._metadata = {item.id: item for item in trace.metadata}
        self._stacks = {item.id: item for item in trace.stacks}
        self._events = {item.id: item for item in trace.events}
        self._operations = {item.id: item for item in trace.operations}

        self._relations_by_source: dict[str, list[ProvenanceRelation]] = {}
        self._relations_by_destination: dict[str, list[ProvenanceRelation]] = {}
        for relation in trace.relations:
            self._relations_by_source.setdefault(relation.source_entity_id, []).append(
                relation
            )
            self._relations_by_destination.setdefault(
                relation.destination_entity_id, []
            ).append(relation)

        self._effects_by_entity: dict[str, list[EntityEffect]] = {}
        self._effects_by_operation: dict[str, list[EntityEffect]] = {}
        for effect in trace.effects:
            self._effects_by_entity.setdefault(effect.affected_entity_id, []).append(
                effect
            )
            self._effects_by_operation.setdefault(
                effect.mutation_operation_id, []
            ).append(effect)

        self._operations_by_event: dict[str, list[MutationOperation]] = {}
        for operation in trace.operations:
            self._operations_by_event.setdefault(operation.owner_event_id, []).append(
                operation
            )

        self._children_by_parent: dict[str | None, list[RewriteEvent]] = {}
        for event in trace.events:
            self._children_by_parent.setdefault(event.parent_id, []).append(event)

        self._occurrences_by_entity_snapshot: dict[
            tuple[str, str], list[EntityOccurrence]
        ] = {}
        for occurrence in trace.occurrences:
            self._occurrences_by_entity_snapshot.setdefault(
                (occurrence.entity_id, occurrence.snapshot_id), []
            ).append(occurrence)

    def configuration(self, item_id: str) -> CaptureConfiguration:
        return self._configurations[item_id]

    def style(self, item_id: str) -> StyleRecord:
        return self._styles[item_id]

    def entity(self, item_id: str) -> TraceEntity:
        return self._entities[item_id]

    def snapshot(self, item_id: str) -> Snapshot:
        return self._snapshots[item_id]

    def occurrence(self, item_id: str) -> EntityOccurrence:
        return self._occurrences[item_id]

    def metadata_record(self, item_id: str) -> MetadataRecord:
        return self._metadata[item_id]

    def stack(self, item_id: str) -> InvocationStack:
        return self._stacks[item_id]

    def event(self, item_id: str) -> RewriteEvent:
        return self._events[item_id]

    def operation(self, item_id: str) -> MutationOperation:
        return self._operations[item_id]

    def children(self, parent_id: str | None) -> tuple[RewriteEvent, ...]:
        return tuple(self._children_by_parent.get(parent_id, ()))

    def operations_for_event(self, event_id: str) -> tuple[MutationOperation, ...]:
        return tuple(self._operations_by_event.get(event_id, ()))

    def relations_from(self, entity_id: str) -> tuple[ProvenanceRelation, ...]:
        return tuple(self._relations_by_source.get(entity_id, ()))

    def relations_to(self, entity_id: str) -> tuple[ProvenanceRelation, ...]:
        return tuple(self._relations_by_destination.get(entity_id, ()))

    def effects_for_entity(self, entity_id: str) -> tuple[EntityEffect, ...]:
        return tuple(self._effects_by_entity.get(entity_id, ()))

    def effects_for_operation(self, operation_id: str) -> tuple[EntityEffect, ...]:
        return tuple(self._effects_by_operation.get(operation_id, ()))

    def occurrences_for(
        self, entity_id: str, snapshot_id: str | None = None
    ) -> tuple[EntityOccurrence, ...]:
        if snapshot_id is not None:
            return tuple(
                self._occurrences_by_entity_snapshot.get((entity_id, snapshot_id), ())
            )
        return tuple(
            occurrence
            for occurrence in self.trace.occurrences
            if occurrence.entity_id == entity_id
        )

    def identity_match(
        self, entity_id: str, left_snapshot_id: str, right_snapshot_id: str
    ) -> IdentityMatch:
        return IdentityMatch(
            entity_id=entity_id,
            left_occurrence_ids=tuple(
                item.id for item in self.occurrences_for(entity_id, left_snapshot_id)
            ),
            right_occurrence_ids=tuple(
                item.id for item in self.occurrences_for(entity_id, right_snapshot_id)
            ),
        )

    def lines_for_occurrence(self, occurrence_id: str) -> tuple[int, ...]:
        occurrence = self.occurrence(occurrence_id)
        text = self.snapshot(occurrence.snapshot_id).text
        line = text.count("\n", 0, occurrence.start) + 1
        lines: list[int] = []
        for character in text[occurrence.start : occurrence.end]:
            if not lines or lines[-1] != line:
                lines.append(line)
            if character == "\n":
                line += 1
        return tuple(lines)

    def projected_lines(self, snapshot_id: str, entity_id: str) -> tuple[int, ...]:
        lines: set[int] = set()
        for occurrence in self.occurrences_for(entity_id, snapshot_id):
            lines.update(self.lines_for_occurrence(occurrence.id))
        return tuple(sorted(lines))

    def is_descendant(self, candidate_id: str, ancestor_id: str) -> bool:
        current = self.event(candidate_id)
        while current.parent_id is not None:
            if current.parent_id == ancestor_id:
                return True
            current = self.event(current.parent_id)
        return False

    def is_unmatched(self, entity_id: str) -> bool:
        if self.relations_from(entity_id) or self.relations_to(entity_id):
            return False
        if self.effects_for_entity(entity_id):
            return False
        occurrence_snapshots = {
            item.snapshot_id for item in self.occurrences_for(entity_id)
        }
        return len(occurrence_snapshots) < 2


def _validate_domain(prefix: str, identifiers: tuple[str, ...]) -> None:
    for index, identifier in enumerate(identifiers):
        expected = f"{prefix}-{index}"
        if identifier != expected:
            raise TraceValidationError(
                f"{prefix} IDs must be monotonic: expected {expected!r}, "
                f"got {identifier!r}"
            )


def _require_reference(
    reference: str, values: Mapping[str, object], description: str
) -> None:
    if reference not in values:
        raise TraceValidationError(f"unknown {description}: {reference!r}")


def _validate_parent_graph(
    records: tuple[tuple[str, str | None], ...], description: str
) -> None:
    parents = dict(records)
    for identifier in parents:
        seen: set[str] = set()
        current: str | None = identifier
        while current is not None:
            if current in seen:
                raise TraceValidationError(f"{description} parent cycle at {current!r}")
            seen.add(current)
            current = parents.get(current)


def _validate_color(color: ColorRecord) -> None:
    if type(color.encoding) is not str:
        raise TraceValidationError("color encoding must be a string")
    if color.encoding not in {
        "default",
        "standard",
        "eight_bit",
        "truecolor",
        "windows",
    }:
        raise TraceValidationError(f"unsupported color encoding: {color.encoding!r}")
    if color.name is not None and type(color.name) is not str:
        raise TraceValidationError("color name must be a string or None")
    if color.number is not None and (
        type(color.number) is not int or not 0 <= color.number <= 255
    ):
        raise TraceValidationError("color number must be an integer in [0, 255]")
    if color.triplet is not None and (
        type(color.triplet) is not tuple
        or len(color.triplet) != 3
        or any(
            type(channel) is not int or not 0 <= channel <= 255
            for channel in color.triplet
        )
    ):
        raise TraceValidationError(
            "color triplet must contain three integer channels in [0, 255]"
        )


def _require_bool(value: object, description: str) -> None:
    if type(value) is not bool:
        raise TraceValidationError(f"{description} must be a boolean")


def _require_int(value: object, description: str, *, minimum: int = 0) -> None:
    if type(value) is not int or value < minimum:
        raise TraceValidationError(
            f"{description} must be an integer greater than or equal to {minimum}"
        )


def _require_str(value: object, description: str, *, nonempty: bool = False) -> None:
    if type(value) is not str or (nonempty and not value):
        qualifier = "nonempty " if nonempty else ""
        raise TraceValidationError(f"{description} must be a {qualifier}string")


def _require_optional_str(
    value: object, description: str, *, nonempty: bool = False
) -> None:
    if value is not None:
        _require_str(value, description, nonempty=nonempty)


def _require_tuple(value: object, description: str) -> None:
    if type(value) is not tuple:
        raise TraceValidationError(f"{description} must be a tuple")


def _require_record_tuple(
    values: object, record_type: type[object], description: str
) -> None:
    _require_tuple(values, description)
    records = cast(tuple[object, ...], values)
    if any(type(item) is not record_type for item in records):
        raise TraceValidationError(
            f"{description} must contain only {record_type.__name__} records"
        )


def _require_string_tuple(values: object, description: str) -> None:
    _require_tuple(values, description)
    for value in cast(tuple[object, ...], values):
        _require_str(value, description, nonempty=True)


def _validate_trace_shapes(trace: Trace) -> None:
    _require_int(trace.schema_version, "trace schema version", minimum=1)
    _require_bool(trace.complete, "trace completeness")
    for values, record_type, description in (
        (trace.configurations, CaptureConfiguration, "trace configurations"),
        (trace.styles, StyleRecord, "trace styles"),
        (trace.entities, TraceEntity, "trace entities"),
        (trace.snapshots, Snapshot, "trace snapshots"),
        (trace.occurrences, EntityOccurrence, "trace occurrences"),
        (trace.metadata, MetadataRecord, "trace metadata"),
        (trace.stacks, InvocationStack, "trace stacks"),
        (trace.events, RewriteEvent, "trace events"),
        (trace.operations, MutationOperation, "trace operations"),
        (trace.relations, ProvenanceRelation, "trace relations"),
        (trace.effects, EntityEffect, "trace effects"),
    ):
        _require_record_tuple(values, record_type, description)

    for configuration in trace.configurations:
        _require_str(configuration.id, "configuration ID", nonempty=True)
        _require_str(
            configuration.kirin_commit, "configuration Kirin commit", nonempty=True
        )
        _require_str(
            configuration.rich_version, "configuration Rich version", nonempty=True
        )
        _require_str(configuration.theme, "configuration theme", nonempty=True)
        _require_bool(
            configuration.show_indent_mark, "configuration indentation setting"
        )
        _require_optional_str(configuration.hint, "configuration hint")
        _require_bool(
            configuration.printer_analysis, "configuration printer analysis setting"
        )
        _require_str(
            configuration.highlighter,
            "configuration highlighter",
            nonempty=True,
        )

    for style in trace.styles:
        _require_str(style.id, "style ID", nonempty=True)
        if style.color is not None and type(style.color) is not ColorRecord:
            raise TraceValidationError("style color must be a ColorRecord or None")
        if style.bgcolor is not None and type(style.bgcolor) is not ColorRecord:
            raise TraceValidationError(
                "style background color must be a ColorRecord or None"
            )
        for name in (
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
        ):
            value = getattr(style, name)
            if value is not None:
                _require_bool(value, f"style {name}")
        _require_optional_str(style.link, "style link")
        if type(style.meta) is not FrozenMap:
            raise TraceValidationError("style metadata must be a FrozenMap")
        _validate_frozen_value(style.meta, "style metadata")

    for entity in trace.entities:
        _require_str(entity.id, "entity ID", nonempty=True)
        _require_str(entity.kind, "entity kind", nonempty=True)
        _require_str(entity.qualified_type, "entity qualified type", nonempty=True)
        _require_optional_str(
            entity.defining_owner_id, "entity defining-owner ID", nonempty=True
        )

    for snapshot in trace.snapshots:
        _require_str(snapshot.id, "snapshot ID", nonempty=True)
        _require_str(snapshot.event_id, "snapshot event ID", nonempty=True)
        _require_str(snapshot.state, "snapshot state", nonempty=True)
        _require_int(snapshot.schema_version, "snapshot schema version", minimum=1)
        _require_str(
            snapshot.configuration_id,
            "snapshot configuration ID",
            nonempty=True,
        )
        _require_str(snapshot.root_entity_id, "snapshot root entity ID", nonempty=True)
        _require_str(snapshot.text, "snapshot text")
        _require_record_tuple(snapshot.style_spans, StyleSpan, "snapshot style spans")
        _require_string_tuple(snapshot.entity_ids, "snapshot entity IDs")
        _require_string_tuple(snapshot.occurrence_ids, "snapshot occurrence IDs")
        _require_string_tuple(snapshot.metadata_ids, "snapshot metadata IDs")
        _require_bool(snapshot.analysis_supplied, "snapshot analysis state")
        for span in snapshot.style_spans:
            _require_int(span.start, "style span start")
            _require_int(span.end, "style span end")
            _require_optional_str(span.style_id, "style span ID", nonempty=True)

    for occurrence in trace.occurrences:
        _require_str(occurrence.id, "occurrence ID", nonempty=True)
        _require_str(occurrence.snapshot_id, "occurrence snapshot ID", nonempty=True)
        _require_str(occurrence.entity_id, "occurrence entity ID", nonempty=True)
        _require_str(occurrence.role, "occurrence role", nonempty=True)
        _require_int(occurrence.start, "occurrence start")
        _require_int(occurrence.end, "occurrence end")

    for record in trace.metadata:
        _require_str(record.id, "metadata ID", nonempty=True)
        _require_str(record.snapshot_id, "metadata snapshot ID", nonempty=True)
        _require_str(record.owner_entity_id, "metadata owner entity ID", nonempty=True)
        _require_str(record.namespace, "metadata namespace", nonempty=True)
        _require_str(record.key, "metadata key")
        _require_str(record.presence, "metadata presence", nonempty=True)
        if record.value is not None:
            if type(record.value) is not RenderedValue:
                raise TraceValidationError(
                    "metadata value must be a RenderedValue or None"
                )
            _require_str(
                record.value.qualified_type,
                "rendered metadata qualified type",
                nonempty=True,
            )
            _require_str(record.value.text, "rendered metadata text")
            _require_str(record.value.path, "rendered metadata path", nonempty=True)

    for stack in trace.stacks:
        _require_str(stack.id, "stack ID", nonempty=True)
        _require_record_tuple(stack.frames, FrameLocation, "stack frames")
        for frame in stack.frames:
            _require_str(frame.filename, "frame filename", nonempty=True)
            _require_int(frame.line, "frame line")
            _require_str(frame.function, "frame function", nonempty=True)

    for event in trace.events:
        _require_str(event.id, "event ID", nonempty=True)
        _require_int(event.sequence, "event sequence")
        _require_optional_str(event.parent_id, "event parent ID", nonempty=True)
        _require_int(event.sibling_ordinal, "event sibling ordinal")
        _require_str(event.rule_type, "event rule type", nonempty=True)
        _require_str(event.completion, "event completion", nonempty=True)
        _require_str(event.root_entity_id, "event root entity ID", nonempty=True)
        _require_str(
            event.before_snapshot_id, "event before snapshot ID", nonempty=True
        )
        _require_optional_str(
            event.after_snapshot_id, "event after snapshot ID", nonempty=True
        )
        _require_str(
            event.invocation_stack_id, "event invocation stack ID", nonempty=True
        )
        if event.result is not None:
            if type(event.result) is not RewriteResultRecord:
                raise TraceValidationError(
                    "event result must be a RewriteResultRecord or None"
                )
            _require_bool(event.result.terminated, "result terminated state")
            _require_bool(event.result.has_done_something, "result mutation state")
            _require_bool(event.result.exceeded_max_iter, "result max-iteration state")

    for operation in trace.operations:
        _require_str(operation.id, "operation ID", nonempty=True)
        _require_int(operation.sequence, "operation sequence")
        _require_str(
            operation.owner_event_id, "operation owner event ID", nonempty=True
        )
        _require_optional_str(
            operation.parent_operation_id,
            "operation parent ID",
            nonempty=True,
        )
        _require_str(operation.api, "operation API", nonempty=True)
        _require_str(operation.outcome, "operation outcome", nonempty=True)
        _require_string_tuple(
            operation.source_entity_ids, "operation source entity IDs"
        )
        _require_string_tuple(
            operation.destination_entity_ids,
            "operation destination entity IDs",
        )
        _require_str(
            operation.invocation_stack_id,
            "operation invocation stack ID",
            nonempty=True,
        )

    for relation in trace.relations:
        _require_str(relation.id, "relation ID", nonempty=True)
        _require_str(relation.basis, "relation basis", nonempty=True)
        _require_str(
            relation.source_entity_id, "relation source entity ID", nonempty=True
        )
        _require_str(
            relation.destination_entity_id,
            "relation destination entity ID",
            nonempty=True,
        )
        _require_str(
            relation.mutation_operation_id,
            "relation mutation operation ID",
            nonempty=True,
        )

    for effect in trace.effects:
        _require_str(effect.id, "effect ID", nonempty=True)
        _require_str(effect.kind, "effect kind", nonempty=True)
        _require_str(
            effect.affected_entity_id, "effect affected entity ID", nonempty=True
        )
        _require_str(
            effect.mutation_operation_id,
            "effect mutation operation ID",
            nonempty=True,
        )


def _validate_trace(trace: Trace) -> None:
    _validate_trace_shapes(trace)
    if trace.schema_version != 1:
        raise TraceValidationError("unsupported trace schema version")

    _validate_domain("configuration", tuple(item.id for item in trace.configurations))
    _validate_domain("style", tuple(item.id for item in trace.styles))
    _validate_domain("entity", tuple(item.id for item in trace.entities))
    _validate_domain("snapshot", tuple(item.id for item in trace.snapshots))
    _validate_domain("occurrence", tuple(item.id for item in trace.occurrences))
    _validate_domain("metadata", tuple(item.id for item in trace.metadata))
    _validate_domain("stack", tuple(item.id for item in trace.stacks))
    _validate_domain("event", tuple(item.id for item in trace.events))
    _validate_domain("operation", tuple(item.id for item in trace.operations))
    _validate_domain("relation", tuple(item.id for item in trace.relations))
    _validate_domain("effect", tuple(item.id for item in trace.effects))

    configurations = {item.id: item for item in trace.configurations}
    styles = {item.id: item for item in trace.styles}
    entities = {item.id: item for item in trace.entities}
    snapshots = {item.id: item for item in trace.snapshots}
    occurrences = {item.id: item for item in trace.occurrences}
    metadata = {item.id: item for item in trace.metadata}
    stacks = {item.id: item for item in trace.stacks}
    events = {item.id: item for item in trace.events}
    operations = {item.id: item for item in trace.operations}

    for configuration in trace.configurations:
        if (
            not configuration.kirin_commit
            or not configuration.rich_version
            or not configuration.theme
            or not configuration.highlighter
        ):
            raise TraceValidationError("capture configuration labels must be nonempty")

    for style in trace.styles:
        if style.color is not None:
            _validate_color(style.color)
        if style.bgcolor is not None:
            _validate_color(style.bgcolor)

    for entity in trace.entities:
        if entity.kind not in {"region", "block", "statement", "ssa"}:
            raise TraceValidationError(f"unsupported entity kind: {entity.kind!r}")
        if not entity.qualified_type:
            raise TraceValidationError("entity qualified type must be nonempty")
        if entity.kind == "ssa":
            if entity.defining_owner_id is None:
                raise TraceValidationError("SSA entities require a defining owner")
            _require_reference(entity.defining_owner_id, entities, "SSA defining owner")
            if entities[entity.defining_owner_id].kind not in {"block", "statement"}:
                raise TraceValidationError(
                    "SSA defining owners must be blocks or statements"
                )
        elif entity.defining_owner_id is not None:
            raise TraceValidationError("non-SSA entities cannot have defining owners")

    for stack in trace.stacks:
        for frame in stack.frames:
            if frame.line < 0:
                raise TraceValidationError("frame line numbers must be nonnegative")
            if not frame.filename or not frame.function:
                raise TraceValidationError("frame fields must be nonempty")

    root_ordinals: dict[str | None, int] = {}
    for index, event in enumerate(trace.events):
        if event.sequence != index:
            raise TraceValidationError("event sequence must match entry order")
        if event.parent_id is not None:
            _require_reference(event.parent_id, events, "event parent")
            if int(event.parent_id.removeprefix("event-")) >= index:
                raise TraceValidationError("event parents must precede their children")
        expected_ordinal = root_ordinals.get(event.parent_id, 0)
        if event.sibling_ordinal != expected_ordinal:
            raise TraceValidationError("event sibling ordinals must be contiguous")
        root_ordinals[event.parent_id] = expected_ordinal + 1
        if not event.rule_type:
            raise TraceValidationError("event rule type must be nonempty")
        if event.completion not in {"complete", "incomplete"}:
            raise TraceValidationError("unknown event completion")
        _require_reference(event.root_entity_id, entities, "event root entity")
        if entities[event.root_entity_id].kind == "ssa":
            raise TraceValidationError("an event root cannot be an SSA entity")
        _require_reference(event.before_snapshot_id, snapshots, "event before snapshot")
        _require_reference(event.invocation_stack_id, stacks, "event stack")
        before = snapshots[event.before_snapshot_id]
        if (
            before.event_id != event.id
            or before.state != "before"
            or before.root_entity_id != event.root_entity_id
        ):
            raise TraceValidationError("event before snapshot binding is invalid")
        if event.completion == "complete":
            if event.after_snapshot_id is None or event.result is None:
                raise TraceValidationError(
                    "complete events require an after snapshot and result"
                )
            _require_reference(
                event.after_snapshot_id, snapshots, "event after snapshot"
            )
            after = snapshots[event.after_snapshot_id]
            if (
                after.event_id != event.id
                or after.state != "after"
                or after.root_entity_id != event.root_entity_id
            ):
                raise TraceValidationError("event after snapshot binding is invalid")
        elif event.after_snapshot_id is not None or event.result is not None:
            raise TraceValidationError(
                "incomplete events cannot have an after snapshot or result"
            )

    _validate_parent_graph(
        tuple((item.id, item.parent_id) for item in trace.events), "event"
    )
    if trace.complete != all(event.completion == "complete" for event in trace.events):
        raise TraceValidationError("aggregate completeness does not match events")

    snapshot_bindings: list[str] = []
    for event in trace.events:
        snapshot_bindings.append(event.before_snapshot_id)
        if event.after_snapshot_id is not None:
            snapshot_bindings.append(event.after_snapshot_id)
    if len(snapshot_bindings) != len(set(snapshot_bindings)) or set(
        snapshot_bindings
    ) != set(snapshots):
        raise TraceValidationError("each snapshot must have one event/state binding")

    occurrence_bindings: list[str] = []
    metadata_bindings: list[str] = []
    used_configurations: set[str] = set()
    used_styles: set[str] = set()
    interactive_by_snapshot: dict[str, list[tuple[int, int]]] = {}
    for snapshot in trace.snapshots:
        if snapshot.schema_version != trace.schema_version:
            raise TraceValidationError("snapshot schema does not match trace schema")
        _require_reference(
            snapshot.configuration_id, configurations, "capture configuration"
        )
        used_configurations.add(snapshot.configuration_id)
        _require_reference(snapshot.event_id, events, "snapshot event")
        _require_reference(snapshot.root_entity_id, entities, "snapshot root")
        if snapshot.state not in {"before", "after"}:
            raise TraceValidationError("unknown snapshot state")
        if len(snapshot.entity_ids) != len(set(snapshot.entity_ids)):
            raise TraceValidationError("snapshot entity IDs must be unique")
        if snapshot.root_entity_id not in snapshot.entity_ids:
            raise TraceValidationError("snapshot entities must include its root")
        for entity_id in snapshot.entity_ids:
            _require_reference(entity_id, entities, "snapshot entity")

        if snapshot.text:
            cursor = 0
            for span in snapshot.style_spans:
                if span.start != cursor or span.end <= span.start:
                    raise TraceValidationError(
                        "style spans must cover text contiguously"
                    )
                if span.end > len(snapshot.text):
                    raise TraceValidationError("style span exceeds snapshot text")
                if span.style_id is not None:
                    _require_reference(span.style_id, styles, "style span style")
                    used_styles.add(span.style_id)
                cursor = span.end
            if cursor != len(snapshot.text):
                raise TraceValidationError("style spans must cover all snapshot text")
        elif snapshot.style_spans:
            raise TraceValidationError("empty snapshots cannot have style spans")

        for occurrence_id in snapshot.occurrence_ids:
            _require_reference(occurrence_id, occurrences, "snapshot occurrence")
            occurrence = occurrences[occurrence_id]
            if occurrence.snapshot_id != snapshot.id:
                raise TraceValidationError("occurrence snapshot binding is invalid")
            if occurrence.entity_id not in snapshot.entity_ids:
                raise TraceValidationError(
                    "occurrence entity is absent from its snapshot"
                )
            if occurrence.role not in {"container", "definition", "reference"}:
                raise TraceValidationError("unknown occurrence role")
            if (
                occurrence.start < 0
                or occurrence.end < occurrence.start
                or occurrence.end > len(snapshot.text)
            ):
                raise TraceValidationError("occurrence interval is invalid")
            if occurrence.role != "container" and occurrence.end == occurrence.start:
                raise TraceValidationError(
                    "interactive occurrence intervals must be nonempty"
                )
            entity_kind = entities[occurrence.entity_id].kind
            if occurrence.role == "container" and entity_kind == "ssa":
                raise TraceValidationError(
                    "SSA entities cannot own container intervals"
                )
            if occurrence.role != "container" and entity_kind != "ssa":
                raise TraceValidationError(
                    "only SSA entities can own interactive intervals"
                )
            if occurrence.role != "container":
                interactive_by_snapshot.setdefault(snapshot.id, []).append(
                    (occurrence.start, occurrence.end)
                )
            occurrence_bindings.append(occurrence_id)

        for metadata_id in snapshot.metadata_ids:
            _require_reference(metadata_id, metadata, "snapshot metadata")
            record = metadata[metadata_id]
            if record.snapshot_id != snapshot.id:
                raise TraceValidationError("metadata snapshot binding is invalid")
            if record.owner_entity_id not in snapshot.entity_ids:
                raise TraceValidationError("metadata owner is absent from its snapshot")
            if not record.namespace:
                raise TraceValidationError("metadata namespace must be nonempty")
            if record.presence == "present" and record.value is None:
                raise TraceValidationError("present metadata requires a value")
            if record.presence == "absent" and record.value is not None:
                raise TraceValidationError("absent metadata cannot have a value")
            if record.presence not in {"present", "absent"}:
                raise TraceValidationError("unknown metadata presence")
            if record.value is not None:
                if not record.value.qualified_type:
                    raise TraceValidationError(
                        "rendered metadata type must be nonempty"
                    )
                if record.value.path not in {"printable", "repr"}:
                    raise TraceValidationError("unknown metadata render path")
            metadata_bindings.append(metadata_id)

    if used_configurations != set(configurations):
        raise TraceValidationError("capture configurations cannot be orphaned")
    if used_styles != set(styles):
        raise TraceValidationError("styles cannot be orphaned")
    if len(occurrence_bindings) != len(set(occurrence_bindings)) or set(
        occurrence_bindings
    ) != set(occurrences):
        raise TraceValidationError("each occurrence must have one snapshot binding")
    if len(metadata_bindings) != len(set(metadata_bindings)) or set(
        metadata_bindings
    ) != set(metadata):
        raise TraceValidationError(
            "each metadata record must have one snapshot binding"
        )

    for intervals in interactive_by_snapshot.values():
        intervals.sort()
        for previous, current in pairwise(intervals):
            if current[0] < previous[1]:
                raise TraceValidationError(
                    "interactive definition/reference intervals cannot overlap"
                )

    for index, operation in enumerate(trace.operations):
        if operation.sequence != index:
            raise TraceValidationError("operation sequence must match entry order")
        _require_reference(operation.owner_event_id, events, "operation owner event")
        _require_reference(operation.invocation_stack_id, stacks, "operation stack")
        if operation.parent_operation_id is not None:
            _require_reference(
                operation.parent_operation_id, operations, "operation parent"
            )
            if int(operation.parent_operation_id.removeprefix("operation-")) >= index:
                raise TraceValidationError(
                    "operation parents must precede their children"
                )
            parent = operations[operation.parent_operation_id]
            if parent.owner_event_id != operation.owner_event_id:
                raise TraceValidationError(
                    "nested operations must belong to the same rewrite event"
                )
        if operation.api not in _RELATIONS_BY_API:
            raise TraceValidationError(f"unknown selected API: {operation.api!r}")
        if operation.outcome not in {"completed", "incomplete"}:
            raise TraceValidationError("unknown operation outcome")
        if len(operation.source_entity_ids) != len(
            set(operation.source_entity_ids)
        ) or len(operation.destination_entity_ids) != len(
            set(operation.destination_entity_ids)
        ):
            raise TraceValidationError("operation operands must be unique")
        for entity_id in operation.source_entity_ids + operation.destination_entity_ids:
            _require_reference(entity_id, entities, "operation operand")

    _validate_parent_graph(
        tuple((item.id, item.parent_operation_id) for item in trace.operations),
        "operation",
    )

    relations_by_operation: dict[str, list[ProvenanceRelation]] = {}
    for relation in trace.relations:
        _require_reference(
            relation.mutation_operation_id, operations, "relation operation"
        )
        _require_reference(relation.source_entity_id, entities, "relation source")
        _require_reference(
            relation.destination_entity_id, entities, "relation destination"
        )
        operation = operations[relation.mutation_operation_id]
        if operation.outcome != "completed":
            raise TraceValidationError("incomplete operations cannot own relations")
        if relation.basis not in _RELATIONS_BY_API[operation.api]:
            raise TraceValidationError("relation basis does not match its API")
        if relation.source_entity_id not in operation.source_entity_ids:
            raise TraceValidationError("relation source is not an operation source")
        if relation.destination_entity_id not in operation.destination_entity_ids:
            raise TraceValidationError(
                "relation destination is not an operation destination"
            )
        expected_source, expected_destination = _RELATION_KINDS[relation.basis]
        if (
            entities[relation.source_entity_id].kind != expected_source
            or entities[relation.destination_entity_id].kind != expected_destination
        ):
            raise TraceValidationError("relation endpoint kinds do not match its basis")
        relations_by_operation.setdefault(relation.mutation_operation_id, []).append(
            relation
        )

    effects_by_operation: dict[str, list[EntityEffect]] = {}
    for effect in trace.effects:
        _require_reference(effect.mutation_operation_id, operations, "effect operation")
        _require_reference(effect.affected_entity_id, entities, "effect entity")
        operation = operations[effect.mutation_operation_id]
        if (
            effect.kind != "statement_delete_completed"
            or operation.api != "Statement.delete"
            or operation.outcome != "completed"
        ):
            raise TraceValidationError("invalid completed deletion effect")
        if entities[effect.affected_entity_id].kind != "statement":
            raise TraceValidationError("deletion effects require statement entities")
        if effect.affected_entity_id not in operation.source_entity_ids:
            raise TraceValidationError(
                "effect entity is not an operation source operand"
            )
        effects_by_operation.setdefault(effect.mutation_operation_id, []).append(effect)

    for operation in trace.operations:
        if operation.outcome == "incomplete" and (
            relations_by_operation.get(operation.id)
            or effects_by_operation.get(operation.id)
        ):
            raise TraceValidationError(
                "incomplete operations cannot own relations or effects"
            )
        if (
            operation.outcome == "completed"
            and operation.api == "Statement.delete"
            and len(effects_by_operation.get(operation.id, ())) != 1
        ):
            raise TraceValidationError(
                "completed statement deletion requires exactly one effect"
            )

    used_stacks = {item.invocation_stack_id for item in trace.events}
    used_stacks.update(item.invocation_stack_id for item in trace.operations)
    if used_stacks != set(stacks):
        raise TraceValidationError("invocation stacks cannot be orphaned")


def _style_key(style: StyleRecord | None) -> object:
    if style is None:
        return None
    return (
        style.color,
        style.bgcolor,
        style.bold,
        style.dim,
        style.italic,
        style.underline,
        style.blink,
        style.blink2,
        style.reverse,
        style.conceal,
        style.strike,
        style.underline2,
        style.frame,
        style.encircle,
        style.overline,
        style.link,
        style.meta,
    )


def _snapshot_semantic_key(
    trace: Trace, index: TraceIndex, snapshot: Snapshot
) -> object:
    effective_styles: list[tuple[int, int, object]] = []
    for span in snapshot.style_spans:
        style = None if span.style_id is None else index.style(span.style_id)
        key = _style_key(style)
        if effective_styles and effective_styles[-1][2] == key:
            previous = effective_styles[-1]
            effective_styles[-1] = (previous[0], span.end, key)
        else:
            effective_styles.append((span.start, span.end, key))

    entity_values = tuple(
        (
            entity.id,
            entity.kind,
            entity.qualified_type,
            entity.defining_owner_id,
        )
        for entity in (index.entity(item_id) for item_id in snapshot.entity_ids)
    )
    occurrence_values = tuple(
        (
            occurrence.entity_id,
            occurrence.role,
            occurrence.start,
            occurrence.end,
        )
        for occurrence in (
            index.occurrence(item_id) for item_id in snapshot.occurrence_ids
        )
    )
    metadata_values = tuple(
        (
            record.owner_entity_id,
            record.namespace,
            record.key,
            record.presence,
            record.value,
        )
        for record in (
            index.metadata_record(item_id) for item_id in snapshot.metadata_ids
        )
    )
    configuration = index.configuration(snapshot.configuration_id)
    configuration_value = (
        configuration.kirin_commit,
        configuration.rich_version,
        configuration.theme,
        configuration.show_indent_mark,
        configuration.hint,
        configuration.printer_analysis,
        configuration.highlighter,
    )
    return (
        snapshot.schema_version,
        configuration_value,
        snapshot.root_entity_id,
        snapshot.text,
        tuple(effective_styles),
        entity_values,
        occurrence_values,
        metadata_values,
        snapshot.analysis_supplied,
    )
