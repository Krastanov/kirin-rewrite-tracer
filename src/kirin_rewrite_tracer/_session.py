"""Transactional public rewrite-tracing sessions."""

from __future__ import annotations

import inspect
import sys
import weakref
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from types import CodeType, FrameType, FunctionType, TracebackType
from typing import Any, Literal, NoReturn, cast

from kirin.ir import Block, IRNode, Region, SSAValue, Statement
from kirin.rewrite.abc import RewriteResult, RewriteRule

from ._builder import _TraceBuilder
from ._compat import (
    PINNED_KIRIN_COMMIT,
    CompatibilityError,
    CompatibilityReport,
    preflight_compatibility,
)
from ._model import RewriteEvent, RewriteResultRecord, Trace
from ._mutation import _BuilderMutationRecorder, _MutationInterceptors
from ._snapshot import _SnapshotAdapter
from ._stack import capture_invocation_stack

_RecorderState = Literal["CREATED", "ACTIVE", "FROZEN", "INVALID"]
_FrameKind = Literal["public", "region", "block", "statement"]
_ProfileCallback = Callable[[FrameType, str, object], object]


class TraceStateError(RuntimeError):
    """Raised when a recorder has no valid frozen trace in its current state."""


class UnsupportedTraceError(RuntimeError):
    """Raised when execution leaves the deliberately narrow v1 support envelope."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True, slots=True)
class _FrameClassification:
    kind: _FrameKind
    rule: RewriteRule
    node: IRNode[Any]
    function: FunctionType


@dataclass(slots=True)
class _EventShell:
    frame: FrameType
    rule: RewriteRule
    root: IRNode[Any]
    event_id: str
    index: int


_SPECIALIZED_TYPES: dict[str, tuple[_FrameKind, type[IRNode[Any]]]] = {
    "rewrite_Region": ("region", Region),
    "rewrite_Block": ("block", Block),
    "rewrite_Statement": ("statement", Statement),
}
_METHOD_NAMES = ("rewrite", *tuple(_SPECIALIZED_TYPES))
_BASE_CODES = tuple(
    cast(FunctionType, vars(RewriteRule)[name]).__code__ for name in _METHOD_NAMES
)
_MISSING = object()
_active_recorder: TraceRecorder | None = None


def _qualified_type(value: object) -> str:
    return f"{type(value).__module__}.{type(value).__qualname__}"


def _exception_type(error: BaseException) -> str:
    """Describe an exception without invoking user-controlled formatting."""

    return f"{type(error).__module__}.{type(error).__qualname__}"


class _TracebackScrubber:
    """An unreachable cycle whose finalizer scrubs a propagated stable error."""

    __slots__ = ("__weakref__", "cycle")

    def __init__(self) -> None:
        self.cycle = self


def _clear_error_traceback(error: UnsupportedTraceError) -> None:
    error.__traceback__ = None
    error.__context__ = None
    error.__cause__ = None


def _schedule_traceback_scrub(error: UnsupportedTraceError) -> None:
    scrubber = _TracebackScrubber()
    finalizer = weakref.finalize(scrubber, _clear_error_traceback, error)
    cast(Any, finalizer).atexit = False


def _code_is(candidate: CodeType, choices: tuple[CodeType, ...]) -> bool:
    return any(candidate is choice for choice in choices)


class TraceRecorder:
    """One-shot context manager that freezes one immutable rewrite trace."""

    __slots__ = (
        "_adapter",
        "_analysis_copy",
        "_analysis_input",
        "_builder",
        "_callback",
        "_cleaning",
        "_configuration_id",
        "_entered",
        "_error",
        "_events",
        "_instrumented",
        "_mutation_recorder",
        "_mutations",
        "_report",
        "_sibling_counts",
        "_state",
        "_trace",
    )

    def __init__(self, *, analysis: Mapping[SSAValue, object] | None = None) -> None:
        self._state: _RecorderState = "CREATED"
        self._trace: Trace | None = None
        self._error: UnsupportedTraceError | None = None
        self._analysis_input = analysis
        self._analysis_copy: dict[SSAValue, object] | None = None
        self._report: CompatibilityReport | None = None
        self._builder: _TraceBuilder | None = None
        self._configuration_id: str | None = None
        self._adapter: _SnapshotAdapter | None = None
        self._mutation_recorder: _BuilderMutationRecorder | None = None
        self._mutations: _MutationInterceptors | None = None
        self._callback: _ProfileCallback | None = None
        self._events: list[_EventShell] = []
        self._sibling_counts: dict[str | None, int] = {}
        self._entered = False
        self._instrumented = False
        self._cleaning = False

    @property
    def state(self) -> str:
        """Return the recorder's stable lifecycle state name."""

        return self._state

    @property
    def trace(self) -> Trace:
        """Return the frozen trace, or reject access in every other state."""

        if self._state == "FROZEN":
            trace = self._trace
            if trace is None:  # pragma: no cover - defensive invariant
                raise TraceStateError("frozen recorder lost its trace")
            return trace
        if self._state == "INVALID":
            self._raise_stored_error()
        raise TraceStateError(
            f"trace is unavailable while recorder state is {self._state}"
        )

    def __enter__(self) -> TraceRecorder:
        global _active_recorder

        if self._state == "INVALID":
            self._raise_stored_error()
        if self._state != "CREATED":
            raise TraceStateError("a TraceRecorder can be entered only once")

        activation_failure: str
        try:
            report = preflight_compatibility(
                active_session=_active_recorder is not None
            )
            analysis = self._copy_analysis()
            self._analysis_input = None
            builder = _TraceBuilder()
            mutation_recorder = _BuilderMutationRecorder(
                builder,
                active_event_id=self._active_event_id,
                invalidate=self._invalidate,
                mark_invalid=self._mark_invalid,
            )
            mutations = _MutationInterceptors(mutation_recorder)
            expected_descriptors = tuple(
                descriptor for _owner, _name, descriptor in report.descriptors.items()
            )
            if mutations.raw_descriptors != expected_descriptors:
                raise RuntimeError(
                    "mutation descriptors changed between preflight and installation"
                )

            self._report = report
            self._analysis_copy = analysis
            self._builder = builder
            self._mutation_recorder = mutation_recorder
            self._mutations = mutations
            callback = self._make_profile_callback()
            self._callback = callback

            mutations.install()
            self._instrumented = True
            if _active_recorder is not None:
                raise CompatibilityError(
                    "active-session",
                    "another trace session became active during activation",
                )
            if sys.getprofile() is not None:
                raise CompatibilityError(
                    "profile-occupied",
                    "the current thread profile slot became occupied during activation",
                )
            self._state = "ACTIVE"
            self._entered = True
            _active_recorder = self
            sys.setprofile(callback)
            if sys.getprofile() is not callback:
                raise RuntimeError("the tracing profile callback was not retained")
            return self
        except CompatibilityError as error:
            activation_failure = (
                f"compatibility preflight failed: {error.code}: {error.detail}"
            )
        except Exception as error:
            activation_failure = f"trace activation failed: {_exception_type(error)}"
        except BaseException:
            self._store_invalid("trace activation was interrupted")
            self._stop_instrumentation()
            self._release_live_capture()
            if _active_recorder is self:
                _active_recorder = None
            self._entered = False
            raise

        self._store_invalid(activation_failure)
        self._stop_instrumentation()
        self._release_live_capture()
        if _active_recorder is self:
            _active_recorder = None
        self._entered = False
        self._raise_stored_error()

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        del exception_type, traceback
        global _active_recorder

        if not self._entered:
            raise TraceStateError("recorder context exit has no matching entry")

        try:
            if self._state == "ACTIVE" and self._events:
                self._store_invalid(
                    "rewrite frames remained active when the trace context exited"
                )
            self._stop_instrumentation()
            if self._state == "ACTIVE":
                builder = self._require_builder()
                try:
                    self._trace = builder.freeze()
                except Exception as freeze_error:
                    self._store_invalid(
                        f"trace freezing failed: {_exception_type(freeze_error)}"
                    )
                else:
                    self._state = "FROZEN"
        finally:
            if _active_recorder is self:
                _active_recorder = None
            self._entered = False
            self._release_live_capture()

        if self._state == "INVALID":
            stored_error = self._require_error()
            if exception is None:
                self._raise_stored_error()
            # Do not let the recorder retain a traceback from an earlier caught signal.
            stored_error.__traceback__ = None
            stored_error.__context__ = None
            stored_error.__cause__ = None
        return False

    def _copy_analysis(self) -> dict[SSAValue, object] | None:
        source = self._analysis_input
        if source is None:
            return None
        if not isinstance(source, Mapping):
            raise TypeError("analysis must be a mapping from SSAValue objects")
        copied: dict[SSAValue, object] = {}
        for key, value in source.items():
            if not isinstance(key, SSAValue):
                raise TypeError("analysis mapping keys must be SSAValue objects")
            copied[key] = value
        return copied

    def _ensure_adapter(self) -> _SnapshotAdapter:
        adapter = self._adapter
        if adapter is not None:
            return adapter
        builder = self._require_builder()
        report = self._report
        if report is None:
            raise RuntimeError("active recorder lost its compatibility report")
        configuration_id = builder.add_configuration(
            kirin_commit=PINNED_KIRIN_COMMIT,
            rich_version=report.rich_version,
        )
        adapter = _SnapshotAdapter(
            builder,
            configuration_id,
            self._analysis_copy,
        )
        self._configuration_id = configuration_id
        self._adapter = adapter
        return adapter

    def _make_profile_callback(self) -> _ProfileCallback:
        def profile(frame: FrameType, event: str, argument: object) -> None:
            reduction_failure: str | None = None
            try:
                if self._state != "ACTIVE":
                    return
                if sys.getprofile() is not profile:
                    self._invalidate("a callback ran without owning the profile slot")
                self._reduce_profile_event(frame, event, argument)
            except UnsupportedTraceError as error:
                if error is self._error:
                    raise
                reduction_failure = (
                    "profile reduction raised a foreign UnsupportedTraceError"
                )
            except Exception as error:
                reduction_failure = (
                    f"profile reduction failed: {_exception_type(error)}"
                )
            except BaseException:
                self._mark_invalid("profile reduction was interrupted")
                raise
            if reduction_failure is not None:
                self._invalidate(reduction_failure)

        return profile

    def _reduce_profile_event(
        self, frame: FrameType, event: str, argument: object
    ) -> None:
        if event == "call":
            mutations = self._mutations
            if mutations is None:
                raise RuntimeError("active recorder lost its mutation interceptors")
            if mutations.authorize_profile_call(frame):
                return
            classification = self._classify_frame(frame)
            if classification is None:
                return
            if classification.kind == "public" or self._specialized_call_owns_event(
                classification
            ):
                self._enter_event(frame, classification)
            return

        if event != "return":
            return
        if self._events and self._events[-1].frame is frame:
            self._return_event(frame, argument)
            return
        if any(shell.frame is frame for shell in self._events):
            self._invalidate("rewrite frames returned out of LIFO order")
        classification = self._classify_frame(frame)
        if classification is not None and classification.kind == "public":
            self._invalidate(
                "a public rewrite frame returned without a matching captured entry"
            )

    def _classify_frame(self, frame: FrameType) -> _FrameClassification | None:
        locals_mapping = frame.f_locals
        rule = locals_mapping.get("self", _MISSING)
        node = locals_mapping.get("node", _MISSING)

        if not isinstance(rule, RewriteRule):
            if _code_is(frame.f_code, _BASE_CODES):
                self._invalidate(
                    "an observable public rewrite frame has an invalid self value"
                )
            return None

        matches: list[tuple[str, FunctionType]] = []
        for owner in type(rule).__mro__:
            namespace = vars(owner)
            for name in _METHOD_NAMES:
                candidate = namespace.get(name)
                descriptor_function: object = (
                    cast(Any, candidate).__wrapped__
                    if type(candidate) in {staticmethod, classmethod}
                    else candidate
                )
                if (
                    name in _METHOD_NAMES
                    and type(candidate) is not FunctionType
                    and type(descriptor_function) is FunctionType
                    and descriptor_function.__code__ is frame.f_code
                ):
                    self._invalidate(
                        "an observable rewrite method is not a plain function"
                    )
                if (
                    inspect.isfunction(candidate)
                    and candidate.__code__ is frame.f_code
                    and not any(
                        existing_name == name and existing_function is candidate
                        for existing_name, existing_function in matches
                    )
                ):
                    matches.append((name, candidate))
        if not matches:
            return None
        if len(matches) != 1:
            self._invalidate(
                "a rewrite frame has an ambiguous public or specialized role"
            )
        name, function = matches[0]
        if (
            inspect.isgeneratorfunction(function)
            or inspect.iscoroutinefunction(function)
            or inspect.isasyncgenfunction(function)
        ):
            self._invalidate(
                "deferred rewrite execution is unsupported once it becomes observable"
            )
        if not isinstance(node, IRNode):
            self._invalidate("an observable rewrite frame has an invalid node value")
        if name == "rewrite":
            return _FrameClassification("public", rule, node, function)
        kind, expected_type = _SPECIALIZED_TYPES[name]
        if not isinstance(node, expected_type):
            self._invalidate(
                f"{name} received a node outside its pinned dispatch category"
            )
        return _FrameClassification(kind, rule, node, function)

    def _specialized_call_owns_event(
        self, classification: _FrameClassification
    ) -> bool:
        """Report whether a specialized handler frame opens its own event.

        A handler running on the innermost open event's own rule instance is
        internal dispatch and records nothing. A handler running on any other
        instance owns a nested event, so its activity is attributed to the rule
        that performed it. Ownership is decided by object identity, never by
        equality. A handler observed while no event is open has no parent to
        attribute to and is unsupported.
        """

        if not self._events:
            self._invalidate(
                "a specialized rewrite handler ran outside a public rewrite event"
            )
        return classification.rule is not self._events[-1].rule

    def _enter_event(
        self, frame: FrameType, classification: _FrameClassification
    ) -> None:
        builder = self._require_builder()
        adapter = self._ensure_adapter()
        event_id = builder.next_id("event")
        parent_id = self._events[-1].event_id if self._events else None
        sibling_ordinal = self._sibling_counts.get(parent_id, 0)
        root = classification.node.get_root()
        if not isinstance(root, IRNode):
            self._invalidate("IRNode.get_root() returned a non-IRNode object")
        stack_id = builder.add_stack(capture_invocation_stack(frame))
        before_snapshot_id = adapter.capture(root, event_id, "before")
        before_snapshot = builder.snapshots[-1]
        if before_snapshot.id != before_snapshot_id:
            raise RuntimeError("snapshot adapter returned a nonterminal snapshot ID")
        index = len(builder.events)
        builder.events.append(
            RewriteEvent(
                id=event_id,
                sequence=index,
                parent_id=parent_id,
                sibling_ordinal=sibling_ordinal,
                rule_type=_qualified_type(classification.rule),
                completion="incomplete",
                root_entity_id=before_snapshot.root_entity_id,
                before_snapshot_id=before_snapshot_id,
                after_snapshot_id=None,
                invocation_stack_id=stack_id,
                result=None,
            )
        )
        self._sibling_counts[parent_id] = sibling_ordinal + 1
        self._events.append(
            _EventShell(
                frame=frame,
                rule=classification.rule,
                root=root,
                event_id=event_id,
                index=index,
            )
        )

    def _return_event(self, frame: FrameType, argument: object) -> None:
        shell = self._events[-1]
        if shell.frame is not frame:  # pragma: no cover - checked by reducer
            self._invalidate("a rewrite return did not match its event shell")
        if not isinstance(argument, RewriteResult):
            self._events.pop()
            return

        terminated = argument.terminated
        changed = argument.has_done_something
        exceeded = argument.exceeded_max_iter
        if any(type(value) is not bool for value in (terminated, changed, exceeded)):
            self._invalidate("RewriteResult fields must be exact booleans")

        builder = self._require_builder()
        after_snapshot_id = self._ensure_adapter().capture(
            shell.root, shell.event_id, "after"
        )
        event = builder.events[shell.index]
        builder.events[shell.index] = replace(
            event,
            completion="complete",
            after_snapshot_id=after_snapshot_id,
            result=RewriteResultRecord(
                terminated=terminated,
                has_done_something=changed,
                exceeded_max_iter=exceeded,
            ),
        )
        self._events.pop()

    def _active_event_id(self) -> str | None:
        if self._state != "ACTIVE" or not self._events:
            return None
        return self._events[-1].event_id

    def _require_builder(self) -> _TraceBuilder:
        builder = self._builder
        if builder is None:
            raise RuntimeError("recorder has no live trace builder")
        return builder

    def _store_invalid(self, reason: str) -> UnsupportedTraceError:
        if self._error is None:
            self._error = UnsupportedTraceError(reason)
        self._state = "INVALID"
        return self._error

    def _mark_invalid(self, reason: str) -> None:
        self._store_invalid(reason)
        self._stop_instrumentation()
        self._release_live_capture()

    def _invalidate(self, reason: str) -> NoReturn:
        self._mark_invalid(reason)
        self._raise_stored_error()

    def _require_error(self) -> UnsupportedTraceError:
        error = self._error
        if error is None:  # pragma: no cover - defensive invariant
            raise TraceStateError("invalid recorder lost its unsupported-use error")
        return error

    def _raise_stored_error(self) -> NoReturn:
        error = self._require_error()
        _clear_error_traceback(error)
        _schedule_traceback_scrub(error)
        raise error from None

    def _stop_instrumentation(self) -> None:
        if self._cleaning:
            return
        self._cleaning = True
        try:
            callback = self._callback
            if callback is not None and self._instrumented:
                current = sys.getprofile()
                if current is callback:
                    sys.setprofile(None)
                elif self._state == "ACTIVE":
                    self._store_invalid(
                        "the tracing profile callback was replaced while active"
                    )
            mutations = self._mutations
            if mutations is not None and self._instrumented:
                try:
                    mutations.uninstall()
                except Exception as error:
                    self._store_invalid(
                        f"mutation interceptor cleanup failed: {_exception_type(error)}"
                    )
            self._instrumented = False
        finally:
            self._cleaning = False

    def _release_live_capture(self) -> None:
        builder = self._builder
        if builder is not None and self._state == "INVALID":
            builder.release()
        self._events.clear()
        self._sibling_counts.clear()
        self._adapter = None
        self._configuration_id = None
        self._analysis_copy = None
        self._analysis_input = None
        self._report = None
        self._mutation_recorder = None
        self._mutations = None
        self._callback = None
        self._builder = None


def trace_rewrites(
    *, analysis: Mapping[SSAValue, object] | None = None
) -> TraceRecorder:
    """Create a fresh one-shot rewrite recorder context."""

    return TraceRecorder(analysis=analysis)


__all__ = (
    "TraceRecorder",
    "TraceStateError",
    "UnsupportedTraceError",
    "trace_rewrites",
)
