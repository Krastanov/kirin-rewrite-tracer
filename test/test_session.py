from __future__ import annotations

import asyncio
import gc
import inspect
import sys
import weakref
from collections.abc import AsyncIterator, ItemsView, Iterator, Mapping
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any, ClassVar, cast

import pytest
from kirin.ir import Block, IRNode, Region, SSAValue, Statement
from kirin.ir.attrs.types import AnyType
from kirin.rewrite.abc import RewriteResult, RewriteRule

from kirin_rewrite_tracer import (
    TraceRecorder,
    TraceStateError,
    UnsupportedTraceError,
    trace_rewrites,
)


class _PlainStatement(Statement):
    name = "test.session"


class _NoOpRule(RewriteRule):
    def rewrite_Statement(self, node: Statement) -> RewriteResult:
        assert isinstance(node, _PlainStatement)
        return RewriteResult()


@dataclass
class _ReturnRule(RewriteRule):
    result: object

    def rewrite(self, node: IRNode[Any]) -> object:  # type: ignore[override]
        assert isinstance(node, _PlainStatement)
        return self.result


@dataclass
class _RaiseRule(RewriteRule):
    error: BaseException

    def rewrite(self, node: IRNode[Any]) -> RewriteResult:
        assert isinstance(node, _PlainStatement)
        raise self.error


@dataclass
class _NestedRule(RewriteRule):
    child: RewriteRule
    catch: bool = False

    def rewrite(self, node: IRNode[Any]) -> RewriteResult:
        if self.catch:
            with suppress(RuntimeError):
                self.child.rewrite(node)
        else:
            self.child.rewrite(node)
        return RewriteResult()


@dataclass
class _CrossInstanceRule(RewriteRule):
    child: RewriteRule

    def rewrite(self, node: IRNode[Any]) -> RewriteResult:
        assert isinstance(node, Statement)
        return self.child.rewrite_Statement(node)


class _GeneratorRule(RewriteRule):
    def rewrite(  # type: ignore[override]
        self, node: IRNode[Any]
    ) -> Iterator[RewriteResult]:
        assert isinstance(node, _PlainStatement)
        yield RewriteResult()


@dataclass
class _NestedGeneratorRule(RewriteRule):
    """Open a real public event, then invalidate from a nested generator body.

    The outer frame owns a live event shell holding the rule and the root, so
    releasing them stays observable after the inner refusal.
    """

    child: _GeneratorRule

    def rewrite(self, node: IRNode[Any]) -> RewriteResult:
        next(self.child.rewrite(node))
        return RewriteResult()


class _CoroutineRule(RewriteRule):
    async def rewrite(  # type: ignore[override]
        self, node: IRNode[Any]
    ) -> RewriteResult:
        assert isinstance(node, _PlainStatement)
        return RewriteResult()


class _AsyncGeneratorRule(RewriteRule):
    async def rewrite(  # type: ignore[override]
        self, node: IRNode[Any]
    ) -> AsyncIterator[RewriteResult]:
        assert isinstance(node, _PlainStatement)
        yield RewriteResult()


_MUTATION_ERROR = RuntimeError("selected mutation failed")


class _ExplodingStatement(_PlainStatement):
    explode = False

    def detach(self) -> None:
        if self.explode:
            raise _MUTATION_ERROR
        super().detach()


class _ForeignRootStatement(_PlainStatement):
    foreign_error: ClassVar[UnsupportedTraceError]

    def get_root(self) -> IRNode[Any]:
        raise self.foreign_error


class _CaughtMutationRule(RewriteRule):
    def rewrite_Statement(self, node: Statement) -> RewriteResult:
        try:
            node.delete()
        except RuntimeError as error:
            assert error is _MUTATION_ERROR
        return RewriteResult()


class _AnalysisValue:
    def __init__(self, text: str) -> None:
        self.text = text

    def __repr__(self) -> str:
        return self.text


class _FrameSentinel:
    pass


class _WeakAnalysisMapping(Mapping[SSAValue, object]):
    def __init__(self, values: dict[SSAValue, object]) -> None:
        self._entries = values

    def __getitem__(self, key: SSAValue) -> object:
        return self._entries[key]

    def __iter__(self) -> Iterator[SSAValue]:
        return iter(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def __bool__(self) -> bool:
        return False


@dataclass
class _HostileAnalysisMapping(Mapping[SSAValue, object]):
    error: UnsupportedTraceError

    def __getitem__(self, key: SSAValue) -> object:
        raise KeyError(key)

    def __iter__(self) -> Iterator[SSAValue]:
        return iter(())

    def __len__(self) -> int:
        return 1

    def items(self) -> ItemsView[SSAValue, object]:
        raise self.error


@dataclass
class _ProfileClaimingAnalysis(Mapping[SSAValue, object]):
    callback: Any

    def __getitem__(self, key: SSAValue) -> object:
        raise KeyError(key)

    def __iter__(self) -> Iterator[SSAValue]:
        return iter(())

    def __len__(self) -> int:
        return 0

    def items(self) -> ItemsView[SSAValue, object]:
        sys.setprofile(self.callback)
        return dict[SSAValue, object]().items()


class _HostileStringError(RuntimeError):
    def __str__(self) -> str:
        raise AssertionError("the tracer formatted a caller exception")


@dataclass
class _StringFailureAnalysis(Mapping[SSAValue, object]):
    error: _HostileStringError

    def __getitem__(self, key: SSAValue) -> object:
        raise KeyError(key)

    def __iter__(self) -> Iterator[SSAValue]:
        return iter(())

    def __len__(self) -> int:
        return 1

    def items(self) -> ItemsView[SSAValue, object]:
        raise self.error


@dataclass
class _AnalysisMutationRule(RewriteRule):
    analysis: dict[SSAValue, object]
    owner: SSAValue

    def rewrite_Statement(self, node: Statement) -> RewriteResult:
        self.analysis[self.owner] = _AnalysisValue("mutated-after-entry")
        return RewriteResult()


@dataclass
class _TransientCopyRule(RewriteRule):
    reference: weakref.ReferenceType[Statement] | None = field(default=None, init=False)

    def rewrite_Statement(self, node: Statement) -> RewriteResult:
        copied = type(node).from_stmt(node)
        self.reference = weakref.ref(copied)
        return RewriteResult()


class _DeleteRule(RewriteRule):
    def rewrite_Statement(self, node: Statement) -> RewriteResult:
        node.delete()
        return RewriteResult(has_done_something=True)


class _HelperRule(RewriteRule):
    def helper(self, node: IRNode[Any]) -> None:
        assert isinstance(node, Statement)

    def rewrite_func_X(self, node: IRNode[Any]) -> None:
        assert isinstance(node, Statement)

    def rewrite(self, node: IRNode[Any]) -> RewriteResult:
        self.helper(node)
        self.rewrite_func_X(node)
        return RewriteResult()


@dataclass(eq=False)
class _EqualDelegator(RewriteRule):
    child: RewriteRule

    def __eq__(self, other: object) -> bool:
        return isinstance(other, RewriteRule)

    def __hash__(self) -> int:
        return id(self)

    def rewrite(self, node: IRNode[Any]) -> RewriteResult:
        assert isinstance(node, Statement)
        return self.child.rewrite_Statement(node)


class _EqualLeaf(_NoOpRule):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, RewriteRule)

    def __hash__(self) -> int:
        return id(self)


class _SelfDispatchingLeaf(RewriteRule):
    """Delegate to its own specialized handler once promoted."""

    def rewrite_Statement(self, node: Statement) -> RewriteResult:
        block = Block()
        return self.rewrite_Block(block)

    def rewrite_Block(self, node: Block) -> RewriteResult:
        return RewriteResult()


@dataclass
class _BlockDelegatingLeaf(RewriteRule):
    child: RewriteRule

    def rewrite_Statement(self, node: Statement) -> RewriteResult:
        return self.child.rewrite_Block(Block())


@dataclass
class _RecursiveDelegator(RewriteRule):
    """Bounce between two instances until ``depth`` calls have been made."""

    depth: int
    partner: _RecursiveDelegator | None = None

    def rewrite(self, node: IRNode[Any]) -> RewriteResult:
        assert isinstance(node, Statement)
        return self.rewrite_Statement(node)

    def rewrite_Statement(self, node: Statement) -> RewriteResult:
        if self.depth <= 0 or self.partner is None:
            return RewriteResult()
        self.partner.depth = self.depth - 1
        return self.partner.rewrite_Statement(node)


class _NonResultLeaf(RewriteRule):
    def rewrite_Statement(self, node: Statement) -> RewriteResult:
        return cast(RewriteResult, None)


class _RaisingLeaf(RewriteRule):
    def rewrite_Statement(self, node: Statement) -> RewriteResult:
        raise RuntimeError("leaf failure")


@dataclass
class _CatchingDelegator(RewriteRule):
    child: RewriteRule

    def rewrite(self, node: IRNode[Any]) -> RewriteResult:
        assert isinstance(node, Statement)
        with suppress(RuntimeError):
            self.child.rewrite_Statement(node)
        return RewriteResult()


class _UnrelatedRewriter:
    def rewrite(self, node: IRNode[Any]) -> IRNode[Any]:
        return node


class _HostileRootStatement(_PlainStatement):
    error: ClassVar[_HostileStringError]

    def get_root(self) -> IRNode[Any]:
        raise self.error


def _assert_invalid_trace(
    recorder: TraceRecorder, expected: UnsupportedTraceError
) -> None:
    assert recorder.state == "INVALID"
    with pytest.raises(UnsupportedTraceError) as denied:
        _ = recorder.trace
    assert denied.value is expected


def test_public_exports_and_one_shot_state_machine() -> None:
    recorder = trace_rewrites()
    assert isinstance(recorder, TraceRecorder)
    assert recorder.state == "CREATED"
    with pytest.raises(TraceStateError):
        _ = recorder.trace

    with recorder as entered:
        assert entered is recorder
        assert recorder.state == "ACTIVE"
        with pytest.raises(TraceStateError):
            _ = recorder.trace

    assert recorder.state == "FROZEN"
    first = recorder.trace
    assert first is recorder.trace
    assert first.complete
    assert first.events == ()
    assert first.configurations == ()
    with pytest.raises(TraceStateError), recorder:
        pass


def test_complete_event_preserves_result_identity_and_exact_facts() -> None:
    result = RewriteResult(
        terminated=True,
        has_done_something=False,
        exceeded_max_iter=True,
    )
    rule = _ReturnRule(result)
    node = _PlainStatement()

    with trace_rewrites() as recorder:
        observed = rule.rewrite(node)

    assert observed is result
    trace = recorder.trace
    assert trace.complete
    assert len(trace.events) == 1
    event = trace.events[0]
    assert event.id == "event-0"
    assert event.parent_id is None
    assert event.sibling_ordinal == 0
    assert event.rule_type.endswith("._ReturnRule")
    assert event.completion == "complete"
    assert event.result is not None
    assert (
        event.result.terminated,
        event.result.has_done_something,
        event.result.exceeded_max_iter,
    ) == (True, False, True)
    assert len(trace.snapshots) == 2
    assert trace.snapshots_semantically_equal(
        event.before_snapshot_id, cast(str, event.after_snapshot_id)
    )


def test_base_dispatch_records_one_public_event_not_specialized_handler() -> None:
    with trace_rewrites() as recorder:
        result = _NoOpRule().rewrite(_PlainStatement())

    assert isinstance(result, RewriteResult)
    assert len(recorder.trace.events) == 1
    assert recorder.trace.events[0].rule_type.endswith("._NoOpRule")


def test_profile_callback_identity_is_stable_for_the_active_session() -> None:
    with trace_rewrites() as recorder:
        callback = sys.getprofile()
        assert callback is not None
        assert sys.getprofile() is callback
        _NoOpRule().rewrite(_PlainStatement())
        assert sys.getprofile() is callback

    assert sys.getprofile() is None
    assert recorder.trace.complete


def test_nested_events_use_lifo_parents_siblings_and_multiple_roots() -> None:
    parent = _NestedRule(_NoOpRule())
    node = _PlainStatement()

    with trace_rewrites() as recorder:
        parent.rewrite(node)
        _NoOpRule().rewrite(node)

    events = recorder.trace.events
    assert [(event.parent_id, event.sibling_ordinal) for event in events] == [
        (None, 0),
        ("event-0", 0),
        (None, 1),
    ]
    assert all(event.completion == "complete" for event in events)


def test_supported_public_exception_freezes_then_propagates_same_object() -> None:
    expected = RuntimeError("rewrite failed")
    recorder = trace_rewrites()

    with pytest.raises(RuntimeError) as caught, recorder:
        _RaiseRule(expected).rewrite(_PlainStatement())

    assert caught.value is expected
    assert recorder.state == "FROZEN"
    assert not recorder.trace.complete
    event = recorder.trace.events[0]
    assert event.completion == "incomplete"
    assert event.after_snapshot_id is None
    assert event.result is None


def test_outside_only_exception_freezes_a_complete_empty_trace() -> None:
    expected = RuntimeError("outside")
    recorder = trace_rewrites()

    with pytest.raises(RuntimeError) as caught, recorder:
        raise expected

    assert caught.value is expected
    assert recorder.trace.complete
    assert recorder.trace.events == ()


def test_caught_child_exception_keeps_child_incomplete_and_parent_complete() -> None:
    expected = RuntimeError("caught child")
    rule = _NestedRule(_RaiseRule(expected), catch=True)

    with trace_rewrites() as recorder:
        result = rule.rewrite(_PlainStatement())

    assert isinstance(result, RewriteResult)
    assert not recorder.trace.complete
    parent, child = recorder.trace.events
    assert parent.completion == "complete"
    assert child.completion == "incomplete"
    assert child.parent_id == parent.id


def test_explicit_non_result_is_neutral_incomplete() -> None:
    recorder = trace_rewrites()
    with recorder:
        result = _ReturnRule(None).rewrite(_PlainStatement())

    assert result is None
    assert not recorder.trace.complete
    assert recorder.trace.events[0].completion == "incomplete"


def test_incomplete_mutation_does_not_make_a_complete_event_trace_incomplete() -> None:
    node = _ExplodingStatement()
    Block([node])
    node.explode = True

    with trace_rewrites() as recorder:
        result = _CaughtMutationRule().rewrite(node)

    assert isinstance(result, RewriteResult)
    assert recorder.trace.complete
    assert recorder.trace.events[0].completion == "complete"
    assert [operation.outcome for operation in recorder.trace.operations] == [
        "incomplete"
    ]


def test_analysis_is_shallow_copied_and_falsey_values_remain_supplied() -> None:
    node = _PlainStatement(result_types=(AnyType(),))
    owner = node.results[0]
    original_value = _AnalysisValue("0")
    analysis: dict[SSAValue, object] = {owner: original_value}
    rule = _AnalysisMutationRule(analysis, owner)

    with trace_rewrites(analysis=analysis) as recorder:
        rule.rewrite(node)

    assert analysis[owner] is not original_value
    snapshots = recorder.trace.snapshots
    assert all(snapshot.analysis_supplied for snapshot in snapshots)
    records = [
        record
        for record in recorder.trace.metadata
        if record.namespace == "analysis" and record.owner_entity_id == "entity-1"
    ]
    assert len(records) == 2
    assert [record.value.text for record in records if record.value is not None] == [
        "0",
        "0",
    ]

    with trace_rewrites() as omitted:
        _NoOpRule().rewrite(_PlainStatement(result_types=(AnyType(),)))
    assert all(not snapshot.analysis_supplied for snapshot in omitted.trace.snapshots)
    assert all(record.namespace != "analysis" for record in omitted.trace.metadata)


def test_empty_and_falsey_analysis_mappings_are_still_supplied() -> None:
    node = _PlainStatement(result_types=(AnyType(),))
    falsey = _WeakAnalysisMapping({node.results[0]: None})
    assert not falsey

    with trace_rewrites(analysis=falsey) as falsey_recorder:
        _NoOpRule().rewrite(node)
    assert all(
        snapshot.analysis_supplied for snapshot in falsey_recorder.trace.snapshots
    )
    assert [
        record.presence
        for record in falsey_recorder.trace.metadata
        if record.namespace == "analysis"
    ] == ["present", "present"]

    with trace_rewrites(analysis={}) as empty_recorder:
        _NoOpRule().rewrite(_PlainStatement())
    assert all(
        snapshot.analysis_supplied for snapshot in empty_recorder.trace.snapshots
    )


def test_original_analysis_mapping_is_released_immediately_after_entry() -> None:
    node = _PlainStatement(result_types=(AnyType(),))
    source = _WeakAnalysisMapping({node.results[0]: _AnalysisValue("retained-copy")})
    source_reference = weakref.ref(source)
    recorder = trace_rewrites(analysis=source)

    with recorder:
        del source
        gc.collect()
        assert source_reference() is None
        _NoOpRule().rewrite(node)

    assert recorder.trace.complete


def test_terminal_freeze_releases_rules_roots_analysis_and_transient_entities() -> None:
    node = _PlainStatement(result_types=(AnyType(),))
    owner = node.results[0]
    analysis_value = _AnalysisValue("analysis-only")
    analysis: dict[SSAValue, object] = {owner: analysis_value}
    rule = _TransientCopyRule()
    node_reference = weakref.ref(node)
    owner_reference = weakref.ref(owner)
    value_reference = weakref.ref(analysis_value)
    rule_reference = weakref.ref(rule)

    with trace_rewrites(analysis=analysis) as recorder:
        rule.rewrite(node)

    transient_reference = rule.reference
    assert transient_reference is not None
    analysis.clear()
    del owner, analysis_value, rule, node
    gc.collect()

    assert recorder.state == "FROZEN"
    assert node_reference() is None
    assert owner_reference() is None
    assert value_reference() is None
    assert rule_reference() is None
    assert transient_reference() is None


def test_completed_event_releases_invocation_frame_locals_while_still_active() -> None:
    node = _PlainStatement()

    def invoke() -> weakref.ReferenceType[_FrameSentinel]:
        sentinel = _FrameSentinel()
        reference = weakref.ref(sentinel)
        _NoOpRule().rewrite(node)
        return reference

    with trace_rewrites() as recorder:
        reference = invoke()
        gc.collect()
        assert reference() is None

    assert recorder.trace.complete


def test_cross_instance_specialized_dispatch_records_a_nested_event() -> None:
    with trace_rewrites() as recorder:
        result = _CrossInstanceRule(_NoOpRule()).rewrite(_PlainStatement())

    assert result == RewriteResult()
    trace = recorder.trace
    assert trace.complete
    assert [event.rule_type.rsplit(".", 1)[-1] for event in trace.events] == [
        "_CrossInstanceRule",
        "_NoOpRule",
    ]
    assert [(event.parent_id, event.sibling_ordinal) for event in trace.events] == [
        (None, 0),
        ("event-0", 0),
    ]
    assert all(event.completion == "complete" for event in trace.events)
    assert len(trace.snapshots) == 4


def test_direct_specialized_dispatch_without_an_open_event_invalidates() -> None:
    direct = trace_rewrites()
    with pytest.raises(UnsupportedTraceError) as direct_error, direct:
        _NoOpRule().rewrite_Statement(_PlainStatement())
    _assert_invalid_trace(direct, direct_error.value)
    assert "outside a public rewrite event" in direct_error.value.reason


def test_equal_but_distinct_rules_still_open_a_nested_event() -> None:
    parent = _EqualDelegator(_EqualLeaf())
    assert parent == parent.child
    assert parent is not parent.child

    with trace_rewrites() as recorder:
        parent.rewrite(_PlainStatement())

    trace = recorder.trace
    assert trace.complete
    assert [event.rule_type.rsplit(".", 1)[-1] for event in trace.events] == [
        "_EqualDelegator",
        "_EqualLeaf",
    ]
    assert trace.events[1].parent_id == trace.events[0].id


def test_same_instance_dispatch_inside_a_promoted_handler_records_no_event() -> None:
    with trace_rewrites() as recorder:
        _CrossInstanceRule(_SelfDispatchingLeaf()).rewrite(_PlainStatement())

    trace = recorder.trace
    assert trace.complete
    assert [event.rule_type.rsplit(".", 1)[-1] for event in trace.events] == [
        "_CrossInstanceRule",
        "_SelfDispatchingLeaf",
    ]


def test_a_promoted_handler_can_itself_parent_a_promoted_handler() -> None:
    leaf = _SelfDispatchingLeaf()
    with trace_rewrites() as recorder:
        _CrossInstanceRule(_BlockDelegatingLeaf(leaf)).rewrite(_PlainStatement())

    trace = recorder.trace
    assert trace.complete
    assert [event.rule_type.rsplit(".", 1)[-1] for event in trace.events] == [
        "_CrossInstanceRule",
        "_BlockDelegatingLeaf",
        "_SelfDispatchingLeaf",
    ]
    assert [event.parent_id for event in trace.events] == [
        None,
        "event-0",
        "event-1",
    ]


def test_mutually_recursive_delegation_records_one_event_per_crossing() -> None:
    first = _RecursiveDelegator(depth=2)
    second = _RecursiveDelegator(depth=0, partner=first)
    first.partner = second

    with trace_rewrites() as recorder:
        first.rewrite(_PlainStatement())

    trace = recorder.trace
    assert trace.complete
    assert [event.parent_id for event in trace.events] == [
        None,
        "event-0",
        "event-1",
    ]
    assert trace.events[0].rule_type == trace.events[2].rule_type
    assert recorder.state == "FROZEN"


def test_promoted_handler_without_a_result_leaves_both_events_incomplete() -> None:
    with trace_rewrites() as recorder:
        _CrossInstanceRule(_NonResultLeaf()).rewrite(_PlainStatement())

    trace = recorder.trace
    assert not trace.complete
    assert [event.completion for event in trace.events] == [
        "incomplete",
        "incomplete",
    ]
    assert all(event.after_snapshot_id is None for event in trace.events)
    assert all(event.result is None for event in trace.events)


def test_raising_promoted_handler_stays_incomplete_under_a_complete_parent() -> None:
    with trace_rewrites() as recorder:
        _CatchingDelegator(_RaisingLeaf()).rewrite(_PlainStatement())

    trace = recorder.trace
    assert not trace.complete
    assert [event.completion for event in trace.events] == ["complete", "incomplete"]
    assert trace.events[1].parent_id == trace.events[0].id
    assert trace.events[1].result is None


def test_caught_callback_error_removes_profile_and_exit_reraises_same_object() -> None:
    recorder = trace_rewrites()
    inside: UnsupportedTraceError | None = None

    with pytest.raises(UnsupportedTraceError) as outside, recorder:
        try:
            _NoOpRule().rewrite_Statement(_PlainStatement())
        except UnsupportedTraceError as error:
            inside = error
            assert sys.getprofile() is None

    assert inside is outside.value
    assert isinstance(outside.value, UnsupportedTraceError)
    _assert_invalid_trace(recorder, outside.value)


def test_caught_unsupported_never_replaces_a_later_body_exception() -> None:
    later = RuntimeError("later body exception")
    recorder = trace_rewrites()
    unsupported: UnsupportedTraceError | None = None

    with pytest.raises(RuntimeError) as caught_later, recorder:
        try:
            _NoOpRule().rewrite_Statement(_PlainStatement())
        except UnsupportedTraceError as caught:
            unsupported = caught
        raise later

    assert caught_later.value is later
    assert unsupported is not None
    _assert_invalid_trace(recorder, unsupported)


def test_prebound_selected_mutator_bypass_invalidates() -> None:
    source = _PlainStatement(result_types=(AnyType(),)).results[0]
    destination = _PlainStatement(result_types=(AnyType(),)).results[0]
    prebound = source.replace_by
    recorder = trace_rewrites()

    with pytest.raises(UnsupportedTraceError) as caught, recorder:
        prebound(destination)

    _assert_invalid_trace(recorder, caught.value)
    assert "without its installed interception wrapper" in caught.value.reason


def test_malformed_public_frames_and_result_fields_invalidate() -> None:
    recorder = trace_rewrites()
    with pytest.raises(UnsupportedTraceError) as malformed, recorder:
        RewriteRule.rewrite(object(), _PlainStatement())  # type: ignore[arg-type]
    _assert_invalid_trace(recorder, malformed.value)

    bad_result = RewriteResult()
    bad_result.terminated = cast(bool, 1)
    recorder = trace_rewrites()
    with pytest.raises(UnsupportedTraceError) as bad_fields, recorder:
        _ReturnRule(bad_result).rewrite(_PlainStatement())
    _assert_invalid_trace(recorder, bad_fields.value)
    assert "exact booleans" in bad_fields.value.reason


def test_foreign_unsupported_from_capture_becomes_the_recorder_error() -> None:
    foreign = UnsupportedTraceError("foreign capture error")
    _ForeignRootStatement.foreign_error = foreign
    recorder = trace_rewrites()

    with pytest.raises(UnsupportedTraceError) as caught, recorder:
        _NoOpRule().rewrite(_ForeignRootStatement())

    assert caught.value is not foreign
    _assert_invalid_trace(recorder, caught.value)


def test_late_invalid_node_and_nonplain_descriptor_invalidate() -> None:
    late_recorder = trace_rewrites()

    with pytest.raises(UnsupportedTraceError) as late_error, late_recorder:

        class LateRule(RewriteRule):
            def rewrite(self, node: IRNode[Any]) -> RewriteResult:
                return RewriteResult()

        LateRule().rewrite(cast(IRNode[Any], object()))

    _assert_invalid_trace(late_recorder, late_error.value)

    class StaticRule(RewriteRule):
        @staticmethod
        def rewrite(  # type: ignore[override]
            self: RewriteRule, node: IRNode[Any]
        ) -> RewriteResult:
            return RewriteResult()

    descriptor_recorder = trace_rewrites()
    with pytest.raises(UnsupportedTraceError) as descriptor_error, descriptor_recorder:
        StaticRule.rewrite(StaticRule(), _PlainStatement())
    _assert_invalid_trace(descriptor_recorder, descriptor_error.value)


def test_nonrewrite_helpers_with_self_and_node_are_ignored() -> None:
    with trace_rewrites() as recorder:
        result = _HelperRule().rewrite(_PlainStatement())

    assert isinstance(result, RewriteResult)
    assert len(recorder.trace.events) == 1
    assert recorder.trace.events[0].rule_type.endswith("._HelperRule")


def test_observed_deferred_rewrite_forms_invalidate_but_unexecuted_does_not() -> None:
    node = _PlainStatement()

    with trace_rewrites() as unexecuted:
        iterator = _GeneratorRule().rewrite(node)
    assert inspect.isgenerator(iterator)
    assert unexecuted.trace.events == ()
    iterator.close()

    generator_recorder = trace_rewrites()
    with pytest.raises(UnsupportedTraceError) as generator_error, generator_recorder:
        next(_GeneratorRule().rewrite(node))
    _assert_invalid_trace(generator_recorder, generator_error.value)

    coroutine_recorder = trace_rewrites()
    with pytest.raises(UnsupportedTraceError) as coroutine_error, coroutine_recorder:
        asyncio.run(_CoroutineRule().rewrite(node))
    _assert_invalid_trace(coroutine_recorder, coroutine_error.value)

    async def consume_one() -> object:
        return await anext(_AsyncGeneratorRule().rewrite(node))

    async_generator_recorder = trace_rewrites()
    with (
        pytest.raises(UnsupportedTraceError) as async_generator_error,
        async_generator_recorder,
    ):
        asyncio.run(consume_one())
    _assert_invalid_trace(async_generator_recorder, async_generator_error.value)


def test_prebound_dynamic_unbound_and_super_public_dispatch_are_recorded() -> None:
    node = _PlainStatement()
    prebound = _NoOpRule().rewrite

    with trace_rewrites() as recorder:
        prebound(node)

        class DynamicRule(RewriteRule):
            def rewrite(self, node: IRNode[Any]) -> RewriteResult:
                return RewriteResult()

        DynamicRule().rewrite(node)
        RewriteRule.rewrite(_NoOpRule(), node)

    assert len(recorder.trace.events) == 3
    assert all(event.completion == "complete" for event in recorder.trace.events)

    class SuperRule(RewriteRule):
        def rewrite(self, node: IRNode[Any]) -> RewriteResult:
            return super().rewrite(node)

    with trace_rewrites() as super_recorder:
        SuperRule().rewrite(node)
    outer, inner = super_recorder.trace.events
    assert inner.parent_id == outer.id
    assert outer.rule_type == inner.rule_type


def test_after_snapshot_uses_the_retained_entry_root_after_detachment() -> None:
    node = _PlainStatement()
    block = Block([node])

    with trace_rewrites() as recorder:
        _DeleteRule().rewrite(node)

    assert node.parent is None
    assert tuple(block.stmts) == ()
    event = recorder.trace.events[0]
    before = recorder.trace.index().snapshot(event.before_snapshot_id)
    after = recorder.trace.index().snapshot(cast(str, event.after_snapshot_id))
    assert event.root_entity_id == before.root_entity_id == after.root_entity_id
    assert recorder.trace.index().entity(event.root_entity_id).kind == "block"


def test_selected_mutators_outside_events_leave_a_complete_empty_trace() -> None:
    with trace_rewrites() as recorder:
        source = _PlainStatement(result_types=(AnyType(),))
        replacement = _PlainStatement(result_types=(AnyType(),))
        block = Block([source])
        source.replace_by(replacement)
        assert tuple(block.stmts) == (replacement,)

        old_value = _PlainStatement(result_types=(AnyType(),)).results[0]
        new_value = _PlainStatement(result_types=(AnyType(),)).results[0]
        old_value.replace_by(new_value)

        copied = _PlainStatement.from_stmt(_PlainStatement(result_types=(AnyType(),)))
        assert isinstance(copied, _PlainStatement)

        region = Region(Block(argtypes=(AnyType(),)))
        cloned = region.clone()
        assert cloned is not region

        doomed = _PlainStatement()
        Block([doomed])
        doomed.delete()

    assert recorder.trace.complete
    assert recorder.trace.events == ()
    assert recorder.trace.operations == ()
    assert recorder.trace.relations == ()
    assert recorder.trace.effects == ()


def test_nested_and_occupied_profile_preflight_leave_existing_owner_untouched() -> None:
    with trace_rewrites() as outer:
        inner = trace_rewrites()
        with pytest.raises(UnsupportedTraceError) as nested, inner:
            pass
        _NoOpRule().rewrite(_PlainStatement())
    assert outer.trace.complete
    _assert_invalid_trace(inner, nested.value)

    def foreign_profile(_frame: object, _event: str, _argument: object) -> None:
        return None

    recorder = trace_rewrites()
    sys.setprofile(foreign_profile)
    try:
        with pytest.raises(UnsupportedTraceError) as occupied, recorder:
            pass
        assert sys.getprofile() is foreign_profile
    finally:
        sys.setprofile(None)
    _assert_invalid_trace(recorder, occupied.value)


def test_foreign_profile_or_descriptor_replacement_is_not_clobbered() -> None:
    def foreign_profile(_frame: object, _event: str, _argument: object) -> None:
        return None

    profile_recorder = trace_rewrites()
    try:
        with pytest.raises(UnsupportedTraceError) as profile_error, profile_recorder:
            sys.setprofile(foreign_profile)
        assert sys.getprofile() is foreign_profile
    finally:
        sys.setprofile(None)
    _assert_invalid_trace(profile_recorder, profile_error.value)

    original = vars(Statement)["delete"]

    def foreign_delete(self: Statement, safe: bool = True) -> None:
        del self, safe

    descriptor_recorder = trace_rewrites()
    try:
        with (
            pytest.raises(UnsupportedTraceError) as descriptor_error,
            descriptor_recorder,
        ):
            Statement.delete = foreign_delete  # type: ignore[method-assign]
        assert vars(Statement)["delete"] is foreign_delete
    finally:
        Statement.delete = original  # type: ignore[method-assign]
    _assert_invalid_trace(descriptor_recorder, descriptor_error.value)


def test_profile_install_failure_rolls_back_and_releases_active_ownership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    originals = tuple(
        inspect.getattr_static(owner, name)
        for owner, name in (
            (Statement, "replace_by"),
            (SSAValue, "replace_by"),
            (Statement, "from_stmt"),
            (Region, "clone"),
            (Statement, "delete"),
        )
    )
    failure = RuntimeError("profile install failure")
    recorder = trace_rewrites()

    def fail_profile_install(callback: object) -> None:
        assert callback is not None
        raise failure

    with monkeypatch.context() as scoped:
        scoped.setattr(sys, "setprofile", fail_profile_install)
        with pytest.raises(UnsupportedTraceError) as caught, recorder:
            pass

    assert (
        tuple(
            inspect.getattr_static(owner, name)
            for owner, name in (
                (Statement, "replace_by"),
                (SSAValue, "replace_by"),
                (Statement, "from_stmt"),
                (Region, "clone"),
                (Statement, "delete"),
            )
        )
        == originals
    )
    _assert_invalid_trace(recorder, caught.value)

    with trace_rewrites() as fresh:
        _NoOpRule().rewrite(_PlainStatement())
    assert fresh.trace.complete


def test_invalid_analysis_is_rejected_at_entry_and_releases_the_mapping() -> None:
    invalid = cast(Mapping[SSAValue, object], {"not-an-ssa": object()})
    recorder = trace_rewrites(analysis=invalid)

    with pytest.raises(UnsupportedTraceError) as caught, recorder:
        pass

    _assert_invalid_trace(recorder, caught.value)


def test_caller_unsupported_error_from_analysis_cannot_bypass_transaction() -> None:
    caller_error = UnsupportedTraceError("caller-created lookalike")
    recorder = trace_rewrites(analysis=_HostileAnalysisMapping(caller_error))

    with pytest.raises(UnsupportedTraceError) as caught, recorder:
        pass

    assert caught.value is not caller_error
    assert recorder.state == "INVALID"
    _assert_invalid_trace(recorder, caught.value)


def test_analysis_cannot_claim_and_then_lose_the_profile_slot() -> None:
    def foreign_profile(_frame: Any, _event: str, _argument: object) -> None:
        return None

    recorder = trace_rewrites(analysis=_ProfileClaimingAnalysis(foreign_profile))
    try:
        with pytest.raises(UnsupportedTraceError) as caught:
            recorder.__enter__()
        assert sys.getprofile() is foreign_profile
    finally:
        sys.setprofile(None)

    _assert_invalid_trace(recorder, caught.value)
    assert "profile slot became occupied" in caught.value.reason


def test_unrelated_rewrite_named_call_is_not_a_public_kirin_frame() -> None:
    node = _PlainStatement()

    with trace_rewrites() as recorder:
        result = _UnrelatedRewriter().rewrite(node)

    assert result is node
    assert recorder.trace.events == ()


def _make_terminal_invalid_weakrefs() -> tuple[
    TraceRecorder,
    weakref.ReferenceType[_NestedGeneratorRule],
    weakref.ReferenceType[_PlainStatement],
    weakref.ReferenceType[UnsupportedTraceError],
]:
    node = _PlainStatement()
    rule = _NestedGeneratorRule(_GeneratorRule())
    node_reference = weakref.ref(node)
    rule_reference = weakref.ref(rule)
    recorder = trace_rewrites()

    error_reference: weakref.ReferenceType[UnsupportedTraceError] | None = None
    try:
        with recorder, suppress(UnsupportedTraceError):
            rule.rewrite(node)
    except UnsupportedTraceError as error:
        error_reference = weakref.ref(error)
    assert error_reference is not None
    return recorder, rule_reference, node_reference, error_reference


def test_terminal_invalid_recorder_releases_error_traceback_frames() -> None:
    (
        recorder,
        rule_reference,
        node_reference,
        error_reference,
    ) = _make_terminal_invalid_weakrefs()

    gc.collect()

    assert rule_reference() is None
    assert node_reference() is None
    original_error = error_reference()
    assert original_error is not None
    assert recorder.state == "INVALID"
    with pytest.raises(UnsupportedTraceError) as denied:
        _ = recorder.trace
    assert denied.value is original_error


def test_hostile_exception_formatting_cannot_break_activation_or_reduction() -> None:
    activation_error = _HostileStringError("activation")
    activation = trace_rewrites(analysis=_StringFailureAnalysis(activation_error))
    with pytest.raises(UnsupportedTraceError) as activation_caught:
        activation.__enter__()
    _assert_invalid_trace(activation, activation_caught.value)
    assert (
        "_HostileStringError" in activation_caught.value.reason
        and activation.state == "INVALID"
    )

    reduction_error = _HostileStringError("reduction")
    _HostileRootStatement.error = reduction_error
    reduction = trace_rewrites()
    with pytest.raises(UnsupportedTraceError) as reduction_caught, reduction:
        _NoOpRule().rewrite(_HostileRootStatement())
    _assert_invalid_trace(reduction, reduction_caught.value)
    assert "_HostileStringError" in reduction_caught.value.reason
