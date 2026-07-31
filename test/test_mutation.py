from __future__ import annotations

import sys
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from types import FrameType, FunctionType
from typing import ClassVar, NoReturn, cast

import pytest
from kirin.ir import Block, Region, SSAValue, Statement
from kirin.ir.attrs.abc import Attribute
from kirin.ir.attrs.types import AnyType
from kirin.ir.ssa import TestValue as _KirinTestValue

from kirin_rewrite_tracer._builder import _TraceBuilder
from kirin_rewrite_tracer._mutation import (
    _BuilderMutationRecorder,
    _MutationInterceptors,
)


class _Unsupported(RuntimeError):
    pass


@dataclass
class _Capture:
    active_event: str | None = "event-0"
    builder: _TraceBuilder = field(init=False)
    error: _Unsupported = field(init=False)
    reasons: list[str] = field(init=False)
    interceptor: _MutationInterceptors = field(init=False)

    def __post_init__(self) -> None:
        self.builder = _TraceBuilder()
        self.error = _Unsupported("unsupported selected mutation")
        self.reasons = []
        recorder = _BuilderMutationRecorder(
            self.builder,
            active_event_id=lambda: self.active_event,
            invalidate=self._invalidate,
            mark_invalid=self._mark_invalid,
        )
        self.interceptor = _MutationInterceptors(recorder)

    def _invalidate(self, reason: str) -> NoReturn:
        self.reasons.append(reason)
        raise self.error

    def _mark_invalid(self, reason: str) -> None:
        self.reasons.append(reason)

    def _profile(self, frame: FrameType, event: str, _arg: object) -> None:
        if event == "call":
            self.interceptor.authorize_profile_call(frame)

    @contextmanager
    def installed(self, *, profile: bool = True) -> Iterator[None]:
        assert sys.getprofile() is None
        self.interceptor.install()
        if profile:
            sys.setprofile(self._profile)
        try:
            yield
        finally:
            sys.setprofile(None)
            self.interceptor.uninstall()


class _PlainStatement(Statement):
    name = "test.plain"


class _DerivedStatement(_PlainStatement):
    name = "test.derived"


_HOSTILE_RESULT_READS: list[Statement] = []


class _HostileResultsStatement(_PlainStatement):
    name = "test.hostile_results"

    @property
    def results(self) -> object:  # type: ignore[override]
        _HOSTILE_RESULT_READS.append(self)
        raise AssertionError("capture-only results projection ran")


class _MutatingCloneStatement(_PlainStatement):
    name = "test.mutating_clone"
    source_block: ClassVar[Block | None] = None

    @classmethod
    def from_stmt(
        cls,
        other: Statement,
        args: Sequence[SSAValue] | None = None,
        regions: list[Region] | None = None,
        successors: list[Block] | None = None,
        attributes: dict[str, Attribute] | None = None,
    ) -> _MutatingCloneStatement:
        source_block = cls.source_block
        assert source_block is not None
        source_block.args.append_from(AnyType())
        return super().from_stmt(
            other,
            args=args,
            regions=regions,
            successors=successors,
            attributes=attributes,
        )


_SENTINEL = RuntimeError("sentinel")


class _ExplodingStatement(_PlainStatement):
    name = "test.exploding"
    explode = False

    def detach(self) -> None:
        if self.explode:
            raise _SENTINEL
        super().detach()


def _operation_apis(capture: _Capture) -> list[str]:
    return [operation.api for operation in capture.builder.operations]


def _set_raw(owner: type[object], name: str, value: object) -> None:
    setattr(owner, name, value)


def test_installs_raw_descriptors_and_restores_exact_objects_in_reverse() -> None:
    targets = (
        (Statement, "replace_by"),
        (SSAValue, "replace_by"),
        (Statement, "from_stmt"),
        (Region, "clone"),
        (Statement, "delete"),
    )
    originals = tuple(vars(owner)[name] for owner, name in targets)
    capture = _Capture()

    with capture.installed():
        installed = tuple(vars(owner)[name] for owner, name in targets)
        assert installed == capture.interceptor.installed_descriptors
        assert type(vars(Statement)["from_stmt"]) is classmethod
        with pytest.raises(RuntimeError, match="already installed"):
            capture.interceptor.install()

    assert tuple(vars(owner)[name] for owner, name in targets) == originals


def test_partial_install_rolls_back_and_foreign_cleanup_is_not_clobbered() -> None:
    targets = (
        (Statement, "replace_by"),
        (SSAValue, "replace_by"),
        (Statement, "from_stmt"),
        (Region, "clone"),
        (Statement, "delete"),
    )
    originals = tuple(vars(owner)[name] for owner, name in targets)
    writes: list[tuple[type[object], str, object]] = []
    failure = RuntimeError("install failure")

    def fail_third(owner: type[object], name: str, value: object) -> None:
        writes.append((owner, name, value))
        if len(writes) == 3:
            raise failure
        setattr(owner, name, value)

    recorder = _BuilderMutationRecorder(
        _TraceBuilder(),
        active_event_id=lambda: None,
        invalidate=lambda _reason: _raise_unexpected(),
        mark_invalid=lambda _reason: None,
    )
    interceptor = _MutationInterceptors(recorder, set_attribute=fail_third)
    with pytest.raises(RuntimeError) as caught:
        interceptor.install()
    assert caught.value is failure
    assert tuple(vars(owner)[name] for owner, name in targets) == originals
    assert [(owner, name) for owner, name, _value in writes[-2:]] == [
        (SSAValue, "replace_by"),
        (Statement, "replace_by"),
    ]

    capture = _Capture()
    capture.interceptor.install()

    def foreign_delete(self: Statement, safe: bool = True) -> None:
        del self, safe

    try:
        _set_raw(Statement, "delete", foreign_delete)
        capture.interceptor.uninstall()
        assert vars(Statement)["delete"] is foreign_delete
        assert tuple(vars(owner)[name] for owner, name in targets[:4]) == originals[:4]
        assert capture.reasons == ["Statement.delete was replaced while tracing"]
    finally:
        _set_raw(Statement, "delete", originals[4])


@pytest.mark.parametrize("failure_write", range(1, 6))  # type: ignore[untyped-decorator]
def test_every_partial_install_boundary_rolls_back(
    failure_write: int,
) -> None:
    targets = (
        (Statement, "replace_by"),
        (SSAValue, "replace_by"),
        (Statement, "from_stmt"),
        (Region, "clone"),
        (Statement, "delete"),
    )
    originals = tuple(vars(owner)[name] for owner, name in targets)
    writes = 0
    failure = RuntimeError(f"installation write {failure_write}")

    def fail_at_boundary(owner: type[object], name: str, value: object) -> None:
        nonlocal writes
        writes += 1
        if writes == failure_write:
            raise failure
        setattr(owner, name, value)

    recorder = _BuilderMutationRecorder(
        _TraceBuilder(),
        active_event_id=lambda: None,
        invalidate=lambda _reason: _raise_unexpected(),
        mark_invalid=lambda _reason: None,
    )
    interceptor = _MutationInterceptors(
        recorder,
        set_attribute=fail_at_boundary,
    )
    with pytest.raises(RuntimeError) as caught:
        interceptor.install()

    assert caught.value is failure
    assert tuple(vars(owner)[name] for owner, name in targets) == originals


def _raise_unexpected() -> NoReturn:
    raise AssertionError("unexpected invalidation")


def test_outside_event_delegates_all_five_apis_without_capture() -> None:
    capture = _Capture(active_event=None)
    with capture.installed():
        source = _PlainStatement(result_types=(AnyType(),))
        replacement = _PlainStatement(result_types=(AnyType(),))
        block = Block([source])
        source.replace_by(replacement)
        assert tuple(block.stmts) == (replacement,)

        source_value = _PlainStatement(result_types=(AnyType(),)).results[0]
        destination_value = _PlainStatement(result_types=(AnyType(),)).results[0]
        source_value.replace_by(destination_value)

        copied = _DerivedStatement.from_stmt(
            _DerivedStatement(result_types=(AnyType(),))
        )
        assert type(copied) is _DerivedStatement

        region = Region(Block(argtypes=(AnyType(),)))
        cloned = region.clone()
        assert cloned is not region

        doomed = _PlainStatement()
        Block([doomed])
        doomed.delete()

    assert capture.builder.operations == []
    assert capture.builder.relations == []
    assert capture.builder.effects == []
    assert capture.builder.stacks == []
    assert capture.builder.entities == []


def test_outside_event_never_evaluates_capture_only_operand_projections() -> None:
    _HOSTILE_RESULT_READS.clear()
    capture = _Capture(active_event=None)
    source = _HostileResultsStatement(result_types=(AnyType(),))

    with capture.installed():
        copied = _HostileResultsStatement.from_stmt(source)

    assert type(copied) is _HostileResultsStatement
    assert _HOSTILE_RESULT_READS == []
    assert capture.builder.operations == []
    assert capture.reasons == []


def test_projection_failures_stickily_invalidate_before_or_after_delegation() -> None:
    _HOSTILE_RESULT_READS.clear()
    before = _Capture()
    source = _HostileResultsStatement(result_types=(AnyType(),))

    with before.installed(), pytest.raises(_Unsupported) as before_error:
        _PlainStatement.from_stmt(source)

    assert before_error.value is before.error
    assert before.reasons == [
        "Statement.from_stmt pre-call capture failed: builtins.AssertionError"
    ]
    assert before.builder.operations == []
    assert [source] == _HOSTILE_RESULT_READS

    _HOSTILE_RESULT_READS.clear()
    after = _Capture()
    ordinary = _PlainStatement(result_types=(AnyType(),))

    with after.installed(), pytest.raises(_Unsupported) as after_error:
        _HostileResultsStatement.from_stmt(ordinary)

    assert after_error.value is after.error
    assert after.reasons == [
        "Statement.from_stmt post-call capture failed: builtins.AssertionError"
    ]
    assert [operation.outcome for operation in after.builder.operations] == [
        "incomplete"
    ]
    assert len(_HOSTILE_RESULT_READS) == 1
    assert isinstance(_HOSTILE_RESULT_READS[0], _HostileResultsStatement)
    assert after.interceptor._expected == []
    after_recorder = cast(
        _BuilderMutationRecorder,
        after.interceptor._recorder,
    )
    assert after_recorder._open == []


def test_unrepresentable_ssa_owner_invalidates_only_when_capture_is_active() -> None:
    outside = _Capture(active_event=None)
    with outside.installed():
        _KirinTestValue().replace_by(_KirinTestValue())
    assert outside.reasons == []
    assert outside.builder.operations == []

    active = _Capture()
    with active.installed(), pytest.raises(_Unsupported) as caught:
        _KirinTestValue().replace_by(_KirinTestValue())

    assert caught.value is active.error
    assert active.reasons == [
        "SSAValue.replace_by pre-call capture failed: builtins.NotImplementedError"
    ]
    assert active.builder.operations == []
    assert active.interceptor._expected == []


def test_statement_replacement_keeps_nested_operations_and_exact_facts() -> None:
    capture = _Capture()
    with capture.installed():
        source = _PlainStatement(result_types=(AnyType(),))
        replacement = _PlainStatement(result_types=(AnyType(),))
        block = Block([source])
        source.replace_by(replacement)

    assert tuple(block.stmts) == (replacement,)
    assert _operation_apis(capture) == [
        "Statement.replace_by",
        "SSAValue.replace_by",
        "Statement.delete",
        "SSAValue.replace_by",
    ]
    assert [
        operation.parent_operation_id for operation in capture.builder.operations
    ] == [None, "operation-0", "operation-0", "operation-2"]
    assert all(
        operation.outcome == "completed" for operation in capture.builder.operations
    )
    assert [
        (relation.basis, relation.mutation_operation_id)
        for relation in capture.builder.relations
    ] == [("statement_replaced_by", "operation-0")]
    replacement_relation = capture.builder.relations[0]
    assert replacement_relation.source_entity_id == capture.builder.registry.lookup(
        source
    )
    assert (
        replacement_relation.destination_entity_id
        == capture.builder.registry.lookup(replacement)
    )
    assert [
        (effect.kind, effect.mutation_operation_id)
        for effect in capture.builder.effects
    ] == [("statement_delete_completed", "operation-2")]
    assert capture.builder.effects[
        0
    ].affected_entity_id == capture.builder.registry.lookup(source)
    outer_stack = capture.builder.stacks[0]
    assert outer_stack.frames
    assert (
        outer_stack.frames[-1].function
        == "test_statement_replacement_keeps_nested_operations_and_exact_facts"
    )
    assert all(
        not frame.filename.endswith("/kirin_rewrite_tracer/_mutation.py")
        for stack in capture.builder.stacks
        for frame in stack.frames
    )


def test_ssa_retargeting_records_only_calls_with_then_current_uses() -> None:
    capture = _Capture()
    with capture.installed():
        producer = _PlainStatement(result_types=(AnyType(),))
        destination = _PlainStatement(result_types=(AnyType(),))
        consumer = _PlainStatement(args=(producer.results[0],))
        producer.results[0].replace_by(destination.results[0])
        assert consumer.args[0] is destination.results[0]

        unused = _PlainStatement(result_types=(AnyType(),)).results[0]
        other = _PlainStatement(result_types=(AnyType(),)).results[0]
        unused.replace_by(other)

    assert _operation_apis(capture) == [
        "SSAValue.replace_by",
        "SSAValue.replace_by",
    ]
    assert [relation.basis for relation in capture.builder.relations] == [
        "ssa_uses_retargeted_to"
    ]
    assert capture.builder.relations[0].mutation_operation_id == "operation-0"
    assert capture.builder.relations[0].source_entity_id == (
        capture.builder.registry.lookup(producer.results[0])
    )
    assert capture.builder.relations[0].destination_entity_id == (
        capture.builder.registry.lookup(destination.results[0])
    )


def test_copy_and_recursive_clone_preserve_dynamic_binding_and_direct_pairs() -> None:
    capture = _Capture()
    with capture.installed():
        source = _DerivedStatement(result_types=(AnyType(),))
        copied = _DerivedStatement.from_stmt(source)
        assert type(copied) is _DerivedStatement

        block = Block(argtypes=(AnyType(),))
        nested_source = _PlainStatement(
            args=(next(iter(block.args)),),
            result_types=(AnyType(),),
        )
        block.stmts.append(nested_source)
        region = Region(block)
        cloned = region.clone()

    assert cloned is not region
    assert _operation_apis(capture) == [
        "Statement.from_stmt",
        "Region.clone",
        "Statement.from_stmt",
    ]
    assert capture.builder.operations[2].parent_operation_id == "operation-1"
    assert [relation.basis for relation in capture.builder.relations] == [
        "statement_copied_to",
        "result_copied_to",
        "statement_copied_to",
        "result_copied_to",
        "region_cloned_to",
        "block_cloned_to",
        "block_argument_cloned_to",
    ]
    root_relations = [
        relation
        for relation in capture.builder.relations
        if relation.mutation_operation_id == "operation-1"
    ]
    assert [relation.basis for relation in root_relations] == [
        "region_cloned_to",
        "block_cloned_to",
        "block_argument_cloned_to",
    ]


def test_region_clone_pairs_the_entry_time_source_argument_inventory() -> None:
    capture = _Capture()
    block = Block(argtypes=(AnyType(),))
    block.stmts.append(_MutatingCloneStatement())
    region = Region(block)
    _MutatingCloneStatement.source_block = block
    try:
        with capture.installed():
            cloned = region.clone()
    finally:
        _MutatingCloneStatement.source_block = None

    assert len(block.args) == 2
    assert len(cloned.blocks[0].args) == 1
    root = next(
        operation
        for operation in capture.builder.operations
        if operation.api == "Region.clone"
    )
    assert root.outcome == "completed"
    assert [
        relation.basis
        for relation in capture.builder.relations
        if relation.mutation_operation_id == root.id
    ] == [
        "region_cloned_to",
        "block_cloned_to",
        "block_argument_cloned_to",
    ]


def test_deletion_effect_is_historical_and_deleted_ssa_has_no_relation() -> None:
    capture = _Capture()
    with capture.installed():
        statement = _PlainStatement(result_types=(AnyType(),))
        block = Block([statement])
        statement.delete()
        block.stmts.append(statement)
        entity_before_release = capture.builder.registry.lookup(statement)
        assert entity_before_release is not None
        assert capture.builder.registry.lookup(statement) == entity_before_release

        detached = _PlainStatement()
        Block([detached])
        detached.detach()

    assert tuple(block.stmts) == (statement,)
    assert _operation_apis(capture) == [
        "Statement.delete",
        "SSAValue.replace_by",
    ]
    assert capture.builder.relations == []
    assert len(capture.builder.effects) == 1
    assert capture.builder.effects[0].mutation_operation_id == "operation-0"


def test_outer_exception_keeps_completed_child_and_propagates_same_object() -> None:
    capture = _Capture()
    with capture.installed():
        source = _ExplodingStatement(result_types=(AnyType(),))
        replacement = _PlainStatement(result_types=(AnyType(),))
        consumer = _PlainStatement(args=(source.results[0],))
        Block([source, consumer])
        source.explode = True

        with pytest.raises(RuntimeError) as caught:
            source.replace_by(replacement)

    assert caught.value is _SENTINEL
    assert _operation_apis(capture) == [
        "Statement.replace_by",
        "SSAValue.replace_by",
        "Statement.delete",
    ]
    assert [operation.outcome for operation in capture.builder.operations] == [
        "incomplete",
        "completed",
        "incomplete",
    ]
    assert [relation.basis for relation in capture.builder.relations] == [
        "ssa_uses_retargeted_to"
    ]
    assert capture.builder.relations[0].mutation_operation_id == "operation-1"
    assert capture.builder.effects == []
    assert consumer.args[0] is replacement.results[0]


def test_prebound_bypass_invalidates_with_the_stored_error_instance() -> None:
    capture = _Capture()
    source = _PlainStatement(result_types=(AnyType(),)).results[0]
    destination = _PlainStatement(result_types=(AnyType(),)).results[0]
    prebound = source.replace_by

    with capture.installed(), pytest.raises(_Unsupported) as caught:
        prebound(destination)

    assert caught.value is capture.error
    assert len(capture.reasons) == 1
    assert "without its installed interception wrapper" in capture.reasons[0]
    assert capture.builder.operations == []


def test_equal_but_distinct_code_object_is_not_a_selected_saved_entry() -> None:
    capture = _Capture()
    raw = vars(Statement)["replace_by"]
    assert isinstance(raw, FunctionType)
    copied_code = raw.__code__.replace()
    assert copied_code is not raw.__code__
    assert copied_code == raw.__code__
    copied_function = FunctionType(copied_code, raw.__globals__)
    observed: list[bool] = []
    stopped = RuntimeError("stop before copied implementation")

    def profile(frame: FrameType, event: str, _arg: object) -> None:
        if event == "call" and frame.f_code is copied_code:
            observed.append(capture.interceptor.authorize_profile_call(frame))
            raise stopped

    source = _PlainStatement()
    replacement = _PlainStatement()
    sys.setprofile(profile)
    try:
        with pytest.raises(RuntimeError) as caught:
            copied_function(source, replacement)
    finally:
        sys.setprofile(None)

    assert caught.value is stopped
    assert observed == [False]
    assert capture.reasons == []


def _assert_delegation_corruption(corruption: str) -> None:
    capture = _Capture()
    selected_index = 2 if corruption == "class" else 0

    def profile(frame: FrameType, event: str, _arg: object) -> None:
        if (
            event == "call"
            and frame.f_code is capture.interceptor.selected_codes[selected_index]
        ):
            expected = capture.interceptor._expected[-1]
            if corruption == "code":
                expected.raw = capture.interceptor._targets[1].raw
            else:
                expected.receiver = object()
            capture.interceptor.authorize_profile_call(frame)

    capture.interceptor.install()
    sys.setprofile(profile)
    try:
        with pytest.raises(_Unsupported) as caught:
            if corruption == "class":
                _DerivedStatement.from_stmt(_DerivedStatement())
            else:
                source = _PlainStatement()
                Block([source])
                source.replace_by(_PlainStatement())
    finally:
        sys.setprofile(None)
        capture.interceptor.uninstall()

    assert caught.value is capture.error
    assert len(capture.reasons) == 1
    if corruption == "code":
        assert "did not match" in capture.reasons[0]
    else:
        assert "unexpected receiver or class" in capture.reasons[0]
    assert capture.builder.operations[0].outcome == "incomplete"


def test_wrong_delegation_code_receiver_or_class_invalidates_once() -> None:
    for corruption in ("code", "receiver", "class"):
        _assert_delegation_corruption(corruption)


def test_missing_and_reused_delegation_tokens_invalidate_once() -> None:
    missing = _Capture()
    with missing.installed(profile=False), pytest.raises(_Unsupported) as caught:
        _PlainStatement(result_types=(AnyType(),)).results[0].replace_by(
            _PlainStatement(result_types=(AnyType(),)).results[0]
        )
    assert caught.value is missing.error
    assert len(missing.reasons) == 1
    assert "without consuming" in missing.reasons[0]

    exceptional = _Capture()
    exploding = _ExplodingStatement()
    exploding.explode = True
    with exceptional.installed(profile=False), pytest.raises(RuntimeError) as caught:
        exploding.delete()
    assert caught.value is _SENTINEL
    assert exceptional.reasons == [
        "Statement.delete exited without consuming its delegation token"
    ]
    assert exceptional.builder.operations[0].outcome == "incomplete"

    reused = _Capture()

    def duplicate_profile(frame: FrameType, event: str, _arg: object) -> None:
        if event == "call" and reused.interceptor.authorize_profile_call(frame):
            reused.interceptor.authorize_profile_call(frame)

    reused.interceptor.install()
    sys.setprofile(duplicate_profile)
    try:
        with pytest.raises(_Unsupported) as caught:
            _PlainStatement(result_types=(AnyType(),)).results[0].replace_by(
                _PlainStatement(result_types=(AnyType(),)).results[0]
            )
    finally:
        sys.setprofile(None)
        reused.interceptor.uninstall()

    assert caught.value is reused.error
    assert len(reused.reasons) == 1
    assert "reused a consumed delegation token" in reused.reasons[0]
    assert reused.builder.operations[0].outcome == "incomplete"
