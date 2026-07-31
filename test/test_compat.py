from __future__ import annotations

import inspect
import json
import subprocess
import sys
from collections.abc import Sequence
from importlib import metadata
from pathlib import Path

import pytest
from kirin.ir import Statement

from kirin_rewrite_tracer import _compat


class _FakeDistribution:
    def __init__(self, root: Path, direct_url: str | None) -> None:
        self.root = root
        self.direct_url = direct_url

    def read_text(self, filename: str) -> str | None:
        assert filename == "direct_url.json"
        return self.direct_url

    def locate_file(self, path: str) -> Path:
        return self.root / path


def _run_git(repository: Path, arguments: Sequence[str]) -> str:
    result = subprocess.run(
        ("git", "-C", repository.as_posix(), *arguments),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _git_checkout(tmp_path: Path) -> tuple[Path, Path, str]:
    repository = tmp_path / "checkout"
    module_file = repository / "src" / "kirin" / "__init__.py"
    module_file.parent.mkdir(parents=True)
    module_file.write_text("# fixture\n", encoding="utf-8")
    _run_git(repository.parent, ("init", repository.as_posix()))
    _run_git(repository, ("config", "user.name", "Compatibility Test"))
    _run_git(repository, ("config", "user.email", "compatibility@example.invalid"))
    _run_git(repository, ("add", "src/kirin/__init__.py"))
    _run_git(repository, ("commit", "-m", "fixture"))
    return (
        repository,
        module_file.resolve(),
        _run_git(repository, ("rev-parse", "HEAD")),
    )


def test_runtime_accepts_each_supported_cpython_minor() -> None:
    for minor in (10, 11, 12, 13):
        assert _compat._verify_runtime("CPython", (3, minor, 0)) == (3, minor, 0)


def test_runtime_rejects_outside_the_exact_envelope() -> None:
    cases = (
        ("PyPy", (3, 10, 0)),
        ("CPython", (3, 9, 99)),
        ("CPython", (3, 14, 0)),
        ("CPython", (4, 0, 0)),
    )
    for implementation, version in cases:
        with pytest.raises(_compat.CompatibilityError) as caught:
            _compat._verify_runtime(implementation, version)
        assert caught.value.code == "python-runtime"


def test_rich_version_comes_from_distribution_metadata() -> None:
    assert (
        _compat._verify_rich_version(lambda name: "15.0.0" if name == "rich" else "")
        == "15.0.0"
    )
    with pytest.raises(_compat.CompatibilityError) as caught:
        _compat._verify_rich_version(lambda _name: "15.0.1")
    assert caught.value.code == "rich-version"

    def missing(_name: str) -> str:
        raise metadata.PackageNotFoundError("rich")

    with pytest.raises(_compat.CompatibilityError) as missing_caught:
        _compat._verify_rich_version(missing)
    assert missing_caught.value.code == "rich-version"


def test_exact_pep610_vcs_provenance_is_accepted(tmp_path: Path) -> None:
    module_file = tmp_path / "installed" / "kirin" / "__init__.py"
    module_file.parent.mkdir(parents=True)
    module_file.write_text("# installed fixture\n", encoding="utf-8")
    document = {
        "url": "https://example.invalid/kirin.git",
        "vcs_info": {
            "vcs": "git",
            "commit_id": _compat.PINNED_KIRIN_COMMIT,
            "requested_revision": _compat.PINNED_KIRIN_COMMIT,
        },
    }
    distribution = _FakeDistribution(
        module_file.parents[1], json.dumps(document, separators=(",", ":"))
    )

    assert _compat._pep610_vcs_proof(distribution, module_file.resolve()) == (
        _compat.ProvenanceProof(
            kind="pep610-vcs", commit_id=_compat.PINNED_KIRIN_COMMIT
        )
    )


def test_nonproof_metadata_never_establishes_the_commit(tmp_path: Path) -> None:
    documents = (
        None,
        "{",
        "{}",
        '{"url":"file:///tmp/kirin","dir_info":{"editable":true}}',
        (
            '{"url":"https://example.invalid/kirin.git",'
            '"vcs_info":{"vcs":"hg","commit_id":'
            f'"{_compat.PINNED_KIRIN_COMMIT}"}}'
        ),
        (
            '{"url":"https://example.invalid/kirin.git",'
            '"vcs_info":{"vcs":"git","commit_id":"' + ("0" * 40) + '"}}'
        ),
        (
            '{"url":"https://example.invalid/kirin.git",'
            '"archive_info":{"hash":"sha256=descriptor-fingerprint"}}'
        ),
    )
    for index, document in enumerate(documents):
        module_file = tmp_path / str(index) / "installed" / "kirin" / "__init__.py"
        module_file.parent.mkdir(parents=True)
        module_file.write_text("# installed fixture\n", encoding="utf-8")
        distribution = _FakeDistribution(module_file.parents[1], document)
        assert _compat._pep610_vcs_proof(distribution, module_file.resolve()) is None


def test_pep610_metadata_must_belong_to_imported_module(tmp_path: Path) -> None:
    module_file = tmp_path / "shadow" / "kirin" / "__init__.py"
    module_file.parent.mkdir(parents=True)
    module_file.write_text("# shadow fixture\n", encoding="utf-8")
    installed_root = tmp_path / "installed"
    installed_module = installed_root / "kirin" / "__init__.py"
    installed_module.parent.mkdir(parents=True)
    installed_module.write_text("# distribution fixture\n", encoding="utf-8")
    distribution = _FakeDistribution(
        installed_root,
        json.dumps(
            {
                "url": "https://example.invalid/kirin.git",
                "vcs_info": {
                    "vcs": "git",
                    "commit_id": _compat.PINNED_KIRIN_COMMIT,
                },
            }
        ),
    )
    assert _compat._pep610_vcs_proof(distribution, module_file.resolve()) is None


def test_clean_exact_git_checkout_is_accepted(tmp_path: Path) -> None:
    _, module_file, head = _git_checkout(tmp_path)
    assert _compat._clean_git_checkout_proof(
        module_file, expected_commit=head
    ) == _compat.ProvenanceProof(kind="clean-git-checkout", commit_id=head)


def test_git_checkout_rejects_wrong_revision_and_dirty_state(tmp_path: Path) -> None:
    repository, module_file, head = _git_checkout(tmp_path)
    assert (
        _compat._clean_git_checkout_proof(module_file, expected_commit="0" * len(head))
        is None
    )
    module_file.write_text("# changed fixture\n", encoding="utf-8")
    assert _compat._clean_git_checkout_proof(module_file, expected_commit=head) is None
    _run_git(repository, ("checkout", "--", "src/kirin/__init__.py"))
    (repository / "untracked.txt").write_text("untracked\n", encoding="utf-8")
    assert _compat._clean_git_checkout_proof(module_file, expected_commit=head) is None


def test_git_checkout_rejects_an_ignored_untracked_import(tmp_path: Path) -> None:
    repository = tmp_path / "checkout"
    repository.mkdir()
    _run_git(repository.parent, ("init", repository.as_posix()))
    _run_git(repository, ("config", "user.name", "Compatibility Test"))
    _run_git(repository, ("config", "user.email", "compatibility@example.invalid"))
    (repository / ".gitignore").write_text("generated/\n", encoding="utf-8")
    _run_git(repository, ("add", ".gitignore"))
    _run_git(repository, ("commit", "-m", "fixture"))
    module_file = repository / "generated" / "kirin" / "__init__.py"
    module_file.parent.mkdir(parents=True)
    module_file.write_text("# ignored fixture\n", encoding="utf-8")
    head = _run_git(repository, ("rev-parse", "HEAD"))
    assert (
        _compat._clean_git_checkout_proof(module_file.resolve(), expected_commit=head)
        is None
    )


def test_verifier_falls_back_from_nonproof_metadata_to_clean_git(
    tmp_path: Path,
) -> None:
    _, module_file, head = _git_checkout(tmp_path)
    nonproof = _FakeDistribution(
        module_file.parents[2],
        '{"url":"file:///checkout","dir_info":{"editable":true}}',
    )

    proof = _compat._verify_kirin_provenance(
        module_file,
        distribution_getter=lambda _name: nonproof,
        expected_commit=head,
    )
    assert proof == _compat.ProvenanceProof(kind="clean-git-checkout", commit_id=head)


def test_exact_raw_descriptors_are_returned() -> None:
    descriptors = _compat._verify_raw_descriptors()
    for owner, name, descriptor in descriptors.items():
        assert inspect.getattr_static(owner, name) is descriptor


def test_shape_equivalent_descriptor_replacement_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = inspect.getattr_static(Statement, "delete")

    def replacement(self: Statement, safe: bool = True) -> None:
        assert self is not None or safe

    replacement.__module__ = original.__module__
    replacement.__qualname__ = original.__qualname__
    monkeypatch.setattr(Statement, "delete", replacement)

    with pytest.raises(_compat.CompatibilityError) as caught:
        _compat._verify_raw_descriptors()
    assert caught.value.code == "descriptor"
    assert "replaced" in caught.value.detail


def test_replacement_of_each_required_descriptor_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    originals = _compat._verify_raw_descriptors()
    for owner, name, _descriptor in originals.items():
        with monkeypatch.context() as scoped:
            scoped.setattr(owner, name, object())
            with pytest.raises(_compat.CompatibilityError) as caught:
                _compat._verify_raw_descriptors()
            assert caught.value.code == "descriptor"
            assert name in caught.value.detail


def test_descriptor_shape_is_checked_independently_of_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imported = _compat._IMPORTED_RAW_DESCRIPTORS
    assert imported is not None

    def malformed(self: Statement) -> None:
        assert self is not None

    monkeypatch.setattr(Statement, "delete", malformed)
    monkeypatch.setattr(
        _compat,
        "_IMPORTED_RAW_DESCRIPTORS",
        _compat.RawDescriptors(
            imported.statement_replace_by,
            imported.ssa_value_replace_by,
            imported.statement_from_stmt,
            imported.region_clone,
            malformed,
        ),
    )
    with pytest.raises(_compat.CompatibilityError) as caught:
        _compat._verify_raw_descriptors()
    assert caught.value.code == "descriptor"
    assert "owner" in caught.value.detail or "signature" in caught.value.detail


def test_shape_spoofed_preimport_replacement_fails_pinned_source_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imported = _compat._IMPORTED_RAW_DESCRIPTORS
    assert imported is not None
    original = inspect.getattr_static(Statement, "delete")

    def replacement(self: Statement, safe: bool = True) -> None:
        del self, safe

    replacement.__module__ = original.__module__
    replacement.__qualname__ = original.__qualname__
    monkeypatch.setattr(Statement, "delete", replacement)
    monkeypatch.setattr(
        _compat,
        "_IMPORTED_RAW_DESCRIPTORS",
        _compat.RawDescriptors(
            imported.statement_replace_by,
            imported.ssa_value_replace_by,
            imported.statement_from_stmt,
            imported.region_clone,
            replacement,
        ),
    )

    with pytest.raises(_compat.CompatibilityError) as caught:
        _compat._verify_raw_descriptors()
    assert caught.value.code == "descriptor"
    assert "pinned implementation" in caught.value.detail


def test_preflight_accepts_installed_pins_without_mutating_profile() -> None:
    before = sys.getprofile()
    assert before is None
    report = _compat.preflight_compatibility(
        active_session=False, get_profile=lambda: before
    )
    assert report.python_version[:2] in {(3, 10), (3, 11), (3, 12), (3, 13)}
    assert report.rich_version == "15.0.0"
    assert report.kirin_provenance == _compat.ProvenanceProof(
        kind="pep610-vcs", commit_id=_compat.PINNED_KIRIN_COMMIT
    )
    assert sys.getprofile() is before


def test_preflight_rejects_nesting_and_an_occupied_profile_slot() -> None:
    def dependency_check_must_not_run(_name: str) -> str:
        raise AssertionError("dependency check ran after an entry-slot rejection")

    with pytest.raises(_compat.CompatibilityError) as nested:
        _compat.preflight_compatibility(
            active_session=True,
            get_profile=lambda: None,
            version_getter=dependency_check_must_not_run,
        )
    assert nested.value.code == "active-session"

    foreign_profile = object()
    with pytest.raises(_compat.CompatibilityError) as occupied:
        _compat.preflight_compatibility(
            active_session=False,
            get_profile=lambda: foreign_profile,
            version_getter=dependency_check_must_not_run,
        )
    assert occupied.value.code == "profile-occupied"
