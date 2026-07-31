from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from ._model import (
    CaptureConfiguration,
    EntityEffect,
    EntityOccurrence,
    FrameLocation,
    InvocationStack,
    MetadataRecord,
    MutationOperation,
    ProvenanceRelation,
    RewriteEvent,
    Snapshot,
    StyleRecord,
    Trace,
    TraceEntity,
    TraceValidationError,
)

_DOMAINS = {
    "configuration",
    "style",
    "entity",
    "snapshot",
    "occurrence",
    "metadata",
    "stack",
    "event",
    "operation",
    "relation",
    "effect",
}


class _IdAllocator:
    __slots__ = ("_next",)

    def __init__(self) -> None:
        self._next = {domain: 0 for domain in _DOMAINS}

    def allocate(self, domain: str) -> str:
        if domain not in self._next:
            raise TraceValidationError(f"unknown ID domain: {domain!r}")
        value = self._next[domain]
        self._next[domain] = value + 1
        return f"{domain}-{value}"


class _EntityRegistry:
    """Identity registry that holds objects strongly only during capture."""

    __slots__ = ("_allocator", "_by_address", "_released")

    def __init__(self, allocator: _IdAllocator | None = None) -> None:
        self._allocator = _IdAllocator() if allocator is None else allocator
        self._by_address: dict[int, list[tuple[object, str]]] = {}
        self._released = False

    def register(self, value: object) -> tuple[str, bool]:
        if self._released:
            raise TraceValidationError("entity registry has been released")
        address = id(value)
        bucket = self._by_address.setdefault(address, [])
        for existing, entity_id in bucket:
            if existing is value:
                return entity_id, False
        entity_id = self._allocator.allocate("entity")
        bucket.append((value, entity_id))
        return entity_id, True

    def lookup(self, value: object) -> str | None:
        for existing, entity_id in self._by_address.get(id(value), ()):
            if existing is value:
                return entity_id
        return None

    def release(self) -> None:
        self._by_address.clear()
        self._released = True


class _TraceBuilder:
    """Mutable capture-only owner for facts that freeze into one Trace."""

    __slots__ = (
        "_allocator",
        "_entity_records",
        "_frozen",
        "_released",
        "_style_keys",
        "configurations",
        "effects",
        "entities",
        "events",
        "metadata",
        "occurrences",
        "operations",
        "registry",
        "relations",
        "snapshots",
        "stacks",
        "styles",
    )

    def __init__(self) -> None:
        self._allocator = _IdAllocator()
        self.registry = _EntityRegistry(self._allocator)
        self.configurations: list[CaptureConfiguration] = []
        self.styles: list[StyleRecord] = []
        self.entities: list[TraceEntity] = []
        self.snapshots: list[Snapshot] = []
        self.occurrences: list[EntityOccurrence] = []
        self.metadata: list[MetadataRecord] = []
        self.stacks: list[InvocationStack] = []
        self.events: list[RewriteEvent] = []
        self.operations: list[MutationOperation] = []
        self.relations: list[ProvenanceRelation] = []
        self.effects: list[EntityEffect] = []
        self._style_keys: dict[tuple[object, ...], str] = {}
        self._entity_records: dict[str, TraceEntity] = {}
        self._frozen: Trace | None = None
        self._released = False

    def next_id(self, domain: str) -> str:
        if self._frozen is not None or self._released:
            raise TraceValidationError("trace builder is no longer mutable")
        return self._allocator.allocate(domain)

    def register_entity(
        self,
        value: object,
        *,
        kind: str,
        qualified_type: str,
        defining_owner_id: str | None = None,
    ) -> str:
        entity_id, created = self.registry.register(value)
        record = TraceEntity(
            id=entity_id,
            kind=kind,
            qualified_type=qualified_type,
            defining_owner_id=defining_owner_id,
        )
        if created:
            self.entities.append(record)
            self._entity_records[entity_id] = record
        elif self._entity_records[entity_id] != record:
            raise TraceValidationError(
                "one live entity was registered with inconsistent facts"
            )
        return entity_id

    def intern_style(self, candidate: StyleRecord) -> str:
        if candidate.id:
            raise TraceValidationError(
                "a style candidate must not carry a persistent ID"
            )
        key = (
            candidate.color,
            candidate.bgcolor,
            candidate.bold,
            candidate.dim,
            candidate.italic,
            candidate.underline,
            candidate.blink,
            candidate.blink2,
            candidate.reverse,
            candidate.conceal,
            candidate.strike,
            candidate.underline2,
            candidate.frame,
            candidate.encircle,
            candidate.overline,
            candidate.link,
            candidate.meta,
        )
        existing = self._style_keys.get(key)
        if existing is not None:
            return existing
        style_id = self.next_id("style")
        style = replace(candidate, id=style_id)
        self.styles.append(style)
        self._style_keys[key] = style_id
        return style_id

    def add_configuration(
        self,
        *,
        kirin_commit: str,
        rich_version: str,
        theme: str = "dark",
        show_indent_mark: bool = True,
        hint: str | None = None,
        printer_analysis: bool = False,
        highlighter: str = "rich.default",
    ) -> str:
        configuration_id = self.next_id("configuration")
        self.configurations.append(
            CaptureConfiguration(
                id=configuration_id,
                kirin_commit=kirin_commit,
                rich_version=rich_version,
                theme=theme,
                show_indent_mark=show_indent_mark,
                hint=hint,
                printer_analysis=printer_analysis,
                highlighter=highlighter,
            )
        )
        return configuration_id

    def add_stack(self, frames: Iterable[FrameLocation]) -> str:
        stack_id = self.next_id("stack")
        self.stacks.append(InvocationStack(stack_id, tuple(frames)))
        return stack_id

    def freeze(self, *, complete: bool | None = None) -> Trace:
        if self._frozen is not None:
            return self._frozen
        if self._released:
            raise TraceValidationError("released builder cannot be frozen")
        aggregate_complete = (
            all(item.completion == "complete" for item in self.events)
            if complete is None
            else complete
        )
        try:
            trace = Trace(
                schema_version=1,
                complete=aggregate_complete,
                configurations=tuple(self.configurations),
                styles=tuple(self.styles),
                entities=tuple(self.entities),
                snapshots=tuple(self.snapshots),
                occurrences=tuple(self.occurrences),
                metadata=tuple(self.metadata),
                stacks=tuple(self.stacks),
                events=tuple(self.events),
                operations=tuple(self.operations),
                relations=tuple(self.relations),
                effects=tuple(self.effects),
            )
        finally:
            self.registry.release()
            self._released = True
        self._frozen = trace
        return trace

    def release(self) -> None:
        if not self._released:
            self.registry.release()
            self._released = True
