from __future__ import annotations

import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from browser_harness import (
    BrowserHarness,
    browser_prerequisite_failure,
    validate_chrome_provision,
)


@pytest.fixture(scope="session")  # type: ignore[untyped-decorator]
def headed_chrome() -> Iterator[BrowserHarness]:
    reason = browser_prerequisite_failure()
    if reason is not None:
        pytest.skip(reason)

    provision = validate_chrome_provision()
    with tempfile.TemporaryDirectory(prefix="krt-browser-", dir="/tmp") as temporary:
        run_root = Path(temporary)
        harness = BrowserHarness.launch(provision, run_root)
        try:
            yield harness
        finally:
            harness.close()
