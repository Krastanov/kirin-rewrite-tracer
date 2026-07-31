"""Transactional interception of Kirin's selected mutation surface."""

from __future__ import annotations

import inspect
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from types import CodeType, FrameType, FunctionType
from typing import NoReturn, Protocol, cast

from kirin.ir import Block, Region, SSAValue, Statement
from kirin.ir.attrs.abc import Attribute
from kirin.ir.ssa import DeletedSSAValue

from ._builder import _TraceBuilder
from ._model import EntityEffect, MutationOperation, ProvenanceRelation
from ._stack import capture_invocation_stack

_STATEMENT_REPLACE = "Statement.replace_by"
_SSA_REPLACE = "SSAValue.replace_by"
_STATEMENT_COPY = "Statement.from_stmt"
_REGION_CLONE = "Region.clone"
_STATEMENT_DELETE = "Statement.delete"


@dataclass(frozen=True, slots=True)
class _OperationHandle:
    index: int
    id: str
    owner_event_id: str


@dataclass(frozen=True, slots=True)
class _CompletionFacts:
    sources: tuple[object, ...]
    destinations: tuple[object, ...]
    relations: tuple[tuple[str, object, object], ...] = ()
    effect: tuple[str, object] | None = None


@dataclass(frozen=True, slots=True)
class _PreparedOperation:
    initial_sources: tuple[object, ...]
    initial_destinations: tuple[object, ...]
    completion: Callable[[object], _CompletionFacts]


class _MutationRecorder(Protocol):
    """The small session-facing surface required by mutation wrappers."""

    def has_active_event(self) -> bool: ...

    def begin_operation(
        self,
        *,
        api: str,
        sources: tuple[object, ...],
        destinations: tuple[object, ...],
        caller_frame: FrameType,
        excluded_codes: tuple[CodeType, ...],
    ) -> _OperationHandle | None: ...

    def complete_operation(
        self, handle: _OperationHandle | None, facts: _CompletionFacts
    ) -> None: ...

    def abort_operation(self, handle: _OperationHandle | None) -> None: ...

    def invalidate(self, reason: str) -> NoReturn: ...

    def mark_invalid(self, reason: str) -> None:
        """Store unsupported use without disturbing an exception already in flight."""
        ...


class _BuilderMutationRecorder:
    """Adapt a mutable trace builder and active-event stack to the wrapper protocol."""

    __slots__ = (
        "_active_event_id",
        "_builder",
        "_invalidate",
        "_mark_invalid",
        "_open",
    )

    def __init__(
        self,
        builder: _TraceBuilder,
        *,
        active_event_id: Callable[[], str | None],
        invalidate: Callable[[str], NoReturn],
        mark_invalid: Callable[[str], None],
    ) -> None:
        self._builder = builder
        self._active_event_id = active_event_id
        self._invalidate = invalidate
        self._mark_invalid = mark_invalid
        self._open: list[_OperationHandle] = []

    def invalidate(self, reason: str) -> NoReturn:
        self._invalidate(reason)

    def has_active_event(self) -> bool:
        return self._active_event_id() is not None

    def mark_invalid(self, reason: str) -> None:
        self._mark_invalid(reason)

    def begin_operation(
        self,
        *,
        api: str,
        sources: tuple[object, ...],
        destinations: tuple[object, ...],
        caller_frame: FrameType,
        excluded_codes: tuple[CodeType, ...],
    ) -> _OperationHandle | None:
        owner_event_id = self._active_event_id()
        if owner_event_id is None:
            return None
        if self._open and self._open[-1].owner_event_id != owner_event_id:
            self.invalidate("a selected mutation crossed rewrite-event ownership")

        source_ids = self._register_operands(sources)
        destination_ids = self._register_operands(destinations)
        frames = capture_invocation_stack(
            caller_frame,
            excluded_codes=excluded_codes,
        )
        stack_id = self._builder.add_stack(frames)
        operation_id = self._builder.next_id("operation")
        handle = _OperationHandle(
            index=len(self._builder.operations),
            id=operation_id,
            owner_event_id=owner_event_id,
        )
        self._builder.operations.append(
            MutationOperation(
                id=operation_id,
                sequence=handle.index,
                owner_event_id=owner_event_id,
                parent_operation_id=self._open[-1].id if self._open else None,
                api=api,
                outcome="incomplete",
                source_entity_ids=source_ids,
                destination_entity_ids=destination_ids,
                invocation_stack_id=stack_id,
            )
        )
        self._open.append(handle)
        return handle

    def complete_operation(
        self, handle: _OperationHandle | None, facts: _CompletionFacts
    ) -> None:
        if handle is None:
            return
        self._require_innermost(handle)

        source_ids = self._register_operands(facts.sources)
        destination_ids = self._register_operands(facts.destinations)
        operation = self._builder.operations[handle.index]
        completed = replace(
            operation,
            outcome="completed",
            source_entity_ids=source_ids,
            destination_entity_ids=destination_ids,
        )

        relations: list[ProvenanceRelation] = []
        for basis, source, destination in facts.relations:
            relations.append(
                ProvenanceRelation(
                    id=self._builder.next_id("relation"),
                    basis=basis,
                    source_entity_id=self._register_entity(source),
                    destination_entity_id=self._register_entity(destination),
                    mutation_operation_id=handle.id,
                )
            )

        effect: EntityEffect | None = None
        if facts.effect is not None:
            kind, affected = facts.effect
            effect = EntityEffect(
                id=self._builder.next_id("effect"),
                kind=kind,
                affected_entity_id=self._register_entity(affected),
                mutation_operation_id=handle.id,
            )

        self._builder.operations[handle.index] = completed
        self._builder.relations.extend(relations)
        if effect is not None:
            self._builder.effects.append(effect)
        self._open.pop()

    def abort_operation(self, handle: _OperationHandle | None) -> None:
        if handle is None:
            return
        self._require_innermost(handle)
        self._open.pop()

    def _require_innermost(self, handle: _OperationHandle) -> None:
        if not self._open or self._open[-1] is not handle:
            self.invalidate("selected mutation operations did not close in LIFO order")

    def _register_operands(self, values: tuple[object, ...]) -> tuple[str, ...]:
        result: list[str] = []
        for value in values:
            entity_id = self._register_entity(value)
            if entity_id not in result:
                result.append(entity_id)
        return tuple(result)

    def _register_entity(self, value: object) -> str:
        qualified_type = f"{type(value).__module__}.{type(value).__qualname__}"
        if isinstance(value, Region):
            return self._builder.register_entity(
                value,
                kind="region",
                qualified_type=qualified_type,
            )
        if isinstance(value, Block):
            return self._builder.register_entity(
                value,
                kind="block",
                qualified_type=qualified_type,
            )
        if isinstance(value, Statement):
            return self._builder.register_entity(
                value,
                kind="statement",
                qualified_type=qualified_type,
            )
        if isinstance(value, SSAValue):
            owner_id = self._register_entity(value.owner)
            return self._builder.register_entity(
                value,
                kind="ssa",
                qualified_type=qualified_type,
                defining_owner_id=owner_id,
            )
        raise TypeError(
            "selected mutation operand has unsupported type "
            f"{type(value).__module__}.{type(value).__qualname__}"
        )


@dataclass(frozen=True, slots=True)
class _RawDescriptor:
    owner: type[object]
    name: str
    api: str
    receiver_local: str
    saved: object
    function: FunctionType

    @property
    def code(self) -> CodeType:
        return self.function.__code__


@dataclass(frozen=True, slots=True)
class _InstallTarget:
    raw: _RawDescriptor
    wrapper: object


@dataclass(slots=True)
class _ExpectedCall:
    raw: _RawDescriptor
    receiver: object
    consumed: bool = False
    invalidated: bool = False


class _MutationInterceptors:
    """Install and own the five exact pinned Kirin mutation descriptors."""

    __slots__ = (
        "_excluded_codes",
        "_expected",
        "_installed",
        "_recorder",
        "_set_attribute",
        "_targets",
    )

    def __init__(
        self,
        recorder: _MutationRecorder,
        *,
        set_attribute: Callable[[type[object], str, object], None] = setattr,
    ) -> None:
        self._recorder = recorder
        self._set_attribute = set_attribute
        raw = (
            _read_raw(Statement, "replace_by", _STATEMENT_REPLACE, "self"),
            _read_raw(SSAValue, "replace_by", _SSA_REPLACE, "self"),
            _read_raw(
                Statement, "from_stmt", _STATEMENT_COPY, "cls", classmethod_=True
            ),
            _read_raw(Region, "clone", _REGION_CLONE, "self"),
            _read_raw(Statement, "delete", _STATEMENT_DELETE, "self"),
        )
        wrappers = self._make_wrappers()
        self._targets = tuple(_InstallTarget(item, wrappers[item.api]) for item in raw)
        self._expected: list[_ExpectedCall] = []
        self._installed: list[_InstallTarget] = []
        self._excluded_codes = (
            *(
                _descriptor_function(target.wrapper).__code__
                for target in self._targets
            ),
            type(self)._invoke.__code__,
        )

    @property
    def raw_descriptors(self) -> tuple[object, ...]:
        return tuple(target.raw.saved for target in self._targets)

    @property
    def installed_descriptors(self) -> tuple[object, ...]:
        return tuple(target.wrapper for target in self._targets)

    @property
    def selected_codes(self) -> tuple[CodeType, ...]:
        return tuple(target.raw.code for target in self._targets)

    def install(self) -> None:
        if self._installed:
            raise RuntimeError("mutation interceptors are already installed")
        try:
            for target in self._targets:
                current = vars(target.raw.owner).get(target.raw.name)
                if current is not target.raw.saved:
                    raise RuntimeError(
                        f"{target.raw.api} changed before interceptor installation"
                    )
                self._installed.append(target)
                self._set_attribute(
                    target.raw.owner,
                    target.raw.name,
                    target.wrapper,
                )
                if vars(target.raw.owner).get(target.raw.name) is not target.wrapper:
                    raise RuntimeError(
                        f"{target.raw.api} wrapper installation did not take effect"
                    )
        except BaseException:
            self._restore_installed(report_foreign=False)
            raise

    def uninstall(self) -> None:
        self._restore_installed(report_foreign=True)

    def authorize_profile_call(self, frame: FrameType) -> bool:
        """Consume one wrapper-issued token for a selected saved-code entry."""

        raw = next(
            (target.raw for target in self._targets if frame.f_code is target.raw.code),
            None,
        )
        if raw is None:
            return False
        if not self._expected:
            self._recorder.invalidate(
                f"{raw.api} entered without its installed interception wrapper"
            )
        expected = self._expected[-1]
        if expected.consumed:
            expected.invalidated = True
            self._recorder.invalidate(f"{raw.api} reused a consumed delegation token")
        if expected.raw.code is not frame.f_code:
            expected.invalidated = True
            self._recorder.invalidate(
                f"{raw.api} did not match the expected selected delegation"
            )
        receiver = frame.f_locals.get(raw.receiver_local)
        if receiver is not expected.receiver:
            expected.invalidated = True
            self._recorder.invalidate(
                f"{raw.api} entered with an unexpected receiver or class"
            )
        expected.consumed = True
        return True

    def _restore_installed(self, *, report_foreign: bool) -> None:
        for target in reversed(self._installed):
            current = vars(target.raw.owner).get(target.raw.name)
            if current is target.wrapper:
                self._set_attribute(
                    target.raw.owner,
                    target.raw.name,
                    target.raw.saved,
                )
            elif report_foreign and current is not target.raw.saved:
                self._recorder.mark_invalid(
                    f"{target.raw.api} was replaced while tracing"
                )
        self._installed.clear()

    def _make_wrappers(self) -> dict[str, object]:
        interceptor = self

        def statement_replace_by(self: Statement, stmt: Statement) -> None:
            caller = sys._getframe(1)

            def prepare() -> _PreparedOperation:
                facts = _CompletionFacts(
                    sources=(self,),
                    destinations=(stmt,),
                    relations=(("statement_replaced_by", self, stmt),),
                )
                return _PreparedOperation(
                    initial_sources=(self,),
                    initial_destinations=(stmt,),
                    completion=lambda _result: facts,
                )

            interceptor._invoke(
                _STATEMENT_REPLACE,
                self,
                (stmt,),
                caller,
                prepare=prepare,
            )

        def ssa_replace_by(self: SSAValue, other: SSAValue) -> None:
            caller = sys._getframe(1)

            def prepare() -> _PreparedOperation:
                had_uses = bool(self.uses)
                relations: tuple[tuple[str, object, object], ...] = ()
                if had_uses and not isinstance(other, DeletedSSAValue):
                    relations = (("ssa_uses_retargeted_to", self, other),)
                facts = _CompletionFacts(
                    sources=(self,),
                    destinations=(other,),
                    relations=relations,
                )
                return _PreparedOperation(
                    initial_sources=(self,),
                    initial_destinations=(other,),
                    completion=lambda _result: facts,
                )

            interceptor._invoke(
                _SSA_REPLACE,
                self,
                (other,),
                caller,
                prepare=prepare,
            )

        def statement_from_stmt(
            cls: type[Statement],
            other: Statement,
            args: Sequence[SSAValue] | None = None,
            regions: list[Region] | None = None,
            successors: list[Block] | None = None,
            attributes: dict[str, Attribute] | None = None,
        ) -> Statement:
            caller = sys._getframe(1)

            def prepare() -> _PreparedOperation:
                source_results = tuple(other.results)

                def completion(result: object) -> _CompletionFacts:
                    if not isinstance(result, Statement):
                        interceptor._recorder.invalidate(
                            "Statement.from_stmt returned a non-Statement result"
                        )
                    copied = result
                    copied_results = tuple(copied.results)
                    if len(source_results) != len(copied_results):
                        interceptor._recorder.invalidate(
                            "Statement.from_stmt returned an unpairable "
                            "result inventory"
                        )
                    relations: list[tuple[str, object, object]] = [
                        ("statement_copied_to", other, copied)
                    ]
                    relations.extend(
                        ("result_copied_to", source, destination)
                        for source, destination in zip(
                            source_results, copied_results, strict=True
                        )
                    )
                    return _CompletionFacts(
                        sources=(other, *source_results),
                        destinations=(copied, *copied_results),
                        relations=tuple(relations),
                    )

                return _PreparedOperation(
                    initial_sources=(other, *source_results),
                    initial_destinations=(),
                    completion=completion,
                )

            result = interceptor._invoke(
                _STATEMENT_COPY,
                cls,
                (other, args, regions, successors, attributes),
                caller,
                prepare=prepare,
            )
            return cast(Statement, result)

        def region_clone(
            self: Region,
            ssamap: dict[SSAValue, SSAValue] | None = None,
        ) -> Region:
            caller = sys._getframe(1)

            def prepare() -> _PreparedOperation:
                source_blocks = tuple(self.blocks)
                source_arguments_by_block = tuple(
                    tuple(block.args) for block in source_blocks
                )
                source_arguments = tuple(
                    argument
                    for arguments in source_arguments_by_block
                    for argument in arguments
                )

                def completion(result: object) -> _CompletionFacts:
                    if not isinstance(result, Region):
                        interceptor._recorder.invalidate(
                            "Region.clone returned a non-Region result"
                        )
                    cloned = result
                    cloned_blocks = tuple(cloned.blocks)
                    if len(source_blocks) != len(cloned_blocks):
                        interceptor._recorder.invalidate(
                            "Region.clone returned an unpairable direct block inventory"
                        )
                    relations: list[tuple[str, object, object]] = [
                        ("region_cloned_to", self, cloned)
                    ]
                    relations.extend(
                        ("block_cloned_to", source, destination)
                        for source, destination in zip(
                            source_blocks, cloned_blocks, strict=True
                        )
                    )
                    cloned_arguments: list[SSAValue] = []
                    for _source, source_arguments_for_block, destination in zip(
                        source_blocks,
                        source_arguments_by_block,
                        cloned_blocks,
                        strict=True,
                    ):
                        destination_arguments = tuple(destination.args)
                        if len(source_arguments_for_block) != len(
                            destination_arguments
                        ):
                            interceptor._recorder.invalidate(
                                "Region.clone returned an unpairable "
                                "block argument inventory"
                            )
                        cloned_arguments.extend(destination_arguments)
                        relations.extend(
                            ("block_argument_cloned_to", old_arg, new_arg)
                            for old_arg, new_arg in zip(
                                source_arguments_for_block,
                                destination_arguments,
                                strict=True,
                            )
                        )
                    return _CompletionFacts(
                        sources=(self, *source_blocks, *source_arguments),
                        destinations=(cloned, *cloned_blocks, *cloned_arguments),
                        relations=tuple(relations),
                    )

                return _PreparedOperation(
                    initial_sources=(self, *source_blocks, *source_arguments),
                    initial_destinations=(),
                    completion=completion,
                )

            result = interceptor._invoke(
                _REGION_CLONE,
                self,
                (ssamap,),
                caller,
                prepare=prepare,
            )
            return cast(Region, result)

        def statement_delete(self: Statement, safe: bool = True) -> None:
            caller = sys._getframe(1)

            def prepare() -> _PreparedOperation:
                facts = _CompletionFacts(
                    sources=(self,),
                    destinations=(),
                    effect=("statement_delete_completed", self),
                )
                return _PreparedOperation(
                    initial_sources=(self,),
                    initial_destinations=(),
                    completion=lambda _result: facts,
                )

            interceptor._invoke(
                _STATEMENT_DELETE,
                self,
                (safe,),
                caller,
                prepare=prepare,
            )

        return {
            _STATEMENT_REPLACE: statement_replace_by,
            _SSA_REPLACE: ssa_replace_by,
            _STATEMENT_COPY: classmethod(statement_from_stmt),
            _REGION_CLONE: region_clone,
            _STATEMENT_DELETE: statement_delete,
        }

    def _invoke(
        self,
        api: str,
        receiver: object,
        arguments: tuple[object, ...],
        caller_frame: FrameType,
        *,
        prepare: Callable[[], _PreparedOperation],
    ) -> object:
        raw = next(target.raw for target in self._targets if target.raw.api == api)
        prepared: _PreparedOperation | None = None
        handle: _OperationHandle | None = None
        if self._recorder.has_active_event():
            preparation_failure: str | None = None
            try:
                prepared = prepare()
                handle = self._recorder.begin_operation(
                    api=api,
                    sources=prepared.initial_sources,
                    destinations=prepared.initial_destinations,
                    caller_frame=caller_frame,
                    excluded_codes=self._excluded_codes,
                )
            except Exception as error:
                preparation_failure = (
                    f"{api} pre-call capture failed: "
                    f"{type(error).__module__}.{type(error).__qualname__}"
                )
            except BaseException:
                self._recorder.mark_invalid(f"{api} pre-call capture was interrupted")
                raise
            if preparation_failure is not None:
                self._recorder.invalidate(preparation_failure)
        expected = _ExpectedCall(raw=raw, receiver=receiver)
        self._expected.append(expected)
        try:
            try:
                result = raw.function(receiver, *arguments)
            except BaseException:
                try:
                    self._recorder.abort_operation(handle)
                except BaseException:
                    self._recorder.mark_invalid(
                        f"{api} failed while closing an incomplete operation"
                    )
                raise
            else:
                if prepared is not None:
                    completion_failure: str | None = None
                    try:
                        facts = prepared.completion(result)
                        self._recorder.complete_operation(handle, facts)
                    except Exception as error:
                        completion_failure = (
                            f"{api} post-call capture failed: "
                            f"{type(error).__module__}.{type(error).__qualname__}"
                        )
                    except BaseException:
                        self._recorder.mark_invalid(
                            f"{api} post-call capture was interrupted"
                        )
                        raise
                    if completion_failure is not None:
                        try:
                            self._recorder.abort_operation(handle)
                        except BaseException:
                            self._recorder.mark_invalid(
                                f"{api} failed while abandoning capture"
                            )
                        self._recorder.invalidate(completion_failure)
                return result
        finally:
            exception_active = sys.exc_info()[0] is not None
            self._close_expected(expected, exception_active=exception_active)

    def _close_expected(
        self, expected: _ExpectedCall, *, exception_active: bool
    ) -> None:
        if not self._expected or self._expected[-1] is not expected:
            reason = "selected mutation delegation tokens did not close in LIFO order"
            if exception_active:
                self._recorder.mark_invalid(reason)
                return
            self._recorder.invalidate(reason)
        self._expected.pop()
        if not expected.consumed and not expected.invalidated:
            reason = f"{expected.raw.api} exited without consuming its delegation token"
            if exception_active:
                self._recorder.mark_invalid(reason)
            else:
                self._recorder.invalidate(reason)


def _read_raw(
    owner: type[object],
    name: str,
    api: str,
    receiver_local: str,
    *,
    classmethod_: bool = False,
) -> _RawDescriptor:
    raw = vars(owner).get(name)
    if classmethod_:
        if type(raw) is not classmethod:
            raise RuntimeError(f"{api} is not the expected raw classmethod")
        function = raw.__wrapped__
    else:
        if not inspect.isfunction(raw):
            raise RuntimeError(f"{api} is not the expected raw Python function")
        function = raw
    if not isinstance(function, FunctionType):
        raise RuntimeError(f"{api} does not carry an ordinary Python function")
    return _RawDescriptor(owner, name, api, receiver_local, raw, function)


def _descriptor_function(descriptor: object) -> FunctionType:
    function: object = (
        descriptor.__wrapped__ if type(descriptor) is classmethod else descriptor
    )
    if not isinstance(function, FunctionType):
        raise RuntimeError("tracer wrapper is not an ordinary Python function")
    return function
