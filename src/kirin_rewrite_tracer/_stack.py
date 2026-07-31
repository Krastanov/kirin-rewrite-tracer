"""Portable, frame-free invocation stack capture."""

from __future__ import annotations

import traceback
from collections.abc import Iterable
from types import CodeType, FrameType

from ._model import FrameLocation


def capture_invocation_stack(
    start_frame: FrameType,
    *,
    excluded_codes: Iterable[CodeType] = (),
) -> tuple[FrameLocation, ...]:
    """Copy an invocation path without retaining Python execution state.

    ``start_frame`` is the innermost frame that belongs in the observed path.  Callers
    may name tracer wrapper code objects to omit; comparison is deliberately by
    identity, so an unrelated function with the same source coordinates remains.
    """

    excluded = tuple(excluded_codes)
    walked = tuple(
        (frame, line)
        for frame, line in traceback.walk_stack(start_frame)
        if not _has_exact_code(frame, excluded)
    )
    summaries = traceback.StackSummary.extract(
        iter(walked),
        limit=len(walked),
        lookup_lines=False,
        capture_locals=False,
    )
    locations: list[FrameLocation] = []
    for summary in reversed(summaries):
        line = summary.lineno
        if line is None:
            raise RuntimeError("a live frame produced no runtime line number")
        locations.append(
            FrameLocation(
                filename=summary.filename,
                line=line,
                function=summary.name,
            )
        )
    return tuple(locations)


def _has_exact_code(frame: FrameType, excluded: tuple[CodeType, ...]) -> bool:
    return any(frame.f_code is code for code in excluded)
