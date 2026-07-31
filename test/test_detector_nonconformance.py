from __future__ import annotations

from typing import Any

from kirin.ir import IRNode, Statement
from kirin.rewrite.abc import RewriteResult, RewriteRule

from kirin_rewrite_tracer import trace_rewrites


class _CounterexampleNode(Statement):
    name = "evidence.detector_counterexample"


class _DirectOverride(RewriteRule):
    def rewrite(self, node: IRNode[Any]) -> RewriteResult:
        return RewriteResult()


def test_invalid_self_direct_override_is_silently_ignored_counterexample() -> None:
    """Bind the known invalid-self detector nonconformance to executable evidence."""

    with trace_rewrites() as recorder:
        result = _DirectOverride.rewrite(
            object(),  # type: ignore[arg-type]
            _CounterexampleNode(),
        )

    assert isinstance(result, RewriteResult)
    assert result == RewriteResult()
    assert recorder.state == "FROZEN"
    assert recorder.trace.complete
    assert recorder.trace.events == ()
