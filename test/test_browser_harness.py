from __future__ import annotations

from pathlib import Path

import pytest
from browser_harness import (
    CHROME_ARCHIVE_SHA256,
    CHROME_ARCHIVE_URL,
    CHROME_PLATFORM,
    CHROME_REVISION,
    CHROME_VERSION,
    CHROMEDRIVER_ARCHIVE_SHA256,
    CHROMEDRIVER_ARCHIVE_URL,
    BrowserHarness,
)

FIXTURES = Path(__file__).with_name("browser-fixtures")


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_pinned_headed_browser_supports_clean_static_page(
    headed_chrome: BrowserHarness, tmp_path: Path
) -> None:
    harness = headed_chrome
    provision = harness.provision
    assert provision.version == CHROME_VERSION
    assert provision.revision == CHROME_REVISION
    assert provision.platform == CHROME_PLATFORM
    assert provision.chrome_archive_url == CHROME_ARCHIVE_URL
    assert provision.chromedriver_archive_url == CHROMEDRIVER_ARCHIVE_URL
    assert provision.chrome_archive_sha256 == CHROME_ARCHIVE_SHA256
    assert provision.chromedriver_archive_sha256 == CHROMEDRIVER_ARCHIVE_SHA256

    destination = tmp_path / "relocated"
    destination.mkdir()
    relocated = harness.open_relocated(FIXTURES / "clean.html", destination)
    assert relocated.parent == destination
    assert tuple(destination.iterdir()) == (relocated,)
    assert harness.driver.current_url == relocated.as_uri()

    observations = harness.observations()
    assert observations.page_network_requests(document_url=relocated.as_uri()) == ()
    assert observations.csp_violations == ()
    assert any(
        "krt-browser-harness-ready" in entry.message for entry in observations.console
    )
    assert observations.auxiliary_requests_for(relocated.as_uri()) == ()
    assert any(
        request.url == relocated.as_uri()
        for request in observations.requests_for_document(relocated.as_uri())
    )

    tree = harness.accessibility_tree()
    assert tree.matching(role="link", name="Skip to workspace")
    assert tree.matching(role="main", name="Harness workspace")
    assert tree.matching(role="button", name="Inspectable action")
    assert tree.matching(role="status", name="Harness ready.")

    zoom_100 = harness.set_page_zoom(100)
    viewport_100 = harness.set_css_viewport(640, 480)
    assert zoom_100.visual_viewport_scale == 1.0
    assert (viewport_100.css_width, viewport_100.css_height) == (640, 480)
    large_viewport_100 = harness.set_css_viewport(1280, 800)
    assert (large_viewport_100.css_width, large_viewport_100.css_height) == (
        1280,
        800,
    )

    zoom_200 = harness.set_page_zoom(200)
    viewport_200 = harness.set_css_viewport(640, 480)
    assert zoom_200.device_pixel_ratio == pytest.approx(zoom_100.device_pixel_ratio * 2)
    assert zoom_200.visual_viewport_scale == 1.0
    assert (viewport_200.css_width, viewport_200.css_height) == (640, 480)
    large_viewport_200 = harness.set_css_viewport(1280, 800)
    assert (large_viewport_200.css_width, large_viewport_200.css_height) == (
        1280,
        800,
    )


@pytest.mark.browser  # type: ignore[untyped-decorator]
def test_monitors_attempted_network_csp_and_console_messages(
    headed_chrome: BrowserHarness, tmp_path: Path
) -> None:
    destination = tmp_path / "monitor"
    destination.mkdir()
    relocated = headed_chrome.open_relocated(FIXTURES / "monitor.html", destination)

    assert (
        headed_chrome.driver.execute_script(
            "return window.__krt_blocked_inline__ === undefined;"
        )
        is True
    )
    observations = headed_chrome.observations()
    assert any(
        request.url == "https://example.invalid/krt-browser-harness"
        for request in observations.page_network_requests(
            document_url=relocated.as_uri()
        )
    )
    assert observations.csp_violations
    assert any(
        "krt-browser-harness-console-probe" in entry.message
        for entry in observations.console
    )
