from __future__ import annotations

import errno
import json
import os
import re
import select
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

import kirin_rewrite_tracer._export as export_module
from kirin_rewrite_tracer import Trace, export_html
from kirin_rewrite_tracer._encoding import (
    PrimitiveObject,
    TraceEncodingError,
    _style_rule,
    _validate_primitive,
    encode_trace,
)
from kirin_rewrite_tracer._model import (
    CaptureConfiguration,
    ColorRecord,
    EntityEffect,
    EntityOccurrence,
    FrameLocation,
    FrozenMap,
    InvocationStack,
    MetadataRecord,
    MutationOperation,
    ProvenanceRelation,
    RenderedValue,
    RewriteEvent,
    RewriteResultRecord,
    Snapshot,
    StyleRecord,
    StyleSpan,
    TraceEntity,
    freeze_json,
)

_HOSTILE = (
    'A😀B</ScRiPt><img src=x onerror="globalThis.pwned=1">'
    "&'\\ <!-- __proto__ https://invalid.example CSS:url(https://invalid.example/x) "
    "\u2028\u2029"
)


def _hostile_trace() -> Trace:
    configuration = CaptureConfiguration(
        id="configuration-0",
        kirin_commit=_HOSTILE,
        rich_version="15.0.0",
        theme=_HOSTILE,
        show_indent_mark=False,
        hint=_HOSTILE,
        printer_analysis=False,
        highlighter=_HOSTILE,
    )
    style_meta = freeze_json(
        {
            "__proto__": _HOSTILE,
            "typed": [False, 0, 1.0, "", None],
        }
    )
    assert isinstance(style_meta, FrozenMap)
    style = StyleRecord(
        id="style-0",
        color=ColorRecord("truecolor", _HOSTILE, None, (17, 34, 51)),
        bgcolor=ColorRecord("standard", _HOSTILE, 1, None),
        bold=True,
        dim=False,
        italic=None,
        underline=True,
        blink=False,
        blink2=None,
        reverse=False,
        conceal=None,
        strike=True,
        underline2=False,
        frame=None,
        encircle=False,
        overline=True,
        link=_HOSTILE,
        meta=style_meta,
    )
    entities = (
        TraceEntity("entity-0", "statement", _HOSTILE),
        TraceEntity("entity-1", "ssa", _HOSTILE, "entity-0"),
        TraceEntity("entity-2", "statement", _HOSTILE),
    )
    occurrences = (
        EntityOccurrence(
            "occurrence-0",
            "snapshot-0",
            "entity-0",
            "container",
            0,
            len(_HOSTILE),
        ),
        EntityOccurrence("occurrence-1", "snapshot-0", "entity-1", "definition", 1, 2),
        EntityOccurrence(
            "occurrence-2",
            "snapshot-1",
            "entity-0",
            "container",
            0,
            len(_HOSTILE),
        ),
        EntityOccurrence("occurrence-3", "snapshot-1", "entity-1", "reference", 1, 2),
    )
    metadata = (
        MetadataRecord(
            "metadata-0",
            "snapshot-0",
            "entity-1",
            _HOSTILE,
            _HOSTILE,
            "present",
            RenderedValue(_HOSTILE, _HOSTILE, "repr"),
        ),
        MetadataRecord(
            "metadata-1",
            "snapshot-1",
            "entity-1",
            _HOSTILE,
            _HOSTILE,
            "present",
            RenderedValue(_HOSTILE, _HOSTILE, "printable"),
        ),
    )
    snapshots = (
        Snapshot(
            id="snapshot-0",
            event_id="event-0",
            state="before",
            schema_version=1,
            configuration_id="configuration-0",
            root_entity_id="entity-0",
            text=_HOSTILE,
            style_spans=(StyleSpan(0, len(_HOSTILE), "style-0"),),
            entity_ids=("entity-0", "entity-1"),
            occurrence_ids=("occurrence-0", "occurrence-1"),
            metadata_ids=("metadata-0",),
            analysis_supplied=True,
        ),
        Snapshot(
            id="snapshot-1",
            event_id="event-0",
            state="after",
            schema_version=1,
            configuration_id="configuration-0",
            root_entity_id="entity-0",
            text=_HOSTILE,
            style_spans=(StyleSpan(0, len(_HOSTILE), "style-0"),),
            entity_ids=("entity-0", "entity-1"),
            occurrence_ids=("occurrence-2", "occurrence-3"),
            metadata_ids=("metadata-1",),
            analysis_supplied=True,
        ),
    )
    stack = InvocationStack("stack-0", (FrameLocation(_HOSTILE, 17, _HOSTILE),))
    event = RewriteEvent(
        id="event-0",
        sequence=0,
        parent_id=None,
        sibling_ordinal=0,
        rule_type=_HOSTILE,
        completion="complete",
        root_entity_id="entity-0",
        before_snapshot_id="snapshot-0",
        after_snapshot_id="snapshot-1",
        invocation_stack_id="stack-0",
        result=RewriteResultRecord(False, True, False),
    )
    operations = (
        MutationOperation(
            id="operation-0",
            sequence=0,
            owner_event_id="event-0",
            parent_operation_id=None,
            api="Statement.replace_by",
            outcome="completed",
            source_entity_ids=("entity-0",),
            destination_entity_ids=("entity-2",),
            invocation_stack_id="stack-0",
        ),
        MutationOperation(
            id="operation-1",
            sequence=1,
            owner_event_id="event-0",
            parent_operation_id="operation-0",
            api="Statement.delete",
            outcome="completed",
            source_entity_ids=("entity-2",),
            destination_entity_ids=(),
            invocation_stack_id="stack-0",
        ),
    )
    relation = ProvenanceRelation(
        "relation-0",
        "statement_replaced_by",
        "entity-0",
        "entity-2",
        "operation-0",
    )
    effect = EntityEffect(
        "effect-0", "statement_delete_completed", "entity-2", "operation-1"
    )
    return Trace(
        schema_version=1,
        complete=True,
        configurations=(configuration,),
        styles=(style,),
        entities=entities,
        snapshots=snapshots,
        occurrences=occurrences,
        metadata=metadata,
        stacks=(stack,),
        events=(event,),
        operations=operations,
        relations=(relation,),
        effects=(effect,),
    )


def _payload_from_document(document: str) -> PrimitiveObject:
    match = re.search(
        r'<script nonce="[^"]+" type="application/json" '
        r'id="trace-data">(.*?)</script>',
        document,
        flags=re.DOTALL,
    )
    assert match is not None
    payload = json.loads(match.group(1))
    assert isinstance(payload, dict)
    return cast(PrimitiveObject, payload)


def _trace_payload(payload: PrimitiveObject) -> PrimitiveObject:
    value = payload["trace"]
    assert isinstance(value, dict)
    return value


def _projection_payload(payload: PrimitiveObject) -> PrimitiveObject:
    value = payload["projection"]
    assert isinstance(value, dict)
    return value


def _temporary_files(parent: Path, target: Path) -> list[Path]:
    return list(parent.glob(f".{target.name}.*.tmp"))


def test_encoder_copies_every_fact_domain_and_preserves_ordered_map_types() -> None:
    trace = _hostile_trace()
    payload = encode_trace(trace)
    facts = _trace_payload(payload)

    assert payload["export_schema_version"] == 1
    assert facts["schema_version"] == 1
    assert facts["complete"] is True
    for domain in (
        "configurations",
        "styles",
        "entities",
        "snapshots",
        "occurrences",
        "metadata",
        "stacks",
        "events",
        "operations",
        "relations",
        "effects",
    ):
        assert domain in facts

    styles = facts["styles"]
    assert isinstance(styles, list)
    encoded_style = styles[0]
    assert isinstance(encoded_style, dict)
    assert encoded_style["bold"] is True
    assert encoded_style["dim"] is False
    assert encoded_style["italic"] is None
    meta = encoded_style["meta"]
    assert isinstance(meta, dict)
    assert meta["kind"] == "ordered-map"
    entries = meta["entries"]
    assert isinstance(entries, list)
    assert entries[0] == [
        "__proto__",
        {"kind": "str", "value": _HOSTILE},
    ]
    assert trace == _hostile_trace()
    operations = facts["operations"]
    relations = facts["relations"]
    effects = facts["effects"]
    assert isinstance(operations, list)
    assert isinstance(relations, list)
    assert isinstance(effects, list)
    assert operations[1] == {
        "id": "operation-1",
        "sequence": 1,
        "owner_event_id": "event-0",
        "parent_operation_id": "operation-0",
        "api": "Statement.delete",
        "outcome": "completed",
        "source_entity_ids": ["entity-2"],
        "destination_entity_ids": [],
        "invocation_stack_id": "stack-0",
    }
    assert relations[0] == {
        "id": "relation-0",
        "basis": "statement_replaced_by",
        "source_entity_id": "entity-0",
        "destination_entity_id": "entity-2",
        "mutation_operation_id": "operation-0",
    }
    assert effects[0] == {
        "id": "effect-0",
        "kind": "statement_delete_completed",
        "affected_entity_id": "entity-2",
        "mutation_operation_id": "operation-1",
    }


def test_document_payload_preserves_every_frozen_scalar_type_and_float_bits() -> None:
    trace = _hostile_trace()
    typed_meta = freeze_json(
        {
            "none": None,
            "bool": False,
            "int": 1,
            "same-number-float": 1.0,
            "negative-zero": -0.0,
            "positive-zero": 0.0,
            "subnormal": 5e-324,
            "str": "1",
        }
    )
    assert isinstance(typed_meta, FrozenMap)
    typed_style = replace(trace.styles[0], meta=typed_meta)
    typed_trace = replace(trace, styles=(typed_style,))

    document = export_module._document_bytes(typed_trace, nonce="N" * 24).decode(
        "utf-8"
    )
    facts = _trace_payload(_payload_from_document(document))
    styles = facts["styles"]
    assert isinstance(styles, list)
    style = styles[0]
    assert isinstance(style, dict)
    meta = style["meta"]
    assert isinstance(meta, dict)
    entries = meta["entries"]
    assert entries == [
        ["none", {"kind": "none"}],
        ["bool", {"kind": "bool", "value": False}],
        ["int", {"kind": "int", "value": 1}],
        [
            "same-number-float",
            {"kind": "float", "hex": "0x1.0000000000000p+0"},
        ],
        ["negative-zero", {"kind": "float", "hex": "-0x0.0p+0"}],
        ["positive-zero", {"kind": "float", "hex": "0x0.0p+0"}],
        ["subnormal", {"kind": "float", "hex": "0x0.0000000000001p-1022"}],
        ["str", {"kind": "str", "value": "1"}],
    ]


def test_document_payload_is_raw_text_safe_and_unicode_runs_are_python_derived() -> (
    None
):
    document = export_module._document_bytes(_hostile_trace(), nonce="N" * 24).decode(
        "utf-8"
    )
    payload = _payload_from_document(document)
    facts = _trace_payload(payload)
    projection = _projection_payload(payload)

    assert _HOSTILE not in document
    assert "\\u003c/ScRiPt\\u003e" in document
    assert "\\u003cimg" in document
    assert "\\u0026" in document
    assert "\\ud83d\\ude00" in document
    assert "<img" not in document
    assert "</script><img" not in document.lower()

    configurations = facts["configurations"]
    assert isinstance(configurations, list)
    assert isinstance(configurations[0], dict)
    assert configurations[0]["hint"] == _HOSTILE
    snapshots = projection["snapshots"]
    assert isinstance(snapshots, list)
    assert isinstance(snapshots[0], dict)
    runs = snapshots[0]["render_runs"]
    assert isinstance(runs, list)
    assert [run["text"] for run in runs if isinstance(run, dict)][:3] == [
        "A",
        "😀",
        _HOSTILE[2:],
    ]
    occurrences = projection["occurrences"]
    assert isinstance(occurrences, list)
    assert occurrences[1] == {"occurrence_id": "occurrence-1", "text": "😀"}


def test_document_has_one_cascade_restrictive_nonce_csp_and_no_active_loader() -> None:
    document = export_module._document_bytes(_hostile_trace(), nonce="S" * 24).decode(
        "utf-8"
    )

    assert document.count("<style ") == 1
    assert document.count('nonce="' + "S" * 24 + '"') == 3
    assert "default-src 'none'" in document
    assert "connect-src 'none'" in document
    assert "img-src 'none'" in document
    assert "object-src 'none'" in document
    assert "worker-src 'none'" in document
    assert "script-src 'nonce-" + "S" * 24 + "'" in document
    assert "style-src 'nonce-" + "S" * 24 + "'" in document
    assert '<script nonce="' + "S" * 24 + '" type="application/json"' in document
    assert document.count("<script ") == 2
    for active_api in (
        "innerHTML",
        "eval(",
        "Function(",
        "fetch(",
        "XMLHttpRequest",
        "new Worker",
        "localStorage",
    ):
        assert active_api not in document
    assert "<link " not in document
    assert "<img " not in document
    assert "<iframe " not in document


@pytest.mark.parametrize(
    ("color", "expected"),
    [
        (ColorRecord("default", None, None, None), "color:#D9D9D9"),
        (ColorRecord("standard", None, 1, None), "color:#F4005F"),
        (ColorRecord("eight_bit", None, 196, None), "color:#FF0000"),
        (ColorRecord("truecolor", None, None, (17, 34, 51)), "color:#112233"),
        (ColorRecord("windows", None, 1, None), "color:#C50F1F"),
    ],
)  # type: ignore[untyped-decorator]
def test_generated_style_rules_use_only_validated_color_fields(
    color: ColorRecord, expected: str
) -> None:
    rule = _style_rule(7, StyleRecord(id="style-7", color=color, link=_HOSTILE))

    assert rule.startswith(".kr-captured-style-7{")
    assert expected in rule
    assert _HOSTILE not in rule


def test_style_projection_handles_reverse_dim_and_decorations() -> None:
    style = StyleRecord(
        id="style-0",
        color=ColorRecord("truecolor", None, None, (100, 120, 140)),
        bgcolor=ColorRecord("truecolor", None, None, (10, 20, 30)),
        bold=True,
        italic=True,
        underline2=True,
        strike=True,
        overline=True,
        reverse=True,
        dim=True,
    )

    rule = _style_rule(0, style)

    assert "color:#0B1015" in rule
    assert "background-color:#64788C" in rule
    assert "font-weight:700" in rule
    assert "font-style:italic" in rule
    assert "text-decoration-line:underline line-through overline" in rule
    assert "text-decoration-style:double" in rule


def test_encoder_rejects_unsupported_primitives_and_malformed_color() -> None:
    for value in (
        (1, 2),
        {1: "value"},
        9_007_199_254_740_992,
        float("inf"),
        object(),
    ):
        with pytest.raises(TraceEncodingError):
            _validate_primitive(value)

    malformed = ColorRecord("truecolor", None, None, None)
    with pytest.raises(TraceEncodingError, match="truecolor"):
        _style_rule(0, StyleRecord(id="style-0", color=malformed))


def test_export_success_creates_only_requested_file_and_returns_path(
    tmp_path: Path,
) -> None:
    trace = _hostile_trace()
    target = tmp_path / "trace.html"
    before = repr(trace)

    returned = export_html(trace, target)

    assert returned == target
    assert target.is_file()
    assert sorted(path.name for path in tmp_path.iterdir()) == ["trace.html"]
    assert repr(trace) == before
    payload = _payload_from_document(target.read_text(encoding="utf-8"))
    assert _trace_payload(payload)["complete"] is True


def test_empty_complete_trace_exports_explicit_zero_event_payload(
    tmp_path: Path,
) -> None:
    target = export_html(
        Trace(schema_version=1, complete=True), tmp_path / "empty.html"
    )
    document = target.read_text(encoding="utf-8")
    facts = _trace_payload(_payload_from_document(document))

    assert facts["complete"] is True
    assert facts["events"] == []
    assert "trace.events.length" in document


def test_export_requires_existing_directory_parent(tmp_path: Path) -> None:
    target = tmp_path / "missing" / "trace.html"

    with pytest.raises(FileNotFoundError):
        export_html(Trace(schema_version=1, complete=True), target)

    assert not target.exists()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "existing_kind", ["file", "directory", "symlink", "dangling"]
)
def test_export_refuses_every_existing_target_without_encoding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    existing_kind: str,
) -> None:
    target = tmp_path / "trace.html"
    sentinel = b"sentinel"
    if existing_kind == "file":
        target.write_bytes(sentinel)
    elif existing_kind == "directory":
        target.mkdir()
    elif existing_kind == "symlink":
        source = tmp_path / "source"
        source.write_bytes(sentinel)
        target.symlink_to(source)
    else:
        target.symlink_to(tmp_path / "absent")

    def unexpected_encoding(trace: Trace, *, nonce: str | None = None) -> bytes:
        raise AssertionError((trace, nonce))

    monkeypatch.setattr(export_module, "_document_bytes", unexpected_encoding)
    with pytest.raises(FileExistsError):
        export_html(Trace(schema_version=1, complete=True), target)

    if existing_kind == "file":
        assert target.read_bytes() == sentinel
    elif existing_kind == "directory":
        assert target.is_dir()
    else:
        assert target.is_symlink()
    assert _temporary_files(tmp_path, target) == []


@pytest.mark.parametrize(
    "failing_stage",
    [
        "_document_bytes",
        "_write_stream",
        "_flush_stream",
        "_close_stream",
        "_publish_no_replace",
    ],
)  # type: ignore[untyped-decorator]
def test_every_export_stage_failure_leaves_no_target_or_temporary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failing_stage: str,
) -> None:
    target = tmp_path / "trace.html"

    def fail(*args: object, **kwargs: object) -> None:
        raise OSError(errno.EIO, "injected failure", args, kwargs)

    monkeypatch.setattr(export_module, failing_stage, fail)
    with pytest.raises(OSError, match="injected failure"):
        export_html(Trace(schema_version=1, complete=True), target)

    assert not target.exists()
    assert _temporary_files(tmp_path, target) == []
    assert list(tmp_path.iterdir()) == []


def test_unconfirmed_publication_is_never_rolled_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "trace.html"

    def link_then_fail(temporary: Path, destination: Path) -> None:
        os.link(temporary, destination, follow_symlinks=False)
        raise OSError(errno.EIO, "failure after link")

    monkeypatch.setattr(export_module, "_publish_no_replace", link_then_fail)
    with pytest.raises(OSError, match="failure after link"):
        export_html(Trace(schema_version=1, complete=True), target)

    assert target.is_file()
    assert _temporary_files(tmp_path, target) == []


def test_temporary_cleanup_failure_rolls_back_publication_and_retries_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "trace.html"
    original_unlink = export_module._unlink_if_present
    calls = 0

    def fail_once(path: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError(errno.EIO, "temporary cleanup failed")
        original_unlink(path)

    monkeypatch.setattr(export_module, "_unlink_if_present", fail_once)
    with pytest.raises(OSError, match="temporary cleanup failed"):
        export_html(Trace(schema_version=1, complete=True), target)

    assert calls == 3
    assert not target.exists()
    assert list(tmp_path.iterdir()) == []


def test_raced_competitor_target_is_preserved_and_temp_is_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "trace.html"
    sentinel = b"competitor"

    def competitor_wins(temporary: Path, destination: Path) -> None:
        destination.write_bytes(sentinel)
        os.link(temporary, destination, follow_symlinks=False)

    monkeypatch.setattr(export_module, "_publish_no_replace", competitor_wins)
    with pytest.raises(FileExistsError):
        export_html(Trace(schema_version=1, complete=True), target)

    assert target.read_bytes() == sentinel
    assert _temporary_files(tmp_path, target) == []


def test_raced_hard_link_alias_is_preserved_after_failed_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "trace.html"
    original_publish = export_module._publish_no_replace

    def hard_link_competitor_wins(temporary: Path, destination: Path) -> None:
        os.link(temporary, destination, follow_symlinks=False)
        original_publish(temporary, destination)

    monkeypatch.setattr(
        export_module,
        "_publish_no_replace",
        hard_link_competitor_wins,
    )
    with pytest.raises(FileExistsError):
        export_html(Trace(schema_version=1, complete=True), target)

    assert target.is_file()
    assert _temporary_files(tmp_path, target) == []
    facts = _trace_payload(_payload_from_document(target.read_text(encoding="utf-8")))
    assert facts["complete"] is True


def test_atomic_no_clobber_holds_across_two_processes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if not hasattr(os, "fork"):
        pytest.skip("the supported viewer environment is POSIX")

    target = tmp_path / "trace.html"
    ready_read, ready_write = os.pipe()
    start_read, start_write = os.pipe()
    original_publish = export_module._publish_no_replace

    def gated_publish(temporary: Path, destination: Path) -> None:
        os.write(ready_write, b"R")
        assert os.read(start_read, 1) == b"S"
        original_publish(temporary, destination)

    monkeypatch.setattr(export_module, "_publish_no_replace", gated_publish)
    children: list[int] = []
    for _ in range(2):
        child = os.fork()
        if child == 0:
            try:
                export_html(Trace(schema_version=1, complete=True), target)
            except FileExistsError:
                os._exit(10)
            except BaseException:
                os._exit(20)
            os._exit(0)
        children.append(child)

    ready = b""
    while len(ready) < 2:
        readable, _, _ = select.select([ready_read], [], [], 10)
        assert readable, "child processes did not reach the publication barrier"
        ready += os.read(ready_read, 2 - len(ready))
    assert ready == b"RR"
    assert os.write(start_write, b"SS") == 2

    statuses: list[int] = []
    for child in children:
        _, status = os.waitpid(child, 0)
        assert os.WIFEXITED(status)
        statuses.append(os.WEXITSTATUS(status))
    for descriptor in (ready_read, ready_write, start_read, start_write):
        os.close(descriptor)

    assert sorted(statuses) == [0, 10]
    assert target.is_file()
    assert _temporary_files(tmp_path, target) == []


def test_invalid_nonce_fails_before_document_composition() -> None:
    with pytest.raises(ValueError, match="nonce"):
        export_module._document_bytes(
            Trace(schema_version=1, complete=True), nonce='"><script>'
        )


def test_export_rejects_nontrace_input(tmp_path: Path) -> None:
    with pytest.raises(TypeError, match="immutable Trace"):
        export_html(cast(Trace, object()), tmp_path / "trace.html")


def test_incomplete_trace_exports_absent_after_state_without_invention(
    tmp_path: Path,
) -> None:
    complete = _hostile_trace()
    incomplete_event = replace(
        complete.events[0],
        completion="incomplete",
        after_snapshot_id=None,
        result=None,
    )
    incomplete = replace(
        complete,
        complete=False,
        snapshots=(complete.snapshots[0],),
        occurrences=complete.occurrences[:2],
        metadata=complete.metadata[:1],
        events=(incomplete_event,),
    )
    target = export_html(incomplete, tmp_path / "incomplete.html")
    payload = _payload_from_document(target.read_text(encoding="utf-8"))
    facts = _trace_payload(payload)
    events = facts["events"]
    assert isinstance(events, list)
    event = events[0]
    assert isinstance(event, dict)

    assert facts["complete"] is False
    assert event["completion"] == "incomplete"
    assert event["after_snapshot_id"] is None
    assert event["result"] is None
