#!/usr/bin/env python3
"""Provision the pinned Chrome for Testing cache that browser verification requires.

Every URL, hash, and path comes from ``test/browser_harness.py`` so continuous
integration cannot drift from the provision the harness itself validates. The script is
idempotent: an archive whose SHA-256 already matches is neither downloaded nor
re-extracted, so a restored cache is reused without weakening the pin.
"""

from __future__ import annotations

import shutil
import stat
import sys
import urllib.request
import zipfile
from hashlib import sha256
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "test"))

from browser_harness import (
    CHROME_ARCHIVE_SHA256,
    CHROME_ARCHIVE_URL,
    CHROME_VERSION,
    CHROMEDRIVER_ARCHIVE_SHA256,
    CHROMEDRIVER_ARCHIVE_URL,
    chrome_cache_root,
    validate_chrome_provision,
)

_ARCHIVES = (
    (
        "chrome-linux64.zip",
        CHROME_ARCHIVE_URL,
        CHROME_ARCHIVE_SHA256,
        Path("chrome-linux64") / "chrome",
    ),
    (
        "chromedriver-linux64.zip",
        CHROMEDRIVER_ARCHIVE_URL,
        CHROMEDRIVER_ARCHIVE_SHA256,
        Path("chromedriver-linux64") / "chromedriver",
    ),
)


def _digest(path: Path) -> str:
    hasher = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _download(url: str, destination: Path, expected: str) -> bool:
    """Return whether the archive had to be fetched rather than reused."""

    if destination.is_file() and _digest(destination) == expected:
        print(f"reusing {destination.name}")
        return False
    print(f"downloading {url}")
    with urllib.request.urlopen(url) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    actual = _digest(destination)
    if actual != expected:
        raise SystemExit(f"{destination.name} hashed {actual}, expected {expected}")
    return True


def _extract(archive: Path, root: Path, extracted_top: Path) -> None:
    target = root / extracted_top.parts[0]
    if target.exists():
        shutil.rmtree(target)
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            written = Path(bundle.extract(member, root))
            mode = stat.S_IMODE(member.external_attr >> 16)
            if mode:
                written.chmod(mode)
    print(f"extracted {archive.name}")


def main() -> None:
    root = chrome_cache_root()
    root.mkdir(parents=True, exist_ok=True)
    print(f"provisioning Chrome for Testing {CHROME_VERSION} beneath {root}")

    for name, url, expected, extracted_top in _ARCHIVES:
        archive = root / name
        fetched = _download(url, archive, expected)
        # A restored cache can hold a stale extraction beside a replaced archive, so
        # anything newly fetched is always unpacked again.
        if fetched or not (root / extracted_top).is_file():
            _extract(archive, root, extracted_top)

    provision = validate_chrome_provision(root)
    print(f"validated {provision.chrome_binary} and {provision.chromedriver_binary}")


if __name__ == "__main__":
    main()
