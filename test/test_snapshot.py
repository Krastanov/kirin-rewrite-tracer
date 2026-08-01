from __future__ import annotations

from dataclasses import dataclass
from io import StringIO

import pytest
from kirin import ir, types
from kirin.dialects import func, module, py, scf
from kirin.print import Printable, Printer
from rich.style import Style

from kirin_rewrite_tracer._builder import _TraceBuilder
from kirin_rewrite_tracer._model import (
    FrameLocation,
    RewriteEvent,
    Snapshot,
)
from kirin_rewrite_tracer._snapshot import (
    SnapshotCaptureError,
    _SnapshotAdapter,
)

_KIRIN_COMMIT = "7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a"


class Pair(ir.Statement):
    name = "pair"


class LiteralPrint(ir.Statement):
    name = "literal"

    def __init__(self, text: str, *, style: Style | str | None = None) -> None:
        super().__init__()
        self.text = text
        self.style = style
        self.calls = 0

    def print_impl(self, printer: Printer) -> None:
        self.calls += 1
        printer.plain_print(  # type: ignore[no-untyped-call]
            self.text,
            style=self.style,
        )


class BypassPrint(ir.Statement):
    name = "bypass"

    def print_impl(self, printer: Printer) -> None:
        printer.console.file.write("unobserved")


class RawBypassPrint(ir.Statement):
    name = "raw_bypass"

    def print_impl(self, printer: Printer) -> None:
        StringIO.write(printer.console.file, "unobserved")  # type: ignore[arg-type]


class DirectConsolePrint(ir.Statement):
    name = "direct_console"

    def print_impl(self, printer: Printer) -> None:
        printer.console.print("unobserved")


@dataclass
class ReprOnly:
    text: str

    def __repr__(self) -> str:
        return self.text


def _capture(
    root: object,
    *,
    analysis: dict[ir.SSAValue, object] | None = None,
) -> tuple[_TraceBuilder, Snapshot]:
    builder = _TraceBuilder()
    configuration_id = builder.add_configuration(
        kirin_commit=_KIRIN_COMMIT,
        rich_version="15.0.0",
    )
    event_id = builder.next_id("event")
    snapshot_id = _SnapshotAdapter(
        builder,
        configuration_id,
        analysis,
    ).capture(root, event_id, "before")
    snapshot = next(item for item in builder.snapshots if item.id == snapshot_id)
    return builder, snapshot


def _entity_id(builder: _TraceBuilder, value: object) -> str:
    entity_id = builder.registry.lookup(value)
    assert entity_id is not None
    return entity_id


def _occurrences(
    builder: _TraceBuilder, snapshot: Snapshot, value: object
) -> list[tuple[str, int, int, str]]:
    entity_id = _entity_id(builder, value)
    return [
        (
            occurrence.role,
            occurrence.start,
            occurrence.end,
            snapshot.text[occurrence.start : occurrence.end],
        )
        for occurrence in builder.occurrences
        if occurrence.entity_id == entity_id
    ]


def test_multi_result_alignment_and_external_owner_are_exact() -> None:
    external = py.Constant(41)
    short = Pair(args=(external.result,), result_types=(types.Int,))
    long = Pair(args=(short.results[0],), result_types=(types.Int, types.Float))
    long.results[0].name = "substantially_long"
    block = ir.Block([short, long], argtypes=(types.Int,))
    root = ir.Region(block)

    builder, snapshot = _capture(root, analysis={external.result: False})

    assert snapshot.text == root.print_str(end="")
    short_definition = _occurrences(builder, snapshot, short.results[0])[0]
    assert short_definition[0] == "definition"
    assert short_definition[3].startswith("%")
    line_start = snapshot.text.rfind("\n", 0, short_definition[1]) + 1
    assert " " in snapshot.text[line_start : short_definition[1]]

    long_definitions = [
        item
        for result in long.results
        for item in _occurrences(builder, snapshot, result)
        if item[0] == "definition"
    ]
    assert len(long_definitions) == 2
    assert all(item[3].startswith("%") for item in long_definitions)
    assert _occurrences(builder, snapshot, external.result) == [
        (
            "reference",
            snapshot.text.index("pair(") + len("pair("),
            snapshot.text.index("pair(") + len("pair(") + 2,
            _occurrences(builder, snapshot, external.result)[0][3],
        )
    ]

    external_owner_id = _entity_id(builder, external)
    external_value = next(
        entity
        for entity in builder.entities
        if entity.id == _entity_id(builder, external.result)
    )
    assert external_owner_id in snapshot.entity_ids
    assert external_value.defining_owner_id == external_owner_id
    analysis_record = next(
        record
        for record in builder.metadata
        if record.owner_entity_id == external_value.id
        and record.namespace == "analysis"
    )
    assert analysis_record.value is not None
    assert analysis_record.value.text == "False"
    assert analysis_record.value.path == "repr"


def test_block_and_scf_for_definitions_are_not_references() -> None:
    iterable = py.Constant(range(3))
    initial = py.Constant(0)
    body = ir.Region(ir.Block())
    index = body.blocks[0].args.append_from(types.Int, "index")
    accumulator = body.blocks[0].args.append_from(types.Int, "acc")
    body.blocks[0].stmts.append(scf.Yield(index))
    loop = scf.For(iterable.result, body, initial.result)

    builder, snapshot = _capture(loop)

    assert snapshot.text == loop.print_str(end="")
    index_occurrences = _occurrences(builder, snapshot, index)
    assert [item[0] for item in index_occurrences] == ["definition", "reference"]
    assert len(_occurrences(builder, snapshot, accumulator)) == 1
    assert _occurrences(builder, snapshot, accumulator)[0][0] == "definition"
    assert _occurrences(builder, snapshot, iterable.result)[0][0] == "reference"
    assert _occurrences(builder, snapshot, initial.result)[0][0] == "reference"


def test_direct_func_id_is_a_reference_with_external_definition() -> None:
    function = func.Function(  # type: ignore[call-arg]
        sym_name="external",
        slots=(),
        signature=func.Signature(inputs=(), output=types.Int),
        body=ir.Region(ir.Block([func.Return()])),
    )
    argument = py.Constant(1)
    call = func.Call(  # type: ignore[call-arg]
        function.result,
        (argument.result,),
        (),
    )
    root = ir.Region(ir.Block([call]))

    builder, snapshot = _capture(root)

    callee_occurrences = _occurrences(builder, snapshot, function.result)
    assert len(callee_occurrences) == 1
    assert callee_occurrences[0][0] == "reference"
    assert callee_occurrences[0][3] in snapshot.text
    assert _entity_id(builder, function) in snapshot.entity_ids


def test_nested_module_direct_printing_gets_complete_containers() -> None:
    first_constant = py.Constant(1)
    first = func.Function(  # type: ignore[call-arg]
        sym_name="first",
        slots=(),
        signature=func.Signature(inputs=(), output=types.Int),
        body=ir.Region(ir.Block([first_constant, func.Return(first_constant)])),
    )
    second_constant = py.Constant(2)
    second = func.Function(  # type: ignore[call-arg]
        sym_name="second",
        slots=(),
        signature=func.Signature(inputs=(), output=types.Int),
        body=ir.Region(ir.Block([second_constant, func.Return(second_constant)])),
    )
    root = module.Module(
        sym_name="nested",
        entry="second",
        body=ir.Region(ir.Block([first, second])),
    )
    original_print = Printable.print

    builder, snapshot = _capture(root)

    assert Printable.print is original_print
    assert snapshot.text == root.print_str(end="")
    for statement in (root, first, second, first_constant, second_constant):
        containers = [
            item
            for item in _occurrences(builder, snapshot, statement)
            if item[0] == "container"
        ]
        assert len(containers) == 1
        assert containers[0][2] > containers[0][1]
    first_container = _occurrences(builder, snapshot, first)[0]
    assert "@first" in first_container[3]
    assert first_container[3].endswith("\n")


def test_root_is_evaluated_once_and_non_bmp_offsets_are_code_points() -> None:
    root = LiteralPrint("left 😀 right", style="bold red")

    builder, snapshot = _capture(root)

    assert root.calls == 1
    assert snapshot.text == "left 😀 right"
    assert len(snapshot.text) == 12
    assert snapshot.style_spans[0].start == 0
    assert snapshot.style_spans[-1].end == 12
    assert _occurrences(builder, snapshot, root) == [
        ("container", 0, 12, "left 😀 right")
    ]


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "root, message",
    [
        (LiteralPrint("before\rafter"), "control"),
        (BypassPrint(), "bypassed"),
        (RawBypassPrint(), "bypassed"),
        (DirectConsolePrint(), "bypassed"),
        (
            LiteralPrint("bad", style=Style(meta={"hostile": object()})),
            "metadata",
        ),
    ],
)
def test_unrepresentable_output_and_style_metadata_fail(
    root: ir.Statement, message: str
) -> None:
    original_print = Printable.print

    with pytest.raises(SnapshotCaptureError, match=message):
        _capture(root)

    assert Printable.print is original_print


def test_metadata_is_owner_specific_and_omission_is_explicit() -> None:
    source = py.Constant(7)
    source.result.name = "source"
    source.result.hints["hostile"] = ir.PyAttr("<script>&")
    user = Pair(args=(source.result,), result_types=(types.Int,))
    root = ir.Region(ir.Block([user]))

    builder, snapshot = _capture(
        root,
        analysis={
            source.result: False,
            user.results[0]: ReprOnly("<analysis>"),
        },
    )

    source_id = _entity_id(builder, source.result)
    source_records = [
        record for record in builder.metadata if record.owner_entity_id == source_id
    ]
    assert snapshot.analysis_supplied
    assert {(record.namespace, record.key) for record in source_records} == {
        ("ssa", "name"),
        ("ssa", "type"),
        ("hint", "hostile"),
        ("analysis", "value"),
    }
    hint_record = next(
        record
        for record in source_records
        if record.namespace == "hint" and record.value is not None
    )
    assert hint_record.value is not None
    assert hint_record.value.path == "printable"
    assert hint_record.value.text == "'<script>&' : !py.str"
    assert (
        next(
            record.value.text
            for record in source_records
            if record.namespace == "analysis" and record.value is not None
        )
        == "False"
    )

    omitted_builder, omitted = _capture(root)
    assert not omitted.analysis_supplied
    assert not any(
        record.namespace == "analysis" for record in omitted_builder.metadata
    )


def test_printable_metadata_ignores_ambient_forced_color(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    source = py.Constant(7)
    source.result.hints["forced-color"] = ir.PyAttr("plain metadata")

    builder, _ = _capture(source)

    hint = next(
        record
        for record in builder.metadata
        if record.owner_entity_id == _entity_id(builder, source.result)
        and record.namespace == "hint"
        and record.key == "forced-color"
    )
    assert hint.value is not None
    assert hint.value.path == "printable"
    assert hint.value.text == "'plain metadata' : !py.str"


def test_captured_facts_validate_as_an_immutable_incomplete_trace() -> None:
    root = ir.Region(ir.Block([py.Constant(1)]))
    builder, snapshot = _capture(root)
    stack_id = builder.add_stack((FrameLocation("fixture.py", 10, "rewrite"),))
    builder.events.append(
        RewriteEvent(
            id=snapshot.event_id,
            sequence=0,
            parent_id=None,
            sibling_ordinal=0,
            rule_type="fixture.Rule",
            completion="incomplete",
            root_entity_id=snapshot.root_entity_id,
            before_snapshot_id=snapshot.id,
            after_snapshot_id=None,
            invocation_stack_id=stack_id,
            result=None,
        )
    )

    trace = builder.freeze()

    assert not trace.complete
    assert trace.snapshots == (snapshot,)
    assert trace.index().snapshot(snapshot.id) is snapshot
    assert trace.snapshots[0].text == root.print_str(end="")
