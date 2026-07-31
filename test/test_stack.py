from __future__ import annotations

import gc
import linecache
import sys
import weakref
from types import FunctionType
from typing import cast

import pytest

from kirin_rewrite_tracer._model import FrameLocation
from kirin_rewrite_tracer._stack import capture_invocation_stack


class _LifetimeSentinel:
    pass


class _HostileLocal:
    def __repr__(self) -> str:
        raise AssertionError("stack capture must not represent frame locals")


def test_stack_is_outermost_first_with_exact_runtime_fields() -> None:
    def leaf() -> tuple[tuple[FrameLocation, ...], int]:
        frame = sys._getframe()
        capture_line = frame.f_lineno + 1
        locations = capture_invocation_stack(frame)
        return locations, capture_line

    def branch() -> tuple[tuple[tuple[FrameLocation, ...], int], int]:
        frame = sys._getframe()
        call_line = frame.f_lineno + 1
        return leaf(), call_line

    (locations, leaf_line), branch_line = branch()

    assert locations[-2:] == (
        FrameLocation(filename=__file__, line=branch_line, function="branch"),
        FrameLocation(filename=__file__, line=leaf_line, function="leaf"),
    )


def test_code_exclusion_uses_identity_not_matching_coordinates() -> None:
    namespace_one: dict[str, object] = {}
    namespace_two: dict[str, object] = {}
    source = "def duplicate(callback):\n    return callback()\n"
    synthetic_filename = "<same-stack-coordinates>"
    exec(compile(source, synthetic_filename, "exec"), namespace_one)
    exec(compile(source, synthetic_filename, "exec"), namespace_two)
    first = cast(FunctionType, namespace_one["duplicate"])
    second = cast(FunctionType, namespace_two["duplicate"])
    assert first.__code__ is not second.__code__
    assert first.__code__ == second.__code__

    def leaf() -> tuple[FrameLocation, ...]:
        return capture_invocation_stack(
            sys._getframe(),
            excluded_codes=(first.__code__,),
        )

    captured = first(lambda: second(leaf))
    locations = cast(tuple[FrameLocation, ...], captured)

    assert [
        location
        for location in locations
        if location.filename == synthetic_filename and location.function == "duplicate"
    ] == [
        FrameLocation(
            filename=synthetic_filename,
            line=2,
            function="duplicate",
        )
    ]


def test_full_stack_ignores_presentation_traceback_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "tracebacklimit", 1, raising=False)

    def recurse(remaining: int) -> tuple[FrameLocation, ...]:
        if remaining == 0:
            return capture_invocation_stack(sys._getframe())
        return recurse(remaining - 1)

    depth = 96
    locations = recurse(depth)

    assert (
        sum(
            location.filename == __file__ and location.function == "recurse"
            for location in locations
        )
        == depth + 1
    )


def test_capture_never_looks_up_source_or_represents_locals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_source_lookup(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("stack capture must not look up source text")

    monkeypatch.setattr(linecache, "getline", fail_source_lookup)

    def capture_hostile_frame() -> tuple[FrameLocation, ...]:
        hostile = _HostileLocal()
        locations = capture_invocation_stack(sys._getframe())
        assert hostile is not None
        return locations

    locations = capture_hostile_frame()

    assert locations[-1].function == "capture_hostile_frame"


def test_canonical_locations_retain_no_live_frame_or_local() -> None:
    def capture_and_release() -> tuple[
        tuple[FrameLocation, ...], weakref.ReferenceType[_LifetimeSentinel]
    ]:
        sentinel = _LifetimeSentinel()
        reference = weakref.ref(sentinel)
        locations = capture_invocation_stack(sys._getframe())
        return locations, reference

    locations, reference = capture_and_release()
    gc.collect()

    assert locations[-1].function == "capture_and_release"
    assert reference() is None


def test_capture_in_except_block_is_invocation_path_not_exception_traceback() -> None:
    def raise_site() -> None:
        raise RuntimeError("expected")

    def catch_site() -> tuple[tuple[FrameLocation, ...], int]:
        try:
            raise_site()
        except RuntimeError:
            frame = sys._getframe()
            capture_line = frame.f_lineno + 1
            return capture_invocation_stack(frame), capture_line
        raise AssertionError("raise_site unexpectedly returned")

    locations, capture_line = catch_site()

    assert locations[-1] == FrameLocation(
        filename=__file__,
        line=capture_line,
        function="catch_site",
    )
    assert all(location.function != "raise_site" for location in locations)
