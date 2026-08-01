"""Pinned headed-Chrome support shared by browser verification tests."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast
from urllib.parse import urlsplit

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait

CHROME_VERSION: Final = "151.0.7922.47"
CHROME_REVISION: Final = "r1654411"
CHROME_PLATFORM: Final = "linux64"
CHROME_ARCHITECTURE: Final = "x86_64"
PRODUCER_PYTHON: Final = (3, 13, 11)
CACHE_ENVIRONMENT_VARIABLE: Final = "KRT_CHROME_FOR_TESTING_ROOT"

CHROME_ARCHIVE_URL: Final = (
    "https://storage.googleapis.com/chrome-for-testing-public/"
    f"{CHROME_VERSION}/{CHROME_PLATFORM}/chrome-linux64.zip"
)
CHROMEDRIVER_ARCHIVE_URL: Final = (
    "https://storage.googleapis.com/chrome-for-testing-public/"
    f"{CHROME_VERSION}/{CHROME_PLATFORM}/chromedriver-linux64.zip"
)
CHROME_ARCHIVE_SHA256: Final = (
    "14ac03a67e154e3f8bbc57e03ef03315fda8fedff8e045eee8b31500283a33f4"
)
CHROMEDRIVER_ARCHIVE_SHA256: Final = (
    "2faa72828261cd3c5ff00cbc71cfca57a12c26c1406e084e1a34d8d90e292140"
)

_NETWORK_SCHEMES: Final = frozenset({"ftp", "http", "https", "ws", "wss"})
_BLOCKED_NETWORK_PATTERNS: Final = tuple(
    f"{scheme}://*" for scheme in sorted(_NETWORK_SCHEMES)
)


@dataclass(frozen=True, slots=True)
class ChromeProvision:
    """Validated paths and immutable provenance for the browser fixture."""

    root: Path
    chrome_binary: Path
    chromedriver_binary: Path
    version: str = CHROME_VERSION
    revision: str = CHROME_REVISION
    platform: str = CHROME_PLATFORM
    chrome_archive_url: str = CHROME_ARCHIVE_URL
    chromedriver_archive_url: str = CHROMEDRIVER_ARCHIVE_URL
    chrome_archive_sha256: str = CHROME_ARCHIVE_SHA256
    chromedriver_archive_sha256: str = CHROMEDRIVER_ARCHIVE_SHA256


@dataclass(frozen=True, slots=True)
class NetworkRequest:
    url: str
    document_url: str | None
    resource_type: str | None
    initiator_type: str | None


@dataclass(frozen=True, slots=True)
class ConsoleEntry:
    level: str
    source: str
    message: str
    timestamp: float


@dataclass(frozen=True, slots=True)
class PageObservations:
    requests: tuple[NetworkRequest, ...]
    console: tuple[ConsoleEntry, ...]
    csp_violations: tuple[ConsoleEntry, ...]

    def requests_for_document(self, document_url: str) -> tuple[NetworkRequest, ...]:
        return tuple(
            request
            for request in self.requests
            if request.url == document_url or request.document_url == document_url
        )

    def page_network_requests(
        self, *, document_url: str | None = None
    ) -> tuple[NetworkRequest, ...]:
        candidates = (
            self.requests
            if document_url is None
            else self.requests_for_document(document_url)
        )
        return tuple(
            request
            for request in candidates
            if urlsplit(request.url).scheme.casefold() in _NETWORK_SCHEMES
        )

    def auxiliary_requests_for(self, document_url: str) -> tuple[NetworkRequest, ...]:
        return tuple(
            request
            for request in self.requests_for_document(document_url)
            if request.url != document_url
        )


@dataclass(frozen=True, slots=True)
class AccessibilityProperty:
    name: str
    value: str | bool | int | float | None


@dataclass(frozen=True, slots=True)
class AccessibilityNode:
    node_id: str
    ignored: bool
    role: str | None
    name: str | None
    description: str | None
    child_ids: tuple[str, ...]
    properties: tuple[AccessibilityProperty, ...]


@dataclass(frozen=True, slots=True)
class AccessibilityTree:
    nodes: tuple[AccessibilityNode, ...]

    def matching(
        self, *, role: str | None = None, name: str | None = None
    ) -> tuple[AccessibilityNode, ...]:
        return tuple(
            node
            for node in self.nodes
            if (role is None or node.role == role)
            and (name is None or node.name == name)
        )


@dataclass(frozen=True, slots=True)
class ZoomMeasurement:
    requested_percent: int
    device_pixel_ratio: float
    visual_viewport_scale: float


@dataclass(frozen=True, slots=True)
class ViewportMeasurement:
    css_width: int
    css_height: int
    outer_width: int
    outer_height: int
    device_pixel_ratio: float
    zoom_percent: int


def chrome_cache_root() -> Path:
    configured = os.environ.get(CACHE_ENVIRONMENT_VARIABLE)
    if configured:
        return Path(configured).expanduser().resolve()
    return (
        Path.home()
        / ".cache"
        / "kirin-rewrite-tracer"
        / "chrome-for-testing"
        / CHROME_VERSION
    )


def browser_prerequisite_failure() -> str | None:
    """Return a skip reason only when an explicit browser prerequisite is absent."""

    if sys.implementation.name != "cpython" or sys.version_info[:3] != PRODUCER_PYTHON:
        version = ".".join(str(part) for part in sys.version_info[:3])
        return (
            "headed browser verification requires CPython 3.13.11; "
            f"running {sys.implementation.name} {version}"
        )
    if sys.platform != "linux" or platform.machine() != CHROME_ARCHITECTURE:
        return (
            "headed browser verification requires x86-64 Linux; "
            f"running {sys.platform} {platform.machine()}"
        )
    if not os.environ.get("DISPLAY"):
        return (
            "headed browser verification requires a live display; run it under xvfb-run"
        )
    if not _display_is_xvfb():
        return (
            "headed browser verification requires DISPLAY to belong to Xvfb; "
            "run it under xvfb-run"
        )

    root = chrome_cache_root()
    required = (
        root / "chrome-linux64.zip",
        root / "chromedriver-linux64.zip",
        root / "chrome-linux64" / "chrome",
        root / "chromedriver-linux64" / "chromedriver",
    )
    missing = tuple(path for path in required if not path.is_file())
    if missing:
        names = ", ".join(str(path.relative_to(root)) for path in missing)
        return f"pinned Chrome for Testing cache is incomplete at {root}: {names}"
    return None


def validate_chrome_provision(root: Path | None = None) -> ChromeProvision:
    """Validate both downloaded archives and both extracted executables."""

    resolved_root = (root or chrome_cache_root()).resolve()
    chrome_archive = resolved_root / "chrome-linux64.zip"
    driver_archive = resolved_root / "chromedriver-linux64.zip"
    chrome_binary = resolved_root / "chrome-linux64" / "chrome"
    driver_binary = resolved_root / "chromedriver-linux64" / "chromedriver"

    expected_files = (
        chrome_archive,
        driver_archive,
        chrome_binary,
        driver_binary,
    )
    missing = tuple(path for path in expected_files if not path.is_file())
    if missing:
        joined = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"incomplete pinned Chrome provision: {joined}")

    _require_sha256(chrome_archive, CHROME_ARCHIVE_SHA256)
    _require_sha256(driver_archive, CHROMEDRIVER_ARCHIVE_SHA256)
    if not os.access(chrome_binary, os.X_OK):
        raise AssertionError(f"Chrome binary is not executable: {chrome_binary}")
    if not os.access(driver_binary, os.X_OK):
        raise AssertionError(f"ChromeDriver binary is not executable: {driver_binary}")

    chrome_report = _reported_version(chrome_binary)
    expected_chrome_report = f"Google Chrome for Testing {CHROME_VERSION}"
    if chrome_report != expected_chrome_report:
        raise AssertionError(
            f"unexpected Chrome version report: {chrome_report!r}; "
            f"expected {expected_chrome_report!r}"
        )
    driver_report = _reported_version(driver_binary)
    expected_driver_prefix = f"ChromeDriver {CHROME_VERSION} "
    if not driver_report.startswith(expected_driver_prefix):
        raise AssertionError(
            f"unexpected ChromeDriver version report: {driver_report!r}; "
            f"expected prefix {expected_driver_prefix!r}"
        )

    return ChromeProvision(
        root=resolved_root,
        chrome_binary=chrome_binary,
        chromedriver_binary=driver_binary,
    )


class BrowserHarness:
    """One headed, offline Selenium session over the exact pinned binaries."""

    def __init__(
        self, provision: ChromeProvision, run_root: Path, driver: Chrome
    ) -> None:
        self.provision = provision
        self.run_root = run_root
        self.driver = driver
        self._base_device_pixel_ratio: float | None = None
        self._zoom_percent = 100

    @classmethod
    def launch(cls, provision: ChromeProvision, run_root: Path) -> BrowserHarness:
        profile = run_root / "profile"
        cache = run_root / "cache"
        downloads = run_root / "downloads"
        for directory in (profile, cache, downloads):
            directory.mkdir(parents=True, exist_ok=False)

        options = Options()
        options.binary_location = str(provision.chrome_binary)
        for argument in (
            f"--user-data-dir={profile}",
            f"--disk-cache-dir={cache}",
            # The OS sandbox needs unprivileged user namespaces, which stock Ubuntu
            # 24.04 refuses. Inertness is verified through CDP network denial, CSP, and
            # console observation, so no verified property depends on it.
            "--no-sandbox",
            "--window-size=1280,800",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--disable-breakpad",
            "--disable-client-side-phishing-detection",
            "--disable-component-update",
            "--disable-default-apps",
            "--disable-domain-reliability",
            "--disable-extensions",
            "--disable-features=AutofillServerCommunication,"
            "CertificateTransparencyComponentUpdater,MediaRouter",
            "--disable-sync",
            "--metrics-recording-only",
            "--no-pings",
            "--ozone-platform=x11",
            "--password-store=basic",
            "--use-mock-keychain",
            "--lang=en-US",
        ):
            options.add_argument(argument)
        options.add_experimental_option(
            "prefs",
            {
                "download.default_directory": str(downloads),
                "download.prompt_for_download": False,
                "safebrowsing.enabled": False,
            },
        )
        options.set_capability(
            "goog:loggingPrefs", {"browser": "ALL", "performance": "ALL"}
        )

        service = Service(
            executable_path=str(provision.chromedriver_binary),
            log_output=os.devnull,
        )
        driver = webdriver.Chrome(service=service, options=options)
        try:
            cls._validate_session_versions(driver, provision)
            driver.execute_cdp_cmd("Network.enable", {})
            driver.execute_cdp_cmd(
                "Network.setBlockedURLs", {"urls": list(_BLOCKED_NETWORK_PATTERNS)}
            )
            driver.execute_cdp_cmd(
                "Network.emulateNetworkConditions",
                {
                    "offline": True,
                    "latency": 0,
                    "downloadThroughput": 0,
                    "uploadThroughput": 0,
                    "connectionType": "none",
                },
            )
            driver.execute_cdp_cmd("Log.enable", {})
            driver.execute_cdp_cmd("Accessibility.enable", {})
        except BaseException:
            driver.quit()
            raise
        return cls(provision, run_root, driver)

    def close(self) -> None:
        self.driver.quit()

    def relocate(self, source: Path, destination: Path) -> Path:
        """Copy exactly one page to an existing empty directory."""

        if not source.is_file():
            raise FileNotFoundError(source)
        if not destination.is_dir():
            raise NotADirectoryError(destination)
        if any(destination.iterdir()):
            raise ValueError(f"relocation destination is not empty: {destination}")
        target = destination / source.name
        shutil.copyfile(source, target)
        inventory = tuple(destination.iterdir())
        if inventory != (target,):
            raise AssertionError(
                f"relocation created an unexpected inventory: {inventory}"
            )
        return target

    def open_relocated(
        self,
        source: Path,
        destination: Path,
        *,
        ready_attribute: str = "data-krt-ready",
    ) -> Path:
        target = self.relocate(source, destination)
        self.clear_observations()
        self.driver.get(target.as_uri())
        WebDriverWait(self.driver, 10).until(
            lambda driver: (
                driver.execute_script("return document.readyState") == "complete"
            )
        )
        if ready_attribute:
            WebDriverWait(self.driver, 10).until(
                lambda driver: (
                    driver.execute_script(
                        "return document.documentElement.getAttribute(arguments[0]);",
                        ready_attribute,
                    )
                    == "true"
                )
            )
        return target

    def clear_observations(self) -> None:
        self.driver.get_log("performance")  # type: ignore[no-untyped-call]
        self.driver.get_log("browser")  # type: ignore[no-untyped-call]

    def observations(self) -> PageObservations:
        raw_performance = self.driver.get_log(  # type: ignore[no-untyped-call]
            "performance"
        )
        raw_console = self.driver.get_log("browser")  # type: ignore[no-untyped-call]
        requests = _network_requests(raw_performance)
        console = _console_entries(raw_console)
        violations = tuple(entry for entry in console if _is_csp_violation(entry))
        return PageObservations(
            requests=requests,
            console=console,
            csp_violations=violations,
        )

    def accessibility_tree(self) -> AccessibilityTree:
        raw = cast(
            dict[str, object],
            self.driver.execute_cdp_cmd("Accessibility.getFullAXTree", {}),
        )
        raw_nodes = raw.get("nodes")
        if not isinstance(raw_nodes, list):
            raise AssertionError("Accessibility.getFullAXTree returned no node list")
        return AccessibilityTree(
            tuple(
                _accessibility_node(cast(dict[str, object], node)) for node in raw_nodes
            )
        )

    def set_page_zoom(self, percent: int) -> ZoomMeasurement:
        """Set Chrome's real default page zoom through its pinned settings UI."""

        if percent not in (100, 200):
            raise ValueError("the v1 harness supports only 100% and 200% page zoom")

        page_url = self.driver.current_url
        if urlsplit(page_url).scheme != "file":
            raise RuntimeError("load a relocated local page before setting page zoom")

        self._set_default_zoom_factor(1.0, page_url)
        base = _device_pixel_ratio(self.driver)
        self._base_device_pixel_ratio = base

        if percent == 200:
            self._set_default_zoom_factor(2.0, page_url)

        self._zoom_percent = percent
        measurement = ZoomMeasurement(
            requested_percent=percent,
            device_pixel_ratio=_device_pixel_ratio(self.driver),
            visual_viewport_scale=_visual_viewport_scale(self.driver),
        )
        expected_ratio = base * (percent / 100)
        if abs(measurement.device_pixel_ratio - expected_ratio) >= 0.01:
            raise AssertionError(
                f"requested {percent}% page zoom produced DPR "
                f"{measurement.device_pixel_ratio}, expected {expected_ratio}"
            )
        if measurement.visual_viewport_scale != 1.0:
            raise AssertionError(
                "page zoom changed visualViewport.scale like pinch emulation"
            )
        return measurement

    def _set_default_zoom_factor(self, factor: float, page_url: str) -> None:
        self.driver.get("chrome://settings/appearance")
        actual = self.driver.execute_async_script(
            """
            const factor = arguments[0];
            const done = arguments[arguments.length - 1];
            chrome.settingsPrivate.setDefaultZoom(factor).then(
              () => chrome.settingsPrivate.getDefaultZoom()
            ).then(done, error => done({error: String(error)}));
            """,
            factor,
        )
        if not isinstance(actual, (int, float)) or float(actual) != factor:
            raise AssertionError(
                f"Chrome settings reported page zoom factor {actual!r}, "
                f"expected {factor}"
            )
        self.driver.get(page_url)
        WebDriverWait(self.driver, 10).until(
            lambda driver: (
                driver.execute_script("return document.readyState") == "complete"
            )
        )
        self.clear_observations()

    def set_css_viewport(self, width: int, height: int) -> ViewportMeasurement:
        """Resize the headed window until the measured CSS viewport is exact."""

        if width <= 0 or height <= 0:
            raise ValueError("viewport dimensions must be positive")
        zoom_factor = self._zoom_percent / 100
        for _ in range(12):
            measurement = self.viewport()
            if measurement.css_width == width and measurement.css_height == height:
                return measurement
            next_width = max(
                200,
                measurement.outer_width
                + round((width - measurement.css_width) * zoom_factor),
            )
            next_height = max(
                200,
                measurement.outer_height
                + round((height - measurement.css_height) * zoom_factor),
            )
            self.driver.set_window_rect(width=next_width, height=next_height)
            self._await_content_response(
                (measurement.css_width, measurement.css_height)
            )
        measurement = self.viewport()
        raise AssertionError(
            "could not establish requested measured CSS viewport "
            f"{width}x{height}; observed "
            f"{measurement.css_width}x{measurement.css_height} inside a "
            f"{measurement.outer_width}x{measurement.outer_height} window"
        )

    def _await_content_response(self, previous: tuple[int, int]) -> None:
        """Let a resize reach the content box before the next measurement.

        The outer window reports a requested size as soon as it is asked for, so it
        cannot witness the resize; only the CSS viewport shows that the content box
        followed. Waiting is an accuracy aid, so a resize the content declines returns
        quietly and leaves the exact-match loop in charge.
        """

        try:
            WebDriverWait(self.driver, 2, poll_frequency=0.02).until(
                lambda driver: (
                    driver.execute_script(
                        "return [window.innerWidth, window.innerHeight];"
                    )
                    != [previous[0], previous[1]]
                )
            )
        except TimeoutException:
            return

    def viewport(self) -> ViewportMeasurement:
        dimensions = cast(
            list[object],
            self.driver.execute_script(
                "return [window.innerWidth, window.innerHeight, "
                "window.outerWidth, window.outerHeight, window.devicePixelRatio];"
            ),
        )
        if len(dimensions) != 5:
            raise AssertionError(f"unexpected viewport measurement: {dimensions!r}")
        return ViewportMeasurement(
            css_width=int(cast(int | float, dimensions[0])),
            css_height=int(cast(int | float, dimensions[1])),
            outer_width=int(cast(int | float, dimensions[2])),
            outer_height=int(cast(int | float, dimensions[3])),
            device_pixel_ratio=float(cast(int | float, dimensions[4])),
            zoom_percent=self._zoom_percent,
        )

    @staticmethod
    def _validate_session_versions(driver: Chrome, provision: ChromeProvision) -> None:
        capabilities = cast(dict[str, object], driver.capabilities)
        browser_version = capabilities.get("browserVersion")
        if browser_version != provision.version:
            raise AssertionError(
                f"Selenium launched Chrome {browser_version!r}, "
                f"expected {provision.version!r}"
            )
        chrome_capabilities = capabilities.get("chrome")
        if not isinstance(chrome_capabilities, dict):
            raise AssertionError("Selenium returned no Chrome capabilities")
        driver_version = chrome_capabilities.get("chromedriverVersion")
        if not isinstance(driver_version, str) or not driver_version.startswith(
            f"{provision.version} "
        ):
            raise AssertionError(
                f"Selenium launched ChromeDriver {driver_version!r}, "
                f"expected {provision.version!r}"
            )


def _require_sha256(path: Path, expected: str) -> None:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    actual = digest.hexdigest()
    if actual != expected:
        raise AssertionError(
            f"SHA-256 mismatch for {path}: got {actual}, expected {expected}"
        )


def _reported_version(binary: Path) -> str:
    process = subprocess.run(
        [str(binary), "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    return process.stdout.strip()


def _network_requests(
    raw_entries: list[dict[str, object]],
) -> tuple[NetworkRequest, ...]:
    requests: list[NetworkRequest] = []
    for entry in raw_entries:
        encoded = entry.get("message")
        if not isinstance(encoded, str):
            continue
        envelope = json.loads(encoded)
        if not isinstance(envelope, dict):
            continue
        message = envelope.get("message")
        if not isinstance(message, dict):
            continue
        if message.get("method") != "Network.requestWillBeSent":
            continue
        parameters = message.get("params")
        if not isinstance(parameters, dict):
            continue
        raw_request = parameters.get("request")
        if not isinstance(raw_request, dict):
            continue
        url = raw_request.get("url")
        if not isinstance(url, str):
            continue
        requests.append(
            NetworkRequest(
                url=url,
                document_url=_optional_string(parameters.get("documentURL")),
                resource_type=_optional_string(parameters.get("type")),
                initiator_type=_nested_string(parameters.get("initiator"), "type"),
            )
        )
    return tuple(requests)


def _console_entries(
    raw_entries: list[dict[str, object]],
) -> tuple[ConsoleEntry, ...]:
    entries: list[ConsoleEntry] = []
    for entry in raw_entries:
        timestamp = entry.get("timestamp", 0.0)
        entries.append(
            ConsoleEntry(
                level=str(entry.get("level", "")),
                source=str(entry.get("source", "")),
                message=str(entry.get("message", "")),
                timestamp=float(cast(int | float, timestamp)),
            )
        )
    return tuple(entries)


def _is_csp_violation(entry: ConsoleEntry) -> bool:
    folded = entry.message.casefold()
    return "content security policy" in folded and "violat" in folded


def _display_is_xvfb() -> bool:
    display = os.environ.get("DISPLAY", "")
    display_number = display.rsplit(":", maxsplit=1)[-1].split(".", maxsplit=1)[0]
    expected_argument = f":{display_number}".encode()
    for process in Path("/proc").glob("[0-9]*"):
        try:
            if (process / "comm").read_text().strip() != "Xvfb":
                continue
            arguments = (process / "cmdline").read_bytes().split(b"\0")
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if expected_argument in arguments:
            return True
    return False


def _accessibility_node(raw: dict[str, object]) -> AccessibilityNode:
    raw_children = raw.get("childIds")
    child_ids = (
        tuple(str(child) for child in raw_children)
        if isinstance(raw_children, list)
        else ()
    )
    raw_properties = raw.get("properties")
    properties: list[AccessibilityProperty] = []
    if isinstance(raw_properties, list):
        for raw_property in raw_properties:
            if not isinstance(raw_property, dict):
                continue
            name = raw_property.get("name")
            value = raw_property.get("value")
            if not isinstance(name, str) or not isinstance(value, dict):
                continue
            properties.append(
                AccessibilityProperty(
                    name=name,
                    value=_accessibility_value(value.get("value")),
                )
            )
    return AccessibilityNode(
        node_id=str(raw.get("nodeId", "")),
        ignored=raw.get("ignored") is True,
        role=_nested_string(raw.get("role"), "value"),
        name=_nested_string(raw.get("name"), "value"),
        description=_nested_string(raw.get("description"), "value"),
        child_ids=child_ids,
        properties=tuple(properties),
    )


def _accessibility_value(value: object) -> str | bool | int | float | None:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    return str(value)


def _nested_string(value: object, key: str) -> str | None:
    if not isinstance(value, dict):
        return None
    return _optional_string(value.get(key))


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _device_pixel_ratio(driver: Chrome) -> float:
    return float(cast(int | float, driver.execute_script("return devicePixelRatio;")))


def _visual_viewport_scale(driver: Chrome) -> float:
    return float(
        cast(
            int | float,
            driver.execute_script(
                "return window.visualViewport ? window.visualViewport.scale : 1;"
            ),
        )
    )
