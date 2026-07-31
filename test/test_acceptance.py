from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any, cast

import pytest
from kirin import ir, types
from kirin.analysis import const
from kirin.analysis.cfg import CFG
from kirin.dialects import func, py, scf
from kirin.dialects.scf.scf2cf import ScfToCfRule
from kirin.rewrite import Chain, Fixpoint, Walk
from kirin.rewrite.abc import RewriteResult, RewriteRule
from kirin.rewrite.aggressive import Fold as AggressiveFold
from kirin.rewrite.compactify import CompactifyRegion

from kirin_rewrite_tracer import (
    Trace,
    UnsupportedTraceError,
    trace_rewrites,
)


class _ProbeStatement(ir.Statement):
    name = "acceptance.probe"


class _ConsumerStatement(ir.Statement):
    name = "acceptance.consumer"


class _ChildDoomedStatement(ir.Statement):
    name = "acceptance.child_doomed"


class _ParentDoomedStatement(ir.Statement):
    name = "acceptance.parent_doomed"


class _ChangingLeaf(RewriteRule):
    def rewrite_Statement(self, node: ir.Statement) -> RewriteResult:
        if not isinstance(node, _ProbeStatement):
            return RewriteResult()
        result = node.expect_one_result()
        if result.name == "changed":
            return RewriteResult()
        result.name = "changed"
        return RewriteResult(has_done_something=True)


class _NoOpLeaf(RewriteRule):
    pass


@dataclass
class _DispatchProbe(RewriteRule):
    handlers: list[str] = field(default_factory=list)

    def rewrite_Region(self, node: ir.Region) -> RewriteResult:
        self.handlers.append(type(node).__name__)
        return RewriteResult()

    def rewrite_Block(self, node: ir.Block) -> RewriteResult:
        self.handlers.append(type(node).__name__)
        return RewriteResult()

    def rewrite_Statement(self, node: ir.Statement) -> RewriteResult:
        self.handlers.append(type(node).__name__)
        return RewriteResult()


class _DirectRule(RewriteRule):
    def rewrite(self, node: ir.IRNode[Any]) -> RewriteResult:
        assert isinstance(node, ir.IRNode)
        return RewriteResult(has_done_something=True)


class _SuperRule(RewriteRule):
    def rewrite(self, node: ir.IRNode[Any]) -> RewriteResult:
        return super().rewrite(node)

    def rewrite_Statement(self, node: ir.Statement) -> RewriteResult:
        assert isinstance(node, ir.Statement)
        return RewriteResult(has_done_something=True)


def _result_triples(trace: Trace) -> list[tuple[bool, bool, bool] | None]:
    return [
        (
            event.result.terminated,
            event.result.has_done_something,
            event.result.exceeded_max_iter,
        )
        if event.result is not None
        else None
        for event in trace.events
    ]


def _semantic_changes(trace: Trace) -> list[bool]:
    return [
        not trace.snapshots_semantically_equal(
            event.before_snapshot_id,
            cast(str, event.after_snapshot_id),
        )
        for event in trace.events
    ]


def _orchestration_fixture(
    *, already_changed: bool = False
) -> tuple[ir.Block, Fixpoint, _ProbeStatement]:
    statement = _ProbeStatement(result_types=(types.Any,))
    if already_changed:
        statement.expect_one_result().name = "changed"
    block = ir.Block([statement])
    rule = Fixpoint(Walk(Chain(_ChangingLeaf(), _NoOpLeaf())))
    return block, rule, statement


def test_asymmetric_fifteen_event_tree_and_all_no_op_run() -> None:
    block, rule, statement = _orchestration_fixture()
    with trace_rewrites() as recorder:
        result = rule.rewrite(block)

    assert result == RewriteResult(has_done_something=True)
    assert statement.expect_one_result().name == "changed"
    trace = recorder.trace
    assert trace.complete
    assert [event.id for event in trace.events] == [
        f"event-{index}" for index in range(15)
    ]
    assert [event.sequence for event in trace.events] == list(range(15))
    assert [event.parent_id for event in trace.events] == [
        None,
        "event-0",
        "event-1",
        "event-2",
        "event-2",
        "event-1",
        "event-5",
        "event-5",
        "event-0",
        "event-8",
        "event-9",
        "event-9",
        "event-8",
        "event-12",
        "event-12",
    ]
    assert [event.sibling_ordinal for event in trace.events] == [
        0,
        0,
        0,
        0,
        1,
        1,
        0,
        1,
        1,
        0,
        0,
        1,
        1,
        0,
        1,
    ]
    changing_type = f"{__name__}._ChangingLeaf"
    no_op_type = f"{__name__}._NoOpLeaf"
    assert [event.rule_type for event in trace.events] == [
        "kirin.rewrite.fixpoint.Fixpoint",
        "kirin.rewrite.walk.Walk",
        "kirin.rewrite.chain.Chain",
        changing_type,
        no_op_type,
        "kirin.rewrite.chain.Chain",
        changing_type,
        no_op_type,
        "kirin.rewrite.walk.Walk",
        "kirin.rewrite.chain.Chain",
        changing_type,
        no_op_type,
        "kirin.rewrite.chain.Chain",
        changing_type,
        no_op_type,
    ]
    changed_indices = {0, 1, 5, 6}
    assert _result_triples(trace) == [
        (False, index in changed_indices, False) for index in range(15)
    ]
    assert _semantic_changes(trace) == [index in changed_indices for index in range(15)]
    assert len(trace.snapshots) == 30
    assert trace.operations == ()
    assert len({event.root_entity_id for event in trace.events}) == 1
    first_before = trace.index().snapshot(trace.events[0].before_snapshot_id).text
    first_after = (
        trace.index().snapshot(cast(str, trace.events[0].after_snapshot_id)).text
    )
    assert "%0 = acceptance.probe()" in first_before
    assert "%changed = acceptance.probe()" in first_after

    no_op_block, no_op_rule, _ = _orchestration_fixture(already_changed=True)
    with trace_rewrites() as no_op_recorder:
        no_op_result = no_op_rule.rewrite(no_op_block)

    assert no_op_result == RewriteResult()
    no_op_trace = no_op_recorder.trace
    assert len(no_op_trace.events) == 8
    assert [event.rule_type for event in no_op_trace.events] == [
        "kirin.rewrite.fixpoint.Fixpoint",
        "kirin.rewrite.walk.Walk",
        "kirin.rewrite.chain.Chain",
        changing_type,
        no_op_type,
        "kirin.rewrite.chain.Chain",
        changing_type,
        no_op_type,
    ]
    assert _result_triples(no_op_trace) == [(False, False, False)] * 8
    assert _semantic_changes(no_op_trace) == [False] * 8


def test_base_multiple_roots_and_dynamic_public_entry_forms() -> None:
    dispatch = _DispatchProbe()
    roots: tuple[ir.IRNode[Any], ...] = (
        ir.Region(ir.Block()),
        ir.Block(),
        _ProbeStatement(),
    )
    with trace_rewrites() as recorder:
        results = tuple(dispatch.rewrite(root) for root in roots)

    assert results == (RewriteResult(),) * 3
    assert dispatch.handlers == ["Region", "Block", "_ProbeStatement"]
    trace = recorder.trace
    assert len(trace.events) == 3
    assert [event.parent_id for event in trace.events] == [None, None, None]
    assert [event.sibling_ordinal for event in trace.events] == [0, 1, 2]
    assert len({event.root_entity_id for event in trace.events}) == 3

    prebound_rule = _DirectRule()
    prebound = prebound_rule.rewrite
    unbound_rule = _DirectRule()
    with trace_rewrites() as forms_recorder:
        prebound_result = prebound(_ProbeStatement())
        unbound_result = _DirectRule.rewrite(unbound_rule, _ProbeStatement())

        class LateRule(RewriteRule):
            def rewrite(self, node: ir.IRNode[Any]) -> RewriteResult:
                assert isinstance(self, LateRule)
                assert isinstance(node, ir.IRNode)
                return RewriteResult(has_done_something=True)

        late_result = LateRule().rewrite(_ProbeStatement())
        super_result = _SuperRule().rewrite(_ProbeStatement())

    assert all(
        result.has_done_something
        for result in (
            prebound_result,
            unbound_result,
            late_result,
            super_result,
        )
    )
    forms = forms_recorder.trace.events
    assert [event.rule_type.rsplit(".", 1)[-1] for event in forms] == [
        "_DirectRule",
        "_DirectRule",
        "LateRule",
        "_SuperRule",
        "_SuperRule",
    ]
    assert [event.parent_id for event in forms] == [
        None,
        None,
        None,
        None,
        "event-3",
    ]
    assert [event.sibling_ordinal for event in forms] == [0, 1, 2, 3, 0]


def test_pinned_direct_override_owners_use_uniform_event_shape() -> None:
    region = ir.Region(ir.Block())
    compactify = CompactifyRegion(CFG(region))
    cast(Any, compactify).rule = _NoOpLeaf()
    with trace_rewrites() as compactify_recorder:
        compactify_result = compactify.rewrite(region)

    assert compactify_result == RewriteResult()
    assert [event.rule_type for event in compactify_recorder.trace.events] == [
        "kirin.rewrite.compactify.CompactifyRegion",
        f"{__name__}._NoOpLeaf",
    ]
    assert [event.parent_id for event in compactify_recorder.trace.events] == [
        None,
        "event-0",
    ]

    constant_none = func.ConstantNone()  # type: ignore[call-arg]
    aggressive = AggressiveFold(const.Frame(constant_none))
    aggressive.rule = _NoOpLeaf()
    with trace_rewrites() as aggressive_recorder:
        aggressive_result = aggressive.rewrite(ir.Block())

    assert aggressive_result == RewriteResult()
    assert [event.rule_type for event in aggressive_recorder.trace.events] == [
        "kirin.rewrite.aggressive.fold.Fold",
        f"{__name__}._NoOpLeaf",
    ]

    desugar_module = import_module("kirin.dialects.vmath.rewrites.desugar")
    desugar_type = cast(
        type[RewriteRule],
        vars(desugar_module)["WalkDesugarBinop"],
    )
    with trace_rewrites() as desugar_recorder:
        desugar_result = desugar_type().rewrite(py.Constant(0))

    assert desugar_result == RewriteResult()
    assert [event.rule_type for event in desugar_recorder.trace.events] == [
        "kirin.dialects.vmath.rewrites.desugar.WalkDesugarBinop",
        "kirin.rewrite.walk.Walk",
        "kirin.dialects.vmath.rewrites.desugar.DesugarBinOp",
    ]
    assert [event.parent_id for event in desugar_recorder.trace.events] == [
        None,
        "event-0",
        "event-1",
    ]
    assert all(
        event.completion == "complete"
        for event in (
            *compactify_recorder.trace.events,
            *aggressive_recorder.trace.events,
            *desugar_recorder.trace.events,
        )
    )


def _scf_bypass_nodes() -> tuple[ir.Statement, ir.Statement]:
    iterable = py.Constant(0)
    loop = scf.For(
        iterable.result,
        ir.Region(ir.Block(argtypes=(types.Any,))),
    )
    condition = py.Constant(True)
    conditional = scf.IfElse(
        condition.result,
        ir.Block(),
        ir.Block(),
    )
    return loop, conditional


def test_pinned_scf_cross_instance_specialized_bypasses_invalidate() -> None:
    for node in _scf_bypass_nodes():
        recorder = trace_rewrites()
        immediate: UnsupportedTraceError | None = None
        with pytest.raises(UnsupportedTraceError) as exit_error, recorder:
            try:
                ScfToCfRule().rewrite(node)
            except UnsupportedTraceError as error:
                immediate = error

        assert immediate is not None
        assert exit_error.value is immediate
        assert recorder.state == "INVALID"
        with pytest.raises(UnsupportedTraceError) as denied:
            _ = recorder.trace
        assert denied.value is immediate


_INCOMPLETE_SENTINEL = RuntimeError("acceptance child failure")


@dataclass
class _FailingChild(RewriteRule):
    source: ir.SSAValue
    destination: ir.SSAValue
    doomed: _ChildDoomedStatement

    def rewrite_Block(self, node: ir.Block) -> RewriteResult:
        assert isinstance(node, ir.Block)
        self.source.replace_by(self.destination)
        self.doomed.delete()
        raise _INCOMPLETE_SENTINEL


@dataclass
class _IncompleteParent(RewriteRule):
    child: _FailingChild
    doomed: _ParentDoomedStatement
    catch: bool

    def rewrite(self, node: ir.IRNode[Any]) -> RewriteResult:
        if self.catch:
            try:
                self.child.rewrite(node)
            except RuntimeError as error:
                assert error is _INCOMPLETE_SENTINEL
            self.doomed.delete()
            return RewriteResult(
                terminated=True,
                has_done_something=True,
                exceeded_max_iter=True,
            )
        return self.child.rewrite(node)


@dataclass
class _IncompleteFixture:
    block: ir.Block
    old_owner: _ProbeStatement
    new_owner: _ProbeStatement
    consumer: _ConsumerStatement
    child_doomed: _ChildDoomedStatement
    parent_doomed: _ParentDoomedStatement
    parent: _IncompleteParent


def _incomplete_fixture(*, catch: bool) -> _IncompleteFixture:
    old_owner = _ProbeStatement(result_types=(types.Any,))
    old_owner.expect_one_result().name = "old"
    new_owner = _ProbeStatement(result_types=(types.Any,))
    new_owner.expect_one_result().name = "new"
    consumer = _ConsumerStatement(args=(old_owner.expect_one_result(),))
    child_doomed = _ChildDoomedStatement()
    parent_doomed = _ParentDoomedStatement()
    block = ir.Block(
        [
            old_owner,
            new_owner,
            consumer,
            child_doomed,
            parent_doomed,
        ]
    )
    child = _FailingChild(
        old_owner.expect_one_result(),
        new_owner.expect_one_result(),
        child_doomed,
    )
    parent = _IncompleteParent(child, parent_doomed, catch)
    return _IncompleteFixture(
        block,
        old_owner,
        new_owner,
        consumer,
        child_doomed,
        parent_doomed,
        parent,
    )


def _assert_child_provenance(trace: Trace) -> None:
    assert [
        (operation.api, operation.outcome, operation.owner_event_id)
        for operation in trace.operations[:2]
    ] == [
        ("SSAValue.replace_by", "completed", "event-1"),
        ("Statement.delete", "completed", "event-1"),
    ]
    retarget = trace.relations[0]
    assert retarget.basis == "ssa_uses_retargeted_to"
    assert retarget.mutation_operation_id == trace.operations[0].id
    assert retarget.source_entity_id == trace.operations[0].source_entity_ids[0]
    assert (
        retarget.destination_entity_id == trace.operations[0].destination_entity_ids[0]
    )
    child_effect = trace.effects[0]
    assert child_effect.kind == "statement_delete_completed"
    assert child_effect.mutation_operation_id == trace.operations[1].id
    assert (
        trace.index()
        .entity(child_effect.affected_entity_id)
        .qualified_type.endswith("._ChildDoomedStatement")
    )


def test_caught_incomplete_child_retains_exact_completed_provenance() -> None:
    fixture = _incomplete_fixture(catch=True)
    with trace_rewrites() as recorder:
        result = fixture.parent.rewrite(fixture.block)

    assert result == RewriteResult(
        terminated=True,
        has_done_something=True,
        exceeded_max_iter=True,
    )
    assert tuple(fixture.block.stmts) == (
        fixture.old_owner,
        fixture.new_owner,
        fixture.consumer,
    )
    assert fixture.consumer.args[0] is fixture.new_owner.expect_one_result()
    assert fixture.child_doomed.parent_node is None
    assert fixture.parent_doomed.parent_node is None

    trace = recorder.trace
    assert not trace.complete
    parent, child = trace.events
    assert (
        parent.completion,
        parent.parent_id,
        parent.after_snapshot_id is not None,
    ) == ("complete", None, True)
    assert (
        child.completion,
        child.parent_id,
        child.after_snapshot_id,
        child.result,
    ) == ("incomplete", "event-0", None, None)
    assert _result_triples(trace) == [(True, True, True), None]
    assert [
        (operation.api, operation.outcome, operation.owner_event_id)
        for operation in trace.operations
    ] == [
        ("SSAValue.replace_by", "completed", "event-1"),
        ("Statement.delete", "completed", "event-1"),
        ("Statement.delete", "completed", "event-0"),
    ]
    _assert_child_provenance(trace)
    assert len(trace.effects) == 2
    parent_effect = trace.effects[1]
    assert parent_effect.mutation_operation_id == trace.operations[2].id
    assert (
        trace.index()
        .entity(parent_effect.affected_entity_id)
        .qualified_type.endswith("._ParentDoomedStatement")
    )


def test_propagated_incomplete_frames_preserve_exception_identity() -> None:
    fixture = _incomplete_fixture(catch=False)
    with pytest.raises(RuntimeError) as propagated, trace_rewrites() as recorder:
        fixture.parent.rewrite(fixture.block)

    assert propagated.value is _INCOMPLETE_SENTINEL
    assert tuple(fixture.block.stmts) == (
        fixture.old_owner,
        fixture.new_owner,
        fixture.consumer,
        fixture.parent_doomed,
    )
    assert fixture.consumer.args[0] is fixture.new_owner.expect_one_result()
    assert fixture.child_doomed.parent_node is None
    assert fixture.parent_doomed.parent_node is fixture.block

    trace = recorder.trace
    assert not trace.complete
    assert [
        (
            event.completion,
            event.parent_id,
            event.after_snapshot_id,
            event.result,
        )
        for event in trace.events
    ] == [
        ("incomplete", None, None, None),
        ("incomplete", "event-0", None, None),
    ]
    assert len(trace.operations) == 2
    assert len(trace.relations) == 1
    assert len(trace.effects) == 1
    _assert_child_provenance(trace)
