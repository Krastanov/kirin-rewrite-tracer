"""Autonomous inert HTML export with atomic no-overwrite publication."""

from __future__ import annotations

import errno
import json
import os
import re
import secrets
import tempfile
from contextlib import suppress
from importlib.resources import files
from pathlib import Path
from typing import BinaryIO

from ._encoding import encode_trace, generated_style_rules
from ._model import Trace

_ASSET_PACKAGE = "kirin_rewrite_tracer.assets"
_NONCE_PATTERN = re.compile(r"[A-Za-z0-9_-]{16,}")


def export_html(trace: Trace, destination: str | os.PathLike[str]) -> Path:
    """Publish one self-contained HTML file without replacing any destination."""

    if type(trace) is not Trace:
        raise TypeError("trace must be an immutable Trace")

    target = Path(destination)
    parent = target.parent
    if not parent.exists():
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), parent)
    if not parent.is_dir():
        raise NotADirectoryError(errno.ENOTDIR, os.strerror(errno.ENOTDIR), parent)
    try:
        target.lstat()
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), target)

    document = _document_bytes(trace)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=parent
    )
    temporary = Path(temporary_name)
    stream: BinaryIO | None = None
    publication_confirmed = False
    try:
        stream = os.fdopen(descriptor, "wb")
        descriptor = -1
        _write_stream(stream, document)
        _flush_stream(stream)
        _close_stream(stream)
        stream = None
        _publish_no_replace(temporary, target)
        publication_confirmed = True
        _unlink_if_present(temporary)
    except BaseException:
        if publication_confirmed and _same_file(temporary, target):
            _unlink_if_present(target)
        raise
    finally:
        if stream is not None:
            with suppress(BaseException):
                stream.close()
        elif descriptor >= 0:
            with suppress(OSError):
                os.close(descriptor)
        _unlink_if_present(temporary)

    if not publication_confirmed:
        raise RuntimeError("HTML publication did not complete")
    return target


def _document_bytes(trace: Trace, *, nonce: str | None = None) -> bytes:
    payload = encode_trace(trace)
    generated_nonce = secrets.token_urlsafe(24) if nonce is None else nonce
    if _NONCE_PATTERN.fullmatch(generated_nonce) is None:
        raise ValueError("document nonce is outside the fixed safe alphabet")

    serialized = json.dumps(
        payload,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
    )
    serialized = (
        serialized.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )
    static_css = _read_asset("viewer.css")
    generated_css = generated_style_rules(trace)
    viewer_js = _read_asset("viewer.js")
    csp = (
        "default-src 'none'; "
        "base-uri 'none'; "
        "connect-src 'none'; "
        "font-src 'none'; "
        "form-action 'none'; "
        "frame-src 'none'; "
        "img-src 'none'; "
        "media-src 'none'; "
        "object-src 'none'; "
        f"script-src 'nonce-{generated_nonce}'; "
        f"style-src 'nonce-{generated_nonce}'; "
        "worker-src 'none'"
    )
    document = (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f'<meta http-equiv="Content-Security-Policy" content="{csp}">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        "<title>Kirin rewrite trace</title>\n"
        f'<style nonce="{generated_nonce}">\n'
        f"{static_css}\n{generated_css}\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        '<a class="skip-link" href="#ssa-workspace">Skip event hierarchy</a>\n'
        "<header>\n"
        "<h1>Kirin rewrite trace</h1>\n"
        '<p class="trace-summary" id="trace-summary"></p>\n'
        "</header>\n"
        '<main class="workspace" aria-label="Rewrite trace workspace">\n'
        '<section class="event-column" aria-labelledby="events-heading">\n'
        '<div class="column-heading">\n'
        '<h2 id="events-heading">Events</h2>\n'
        '<button class="clear-selection" type="button">Clear selection</button>\n'
        "</div>\n"
        '<ol class="event-tree" id="event-tree"></ol>\n'
        "</section>\n"
        '<section class="ssa-workspace" id="ssa-workspace" '
        'aria-labelledby="ssa-heading">\n'
        '<h2 class="visually-hidden" id="ssa-heading">SSA states</h2>\n'
        '<p class="empty-state" id="ssa-empty">Select an event to inspect states.</p>\n'
        '<div class="ssa-columns" id="ssa-columns"></div>\n'
        "</section>\n"
        "</main>\n"
        '<section class="facts-region" aria-labelledby="facts-heading">\n'
        '<h2 id="facts-heading">Selected event facts</h2>\n'
        '<p id="facts-empty">No event selected.</p>\n'
        '<pre class="facts" id="selected-facts" hidden></pre>\n'
        "</section>\n"
        '<p class="visually-hidden" id="selection-status" '
        'role="status" aria-live="polite">Selected: 0; hidden: 0.</p>\n'
        f'<script nonce="{generated_nonce}" type="application/json" '
        f'id="trace-data">{serialized}</script>\n'
        f'<script nonce="{generated_nonce}">\n{viewer_js}\n</script>\n'
        "</body>\n"
        "</html>\n"
    )
    return document.encode("utf-8")


def _read_asset(name: str) -> str:
    return files(_ASSET_PACKAGE).joinpath(name).read_text(encoding="utf-8")


def _write_stream(stream: BinaryIO, document: bytes) -> None:
    written = stream.write(document)
    if written != len(document):
        raise OSError("short write while exporting HTML")


def _flush_stream(stream: BinaryIO) -> None:
    stream.flush()
    os.fsync(stream.fileno())


def _close_stream(stream: BinaryIO) -> None:
    stream.close()


def _publish_no_replace(temporary: Path, target: Path) -> None:
    os.link(temporary, target, follow_symlinks=False)


def _same_file(left: Path, right: Path) -> bool:
    try:
        left_stat = left.lstat()
        right_stat = right.lstat()
    except OSError:
        return False
    return (left_stat.st_dev, left_stat.st_ino) == (
        right_stat.st_dev,
        right_stat.st_ino,
    )


def _unlink_if_present(path: Path) -> None:
    with suppress(FileNotFoundError):
        path.unlink()
