from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from io import StringIO
from itertools import pairwise
from typing import Any, SupportsIndex, cast

from kirin import ir
from kirin.dialects.scf import For
from kirin.idtable import IdTable
from kirin.print import Printable, Printer
from rich.color import Color, ColorType
from rich.console import Console
from rich.segment import Segment
from rich.style import Style

from ._builder import _TraceBuilder
from ._model import (
    ColorRecord,
    EntityOccurrence,
    FrozenMap,
    MetadataRecord,
    RenderedValue,
    Snapshot,
    StyleRecord,
    StyleSpan,
    TraceValidationError,
    freeze_json,
)


class SnapshotCaptureError(TraceValidationError):
    """A pinned printer path cannot be represented without losing information."""


_CONTROL_CODEPOINTS = frozenset((*range(0x20), *range(0x7F, 0xA0))) - {
    ord("\t"),
    ord("\n"),
}


def _ensure_safe_text(value: str, description: str) -> None:
    if any(ord(character) in _CONTROL_CODEPOINTS for character in value):
        raise SnapshotCaptureError(f"{description} contains an unsupported control")


def _qualified_type(value: object) -> str:
    try:
        value_type = type(value)
        module = value_type.__module__
        qualname = value_type.__qualname__
    except Exception as error:
        raise SnapshotCaptureError(
            "a qualified type label could not be read"
        ) from error
    if (
        type(module) is not str
        or type(qualname) is not str
        or not module
        or not qualname
    ):
        raise SnapshotCaptureError("a qualified type label is not a nonempty string")
    label = f"{module}.{qualname}"
    _ensure_safe_text(label, "qualified type label")
    return label


@dataclass(frozen=True, slots=True)
class _Tag:
    value: ir.SSAValue
    role: str
    start: int
    end: int


class _TaggedId(str):
    value: ir.SSAValue
    role: str

    def __new__(
        cls, text: str, value: ir.SSAValue, role: str = "reference"
    ) -> _TaggedId:
        instance = super().__new__(cls, text)
        instance.value = value
        instance.role = role
        return instance


class _TaggedBlockId(str):
    value: ir.Block

    def __new__(cls, text: str, value: ir.Block) -> _TaggedBlockId:
        instance = super().__new__(cls, text)
        instance.value = value
        return instance


class _TaggedText(str):
    tags: tuple[_Tag, ...]

    def __new__(cls, text: str, tags: Sequence[_Tag] = ()) -> _TaggedText:
        instance = super().__new__(cls, text)
        instance.tags = tuple(tags)
        return instance

    def rjust(self, width: SupportsIndex, fillchar: str = " ") -> _TaggedText:
        result = super().rjust(width, fillchar)
        shift = len(result) - len(self)
        return _TaggedText(
            result,
            tuple(
                _Tag(tag.value, tag.role, tag.start + shift, tag.end + shift)
                for tag in self.tags
            ),
        )


class _TaggedIdTable(IdTable[ir.SSAValue]):
    def __init__(self, printer: _CapturePrinter, *, prefix: str = "%") -> None:
        super().__init__(prefix=prefix)
        self._printer = printer

    def __getitem__(self, value: ir.SSAValue) -> str:
        text = super().__getitem__(value)
        return _TaggedId(text, value, self._printer._take_lookup_role(value))


class _TaggedBlockIdTable(IdTable[ir.Block]):
    def __init__(self) -> None:
        super().__init__(prefix="^")

    def __getitem__(self, value: ir.Block) -> str:
        return _TaggedBlockId(super().__getitem__(value), value)


@dataclass(frozen=True, slots=True)
class _RenderedChunk:
    text: str
    style_id: str | None


class _GuardedSink(StringIO):
    """Accept visible writes only while the pinned ``Console.out`` path owns them."""

    __slots__ = ("permitted",)

    def __init__(self) -> None:
        super().__init__()
        self.permitted = False

    def write(self, value: str) -> int:
        if not self.permitted:
            raise SnapshotCaptureError("visible output bypassed Console.out")
        return super().write(value)


class _RecordingConsole(Console):
    def __init__(
        self,
        sink: _GuardedSink,
        freeze_style: Callable[[Style], str],
    ) -> None:
        super().__init__(
            color_system=None,
            force_jupyter=False,
            force_terminal=False,
            file=sink,
            highlight=True,
            record=True,
            width=1_000_000,
        )
        self._snapshot_sink = sink
        self._freeze_style = freeze_style
        self.snapshot_chunks: list[_RenderedChunk] = []
        self.snapshot_length = 0

    def out(
        self,
        *objects: Any,
        sep: str = " ",
        end: str = "\n",
        style: str | Style | None = None,
        highlight: bool | None = None,
    ) -> None:
        raw_output = sep.join(str(item) for item in objects)
        _ensure_safe_text(raw_output, "printer output")
        _ensure_safe_text(end, "printer output terminator")

        record_buffer = self._record_buffer
        start = len(record_buffer)
        outer = self.file is self._snapshot_sink
        self._snapshot_sink.permitted = outer
        rendered: tuple[Segment, ...]
        try:
            super().out(
                raw_output,
                sep="",
                end=end,
                style=style,
                highlight=highlight,
            )
        finally:
            self._snapshot_sink.permitted = False
            with self._record_buffer_lock:
                rendered = tuple(record_buffer[start:])
                del record_buffer[start:]
        if "".join(segment.text for segment in rendered) != raw_output + end:
            raise SnapshotCaptureError(
                "Rich rendered text differs from the delegated Console.out input"
            )
        if outer:
            for segment in rendered:
                if segment.control:
                    raise SnapshotCaptureError(
                        "Rich emitted an unsupported control segment"
                    )
                _ensure_safe_text(segment.text, "rendered printer output")
                style_id: str | None
                if segment.style is None:
                    style_id = None
                elif isinstance(segment.style, Style):
                    style_id = self._freeze_style(segment.style)
                else:
                    raise SnapshotCaptureError(
                        "Rich emitted an unsupported style object"
                    )
                self.snapshot_chunks.append(_RenderedChunk(segment.text, style_id))
                self.snapshot_length += len(segment.text)

    @property
    def snapshot_text(self) -> str:
        return "".join(chunk.text for chunk in self.snapshot_chunks)

    def discard_recorded_rich(self) -> None:
        self._record_buffer.clear()


class _Inventory:
    __slots__ = (
        "_builder",
        "_entity_ids",
        "_entity_set",
        "_ssa_set",
        "_statement_set",
        "_walked",
        "ssa_values",
        "statements",
    )

    def __init__(self, builder: _TraceBuilder) -> None:
        self._builder = builder
        self._entity_ids: list[str] = []
        self._entity_set: set[str] = set()
        self._walked: set[str] = set()
        self._ssa_set: set[str] = set()
        self._statement_set: set[str] = set()
        self.ssa_values: list[ir.SSAValue] = []
        self.statements: list[ir.Statement] = []

    @property
    def entity_ids(self) -> tuple[str, ...]:
        return tuple(self._entity_ids)

    def _remember(self, entity_id: str) -> str:
        if entity_id not in self._entity_set:
            self._entity_set.add(entity_id)
            self._entity_ids.append(entity_id)
        return entity_id

    def include_node(self, value: object) -> str:
        if isinstance(value, ir.SSAValue):
            return self.include_ssa(value)
        if isinstance(value, ir.Statement):
            kind = "statement"
        elif isinstance(value, ir.Region):
            kind = "region"
        elif isinstance(value, ir.Block):
            kind = "block"
        else:
            raise SnapshotCaptureError(
                f"unsupported captured entity type: {_qualified_type(value)}"
            )
        return self._remember(
            self._builder.register_entity(
                value,
                kind=kind,
                qualified_type=_qualified_type(value),
            )
        )

    def include_ssa(self, value: ir.SSAValue) -> str:
        try:
            owner = value.owner
        except Exception as error:
            raise SnapshotCaptureError(
                "an SSA defining owner could not be read"
            ) from error
        if not isinstance(owner, (ir.Statement, ir.Block)):
            raise SnapshotCaptureError("an SSA value has an unsupported defining owner")
        owner_id = self.include_node(owner)
        entity_id = self._remember(
            self._builder.register_entity(
                value,
                kind="ssa",
                qualified_type=_qualified_type(value),
                defining_owner_id=owner_id,
            )
        )
        if entity_id not in self._ssa_set:
            self._ssa_set.add(entity_id)
            self.ssa_values.append(value)
        return entity_id

    def entity_id(self, value: object) -> str:
        entity_id = self._builder.registry.lookup(value)
        if entity_id is None or entity_id not in self._entity_set:
            entity_id = self.include_node(value)
        return entity_id

    def walk(self, root: object) -> str:
        root_id = self.include_node(root)
        self._walk(root)
        return root_id

    def _walk(self, value: object) -> None:
        entity_id = self.include_node(value)
        if entity_id in self._walked:
            return
        self._walked.add(entity_id)

        if isinstance(value, ir.Statement):
            if entity_id not in self._statement_set:
                self._statement_set.add(entity_id)
                self.statements.append(value)
            for result in value.results:
                self.include_ssa(result)
            for argument in value.args:
                self.include_ssa(argument)
            for successor in value.successors:
                self.include_node(successor)
            for region in value.regions:
                self._walk(region)
        elif isinstance(value, ir.Region):
            for block in value.blocks:
                self._walk(block)
        elif isinstance(value, ir.Block):
            for argument in value.args:
                self.include_ssa(argument)
            for statement in value.stmts:
                self._walk(statement)


class _CapturePrinter(Printer):
    def __init__(self, console: _RecordingConsole, inventory: _Inventory) -> None:
        super().__init__(
            console=console,
            analysis=None,
            hint=None,
            show_indent_mark=True,
            theme="dark",
        )
        self._capture_console = console
        self._inventory = inventory
        self._definition_lookups: list[Counter[int]] = []
        self._hidden_tags: list[list[_Tag]] = []
        self._hidden_lengths: list[int] = []
        self._occurrences: list[tuple[object, str, int, int]] = []
        self._scoped_statements: list[ir.Statement] = []
        self.state.ssa_id = _TaggedIdTable(self)
        self.state.block_id = _TaggedBlockIdTable()

    @property
    def occurrences(self) -> tuple[tuple[object, str, int, int], ...]:
        return tuple(self._occurrences)

    def _take_lookup_role(self, value: ir.SSAValue) -> str:
        marker = id(value)
        for pending in reversed(self._definition_lookups):
            count = pending[marker]
            if count:
                pending[marker] = count - 1
                return "definition"
        return "reference"

    @contextmanager
    def _definition_scope(self, values: Sequence[ir.SSAValue]) -> Iterator[None]:
        pending = Counter(id(value) for value in values)
        self._definition_lookups.append(pending)
        try:
            yield
        finally:
            self._definition_lookups.pop()

    @contextmanager
    def _container_scope(self, value: object) -> Iterator[None]:
        start = self._capture_console.snapshot_length
        try:
            yield
        finally:
            end = self._capture_console.snapshot_length
            self._inventory.entity_id(value)
            self._occurrences.append((value, "container", start, end))

    @contextmanager
    def _direct_scope(self, value: object) -> Iterator[None]:
        definitions: Sequence[ir.SSAValue] = ()
        if isinstance(value, ir.Block):
            definitions = tuple(value.args)
        elif isinstance(value, For):
            definitions = tuple(value.body.blocks[0].args)

        if isinstance(value, (ir.Statement, ir.Region, ir.Block)):
            with self._container_scope(value):
                if isinstance(value, ir.Statement):
                    self._scoped_statements.append(value)
                try:
                    with self._definition_scope(definitions):
                        yield
                finally:
                    if isinstance(value, ir.Statement):
                        self._scoped_statements.pop()
        else:
            yield

    def print(self, object: object) -> None:
        if isinstance(object, ir.Block):
            with (
                self._container_scope(object),
                self._definition_scope(tuple(object.args)),
            ):
                super().print(object)  # type: ignore[no-untyped-call]
            return
        if isinstance(object, ir.Region):
            with self._container_scope(object):
                super().print(object)  # type: ignore[no-untyped-call]
            return
        if isinstance(object, ir.Statement):
            if any(statement is object for statement in self._scoped_statements):
                super().print(object)  # type: ignore[no-untyped-call]
                return
            with self._container_scope(object):
                self._scoped_statements.append(object)
                try:
                    definitions = (
                        tuple(object.body.blocks[0].args)
                        if isinstance(object, For)
                        else ()
                    )
                    with self._definition_scope(definitions):
                        super().print(object)  # type: ignore[no-untyped-call]
                finally:
                    self._scoped_statements.pop()
            return
        super().print(object)  # type: ignore[no-untyped-call]

    def print_stmt(self, node: ir.Statement) -> None:
        with self._container_scope(node):
            self._scoped_statements.append(node)
            try:
                super().print_stmt(node)
            finally:
                self._scoped_statements.pop()

    def plain_print(
        self,
        *objects: object,
        sep: str = "",
        end: str = "",
        style: str | Style | None = None,
        highlight: bool | None = None,
    ) -> None:
        converted: list[str] = []
        relative_tags: list[_Tag] = []
        cursor = 0
        for index, item in enumerate(objects):
            if index:
                cursor += len(sep)
            text = str(item)
            converted.append(text)
            if isinstance(item, _TaggedId):
                relative_tags.append(
                    _Tag(item.value, item.role, cursor, cursor + len(text))
                )
            elif isinstance(item, _TaggedText):
                relative_tags.extend(
                    _Tag(
                        tag.value,
                        tag.role,
                        tag.start + cursor,
                        tag.end + cursor,
                    )
                    for tag in item.tags
                )
            elif isinstance(item, _TaggedBlockId):
                self._inventory.entity_id(item.value)
            cursor += len(text)

        raw_length = cursor + len(end)
        if self.console.file is self._capture_console._snapshot_sink:
            start = self._capture_console.snapshot_length
            super().plain_print(  # type: ignore[no-untyped-call]
                *converted,
                sep=sep,
                end=end,
                style=style,
                highlight=highlight,
            )
            for tag in relative_tags:
                self._occurrences.append(
                    (
                        tag.value,
                        tag.role,
                        start + tag.start,
                        start + tag.end,
                    )
                )
            return

        if self._hidden_tags:
            hidden_start = self._hidden_lengths[-1]
            self._hidden_tags[-1].extend(
                _Tag(
                    tag.value,
                    tag.role,
                    hidden_start + tag.start,
                    hidden_start + tag.end,
                )
                for tag in relative_tags
            )
            self._hidden_lengths[-1] += raw_length
        super().plain_print(  # type: ignore[no-untyped-call]
            *converted,
            sep=sep,
            end=end,
            style=style,
            highlight=highlight,
        )

    def result_str(self, results: list[ir.ResultValue]) -> str:
        tags: list[_Tag] = []
        self._hidden_tags.append(tags)
        self._hidden_lengths.append(0)
        try:
            text = super().result_str(results)
        finally:
            self._hidden_lengths.pop()
            self._hidden_tags.pop()
        return _TaggedText(
            text,
            tuple(_Tag(tag.value, "definition", tag.start, tag.end) for tag in tags),
        )

    def direct_print(
        self,
        value: Printable,
        *,
        end: str,
        options: Mapping[str, object],
        delegate: Callable[..., None],
    ) -> None:
        with self._direct_scope(value):
            delegate(value, self, end=end, **options)


def _freeze_color(color: Color | None) -> ColorRecord | None:
    if color is None:
        return None
    encoding = {
        ColorType.DEFAULT: "default",
        ColorType.STANDARD: "standard",
        ColorType.EIGHT_BIT: "eight_bit",
        ColorType.TRUECOLOR: "truecolor",
        ColorType.WINDOWS: "windows",
    }.get(color.type)
    if encoding is None:
        raise SnapshotCaptureError("Rich produced an unsupported color encoding")
    _ensure_safe_text(color.name, "Rich color name")
    triplet = (
        None
        if color.triplet is None
        else (color.triplet.red, color.triplet.green, color.triplet.blue)
    )
    return ColorRecord(encoding, color.name, color.number, triplet)


def _validate_meta_text(value: object, active: set[int] | None = None) -> None:
    if type(value) is str:
        _ensure_safe_text(value, "Rich style metadata")
        return
    if type(value) is list:
        seen = set() if active is None else active
        marker = id(value)
        if marker in seen:
            raise SnapshotCaptureError("Rich style metadata contains a cycle")
        seen.add(marker)
        try:
            for item in cast(list[object], value):
                _validate_meta_text(item, seen)
        finally:
            seen.remove(marker)
        return
    if type(value) is dict:
        seen = set() if active is None else active
        marker = id(value)
        if marker in seen:
            raise SnapshotCaptureError("Rich style metadata contains a cycle")
        seen.add(marker)
        try:
            for key, item in cast(dict[object, object], value).items():
                if type(key) is str:
                    _ensure_safe_text(key, "Rich style metadata key")
                _validate_meta_text(item, seen)
        finally:
            seen.remove(marker)


def _freeze_style(style: Style) -> StyleRecord:
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
        if value is not None and type(value) is not bool:
            raise SnapshotCaptureError(f"Rich style {name} is not tri-state")
    if style.link is not None:
        if type(style.link) is not str:
            raise SnapshotCaptureError("Rich style link is not a string")
        _ensure_safe_text(style.link, "Rich style link")
    if type(style.meta) is not dict:
        raise SnapshotCaptureError("Rich style metadata is not an ordered map")
    _validate_meta_text(style.meta)
    try:
        meta = freeze_json(style.meta)
    except TraceValidationError as error:
        raise SnapshotCaptureError("Rich style metadata is unsupported") from error
    if not isinstance(meta, FrozenMap):
        raise SnapshotCaptureError("Rich style metadata did not freeze as a map")
    return StyleRecord(
        id="",
        color=_freeze_color(style.color),
        bgcolor=_freeze_color(style.bgcolor),
        bold=style.bold,
        dim=style.dim,
        italic=style.italic,
        underline=style.underline,
        blink=style.blink,
        blink2=style.blink2,
        reverse=style.reverse,
        conceal=style.conceal,
        strike=style.strike,
        underline2=style.underline2,
        frame=style.frame,
        encircle=style.encircle,
        overline=style.overline,
        link=style.link,
        meta=meta,
    )


def _render_metadata(value: object) -> RenderedValue:
    qualified_type = _qualified_type(value)
    if isinstance(value, Printable):
        try:
            rendered = value.print_str(end="")
        except Exception:
            pass
        else:
            if type(rendered) is str:
                _ensure_safe_text(rendered, "printable metadata text")
                return RenderedValue(qualified_type, rendered, "printable")
    try:
        rendered = repr(value)
    except Exception as error:
        raise SnapshotCaptureError("a metadata value has no representation") from error
    if type(rendered) is not str:
        raise SnapshotCaptureError("repr() did not return a string")
    _ensure_safe_text(rendered, "repr metadata text")
    return RenderedValue(qualified_type, rendered, "repr")


class _SnapshotAdapter:
    """Pinned Kirin/Rich snapshot boundary used only while a recorder is active."""

    __slots__ = ("_analysis", "_builder", "_configuration_id")

    def __init__(
        self,
        builder: _TraceBuilder,
        configuration_id: str,
        analysis: Mapping[ir.SSAValue, object] | None,
    ) -> None:
        self._builder = builder
        self._configuration_id = configuration_id
        self._analysis = analysis

    def capture(self, root: object, event_id: str, state: str) -> str:
        if state not in {"before", "after"}:
            raise SnapshotCaptureError(f"unsupported snapshot state: {state!r}")

        inventory = _Inventory(self._builder)
        root_id = inventory.walk(root)
        sink = _GuardedSink()
        console = _RecordingConsole(
            sink,
            lambda style: self._builder.intern_style(_freeze_style(style)),
        )
        capture_printer = _CapturePrinter(console, inventory)

        original_print = cast(Callable[..., None], vars(Printable)["print"])

        def capture_print(
            value: Printable,
            printer: Printer | None = None,
            end: str = "\n",
            **options: object,
        ) -> None:
            if printer is capture_printer:
                capture_printer.direct_print(
                    value,
                    end=end,
                    options=options,
                    delegate=original_print,
                )
                return
            original_print(value, printer, end=end, **options)

        Printable.print = capture_print  # type: ignore[assignment]
        rendering_error: BaseException | None = None
        try:
            cast(Printable, root).print(capture_printer, end="")
        except BaseException as error:
            rendering_error = error
        finally:
            if vars(Printable).get("print") is capture_print:
                Printable.print = original_print  # type: ignore[method-assign]
            elif rendering_error is None:
                rendering_error = SnapshotCaptureError(
                    "Printable.print changed during snapshot capture"
                )

        console.discard_recorded_rich()
        if rendering_error is not None:
            if isinstance(rendering_error, SnapshotCaptureError):
                raise rendering_error
            if isinstance(rendering_error, Exception):
                raise SnapshotCaptureError("the pinned printer execution failed") from (
                    rendering_error
                )
            raise rendering_error

        text = console.snapshot_text
        if sink.getvalue() != text:
            raise SnapshotCaptureError("visible output bypassed Console.out")

        snapshot_id = self._builder.next_id("snapshot")
        style_spans = self._style_spans(console.snapshot_chunks)
        occurrence_ids = self._append_occurrences(
            snapshot_id, text, inventory, capture_printer.occurrences
        )
        metadata_ids = self._append_metadata(snapshot_id, inventory)
        self._builder.snapshots.append(
            Snapshot(
                id=snapshot_id,
                event_id=event_id,
                state=state,
                schema_version=1,
                configuration_id=self._configuration_id,
                root_entity_id=root_id,
                text=text,
                style_spans=style_spans,
                entity_ids=inventory.entity_ids,
                occurrence_ids=occurrence_ids,
                metadata_ids=metadata_ids,
                analysis_supplied=self._analysis is not None,
            )
        )
        return snapshot_id

    def _style_spans(self, chunks: Sequence[_RenderedChunk]) -> tuple[StyleSpan, ...]:
        spans: list[StyleSpan] = []
        cursor = 0
        for chunk in chunks:
            if not chunk.text:
                continue
            style_id = chunk.style_id
            end = cursor + len(chunk.text)
            if spans and spans[-1].style_id == style_id:
                previous = spans[-1]
                spans[-1] = StyleSpan(previous.start, end, style_id)
            else:
                spans.append(StyleSpan(cursor, end, style_id))
            cursor = end
        return tuple(spans)

    def _append_occurrences(
        self,
        snapshot_id: str,
        text: str,
        inventory: _Inventory,
        occurrences: Sequence[tuple[object, str, int, int]],
    ) -> tuple[str, ...]:
        interactive: list[tuple[int, int]] = []
        occurrence_ids: list[str] = []
        for value, role, start, end in occurrences:
            if start < 0 or end < start or end > len(text):
                raise SnapshotCaptureError("a rendered entity interval is invalid")
            if role != "container" and start == end:
                raise SnapshotCaptureError("an interactive interval is empty")
            if role != "container":
                interactive.append((start, end))
            occurrence_id = self._builder.next_id("occurrence")
            self._builder.occurrences.append(
                EntityOccurrence(
                    id=occurrence_id,
                    snapshot_id=snapshot_id,
                    entity_id=inventory.entity_id(value),
                    role=role,
                    start=start,
                    end=end,
                )
            )
            occurrence_ids.append(occurrence_id)
        interactive.sort()
        for previous, current in pairwise(interactive):
            if current[0] < previous[1]:
                raise SnapshotCaptureError(
                    "interactive definition/reference intervals overlap"
                )
        return tuple(occurrence_ids)

    def _append_metadata(
        self, snapshot_id: str, inventory: _Inventory
    ) -> tuple[str, ...]:
        metadata_ids: list[str] = []

        def append(
            owner: object,
            namespace: str,
            key: str,
            value: object | None,
            *,
            absent: bool = False,
        ) -> None:
            _ensure_safe_text(namespace, "metadata namespace")
            _ensure_safe_text(key, "metadata key")
            metadata_id = self._builder.next_id("metadata")
            self._builder.metadata.append(
                MetadataRecord(
                    id=metadata_id,
                    snapshot_id=snapshot_id,
                    owner_entity_id=inventory.entity_id(owner),
                    namespace=namespace,
                    key=key,
                    presence="absent" if absent else "present",
                    value=None if absent else _render_metadata(value),
                )
            )
            metadata_ids.append(metadata_id)

        for statement in inventory.statements:
            try:
                attributes = statement.attributes
            except Exception as error:
                raise SnapshotCaptureError(
                    "statement attributes could not be read"
                ) from error
            for key, attribute in attributes.items():
                if type(key) is not str:
                    raise SnapshotCaptureError(
                        "statement attribute keys must be strings"
                    )
                append(statement, "attribute", key, attribute)

        for ssa_value in inventory.ssa_values:
            try:
                name = ssa_value.name
                value_type = ssa_value.type
                hints = ssa_value.hints
            except Exception as error:
                raise SnapshotCaptureError("SSA metadata could not be read") from error
            if name is None:
                append(ssa_value, "ssa", "name", None, absent=True)
            elif type(name) is str:
                append(ssa_value, "ssa", "name", name)
            else:
                raise SnapshotCaptureError("SSA name must be a string or absent")
            append(ssa_value, "ssa", "type", value_type)
            for key, hint in hints.items():
                if type(key) is not str:
                    raise SnapshotCaptureError("SSA hint keys must be strings")
                append(ssa_value, "hint", key, hint)
            if self._analysis is not None and ssa_value in self._analysis:
                append(
                    ssa_value,
                    "analysis",
                    "value",
                    self._analysis[ssa_value],
                )
        return tuple(metadata_ids)
