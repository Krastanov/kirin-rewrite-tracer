from __future__ import annotations

import kirin_rewrite_tracer


def test_package_imports() -> None:
    assert kirin_rewrite_tracer.__name__ == "kirin_rewrite_tracer"
