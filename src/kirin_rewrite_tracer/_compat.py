"""Pinned runtime and dependency compatibility checks.

This module deliberately keeps commit provenance separate from runtime API-shape
checks.  Matching Kirin objects are necessary for tracing, but only PEP 610 VCS
metadata or a clean Git checkout can prove the supported source revision.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import platform
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from types import FunctionType
from typing import Literal, Protocol, cast

import kirin
from kirin.ir import Region, SSAValue, Statement

PINNED_KIRIN_COMMIT = "7cdc2e02ab7ef0b3f80aaa88f930ff34015d240a"
PINNED_KIRIN_DISTRIBUTION = "kirin-toolchain"
PINNED_RICH_VERSION = "15.0.0"

CompatibilityCode = Literal[
    "active-session",
    "descriptor",
    "kirin-provenance",
    "profile-occupied",
    "python-runtime",
    "rich-version",
]


class CompatibilityError(RuntimeError):
    """Internal preflight failure for conversion to ``UnsupportedTraceError``."""

    def __init__(self, code: CompatibilityCode, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True, slots=True)
class ProvenanceProof:
    """The exact, non-fingerprint proof used for the Kirin revision."""

    kind: Literal["pep610-vcs", "clean-git-checkout"]
    commit_id: str


@dataclass(frozen=True, slots=True)
class RawDescriptors:
    """Exact raw descriptor objects saved for transactional wrapper installation."""

    statement_replace_by: object
    ssa_value_replace_by: object
    statement_from_stmt: object
    region_clone: object
    statement_delete: object

    def items(self) -> tuple[tuple[type[object], str, object], ...]:
        return (
            (Statement, "replace_by", self.statement_replace_by),
            (SSAValue, "replace_by", self.ssa_value_replace_by),
            (Statement, "from_stmt", self.statement_from_stmt),
            (Region, "clone", self.region_clone),
            (Statement, "delete", self.statement_delete),
        )


@dataclass(frozen=True, slots=True)
class CompatibilityReport:
    """Validated inputs needed by the activation transaction."""

    python_version: tuple[int, int, int]
    rich_version: str
    kirin_provenance: ProvenanceProof
    descriptors: RawDescriptors


class _Distribution(Protocol):
    def read_text(self, filename: str) -> str | None: ...

    def locate_file(self, path: str) -> os.PathLike[str]: ...


_DistributionGetter = Callable[[str], _Distribution]


@dataclass(frozen=True, slots=True)
class _ParameterShape:
    name: str
    kind: object
    default: object = inspect.Parameter.empty


@dataclass(frozen=True, slots=True)
class _DescriptorShape:
    owner: type[object]
    name: str
    wrapper: Literal["function", "classmethod"]
    module: str
    qualname: str
    source_sha256: str
    parameters: tuple[_ParameterShape, ...]


_POSITIONAL = inspect.Parameter.POSITIONAL_OR_KEYWORD
_DESCRIPTOR_SHAPES = (
    _DescriptorShape(
        Statement,
        "replace_by",
        "function",
        "kirin.ir.nodes.stmt",
        "Statement.replace_by",
        "fe934016d26a14e530c033c145ce4109ea70d7cf968514e25be3791e6bb8deab",
        (
            _ParameterShape("self", _POSITIONAL),
            _ParameterShape("stmt", _POSITIONAL),
        ),
    ),
    _DescriptorShape(
        SSAValue,
        "replace_by",
        "function",
        "kirin.ir.ssa",
        "SSAValue.replace_by",
        "4271530ddb096aa65ad9e41fa8722a583cc8e2387ef416fcd65c9798071e981c",
        (
            _ParameterShape("self", _POSITIONAL),
            _ParameterShape("other", _POSITIONAL),
        ),
    ),
    _DescriptorShape(
        Statement,
        "from_stmt",
        "classmethod",
        "kirin.ir.nodes.stmt",
        "Statement.from_stmt",
        "86ac9b04674041cb85961b64ebcbf5e084c64fa4b0feb805e53ed1ef641c5827",
        (
            _ParameterShape("cls", _POSITIONAL),
            _ParameterShape("other", _POSITIONAL),
            _ParameterShape("args", _POSITIONAL, None),
            _ParameterShape("regions", _POSITIONAL, None),
            _ParameterShape("successors", _POSITIONAL, None),
            _ParameterShape("attributes", _POSITIONAL, None),
        ),
    ),
    _DescriptorShape(
        Region,
        "clone",
        "function",
        "kirin.ir.nodes.region",
        "Region.clone",
        "add1bc50b130e091e8f4e70f7483cb6ee7d95d1f7c77bb4882021119a040b675",
        (
            _ParameterShape("self", _POSITIONAL),
            _ParameterShape("ssamap", _POSITIONAL, None),
        ),
    ),
    _DescriptorShape(
        Statement,
        "delete",
        "function",
        "kirin.ir.nodes.stmt",
        "Statement.delete",
        "20d895cc5b3851ead391148e2bdd8e5d9d1d519aa56efc4b4b65b46382d063f6",
        (
            _ParameterShape("self", _POSITIONAL),
            _ParameterShape("safe", _POSITIONAL, True),
        ),
    ),
)


def _read_raw_descriptors() -> RawDescriptors:
    try:
        return RawDescriptors(
            statement_replace_by=inspect.getattr_static(Statement, "replace_by"),
            ssa_value_replace_by=inspect.getattr_static(SSAValue, "replace_by"),
            statement_from_stmt=inspect.getattr_static(Statement, "from_stmt"),
            region_clone=inspect.getattr_static(Region, "clone"),
            statement_delete=inspect.getattr_static(Statement, "delete"),
        )
    except AttributeError as error:
        raise CompatibilityError(
            "descriptor", "a required Kirin mutation descriptor is absent"
        ) from error


try:
    # Identity detects replacement after the tracer package has been imported.
    _IMPORTED_RAW_DESCRIPTORS: RawDescriptors | None = _read_raw_descriptors()
except CompatibilityError:
    # A malformed environment remains importable so context entry can reject it.
    _IMPORTED_RAW_DESCRIPTORS = None


def _verify_runtime(
    implementation: str, version: tuple[int, int, int]
) -> tuple[int, int, int]:
    if implementation != "CPython" or not ((3, 10, 0) <= version < (3, 14, 0)):
        raise CompatibilityError("python-runtime", "CPython >=3.10,<3.14 is required")
    return version


def _verify_rich_version(version_getter: Callable[[str], str]) -> str:
    try:
        version = version_getter("rich")
    except metadata.PackageNotFoundError as error:
        raise CompatibilityError(
            "rich-version", f"Rich {PINNED_RICH_VERSION} is required"
        ) from error
    if version != PINNED_RICH_VERSION:
        raise CompatibilityError(
            "rich-version", f"Rich {PINNED_RICH_VERSION} is required"
        )
    return version


def _system_distribution(name: str) -> _Distribution:
    return cast(_Distribution, metadata.distribution(name))


def _resolved_file(path: os.PathLike[str] | str) -> Path | None:
    try:
        return Path(path).resolve(strict=True)
    except (OSError, RuntimeError, TypeError):
        return None


def _pep610_vcs_proof(
    distribution: _Distribution,
    module_file: Path,
    *,
    expected_commit: str = PINNED_KIRIN_COMMIT,
) -> ProvenanceProof | None:
    """Return a VCS proof only when it belongs to the imported Kirin package."""

    try:
        raw = distribution.read_text("direct_url.json")
    except (OSError, UnicodeError, ValueError):
        return None
    if raw is None:
        return None
    try:
        document = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(document, dict) or not isinstance(document.get("url"), str):
        return None
    vcs_info = document.get("vcs_info")
    if not isinstance(vcs_info, dict):
        return None
    if vcs_info.get("vcs") != "git" or vcs_info.get("commit_id") != expected_commit:
        return None

    # Do not accept metadata for another distribution when a different Kirin was
    # imported earlier on sys.path.
    try:
        installed_module = distribution.locate_file("kirin/__init__.py")
    except (OSError, RuntimeError, TypeError):
        return None
    if _resolved_file(installed_module) != module_file:
        return None
    return ProvenanceProof("pep610-vcs", expected_commit)


def _git(cwd: Path, *arguments: str) -> subprocess.CompletedProcess[str] | None:
    environment = os.environ.copy()
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    environment["LC_ALL"] = "C"
    try:
        return subprocess.run(
            ("git", "-C", os.fspath(cwd), *arguments),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            env=environment,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return None


def _git_stdout(cwd: Path, *arguments: str) -> str | None:
    result = _git(cwd, *arguments)
    if result is None or result.returncode != 0:
        return None
    return result.stdout


def _clean_git_checkout_proof(
    module_file: Path,
    *,
    expected_commit: str = PINNED_KIRIN_COMMIT,
) -> ProvenanceProof | None:
    """Prove that the imported module is tracked by a clean exact checkout."""

    root_text = _git_stdout(module_file.parent, "rev-parse", "--show-toplevel")
    if root_text is None:
        return None
    root = _resolved_file(root_text.strip())
    if root is None:
        return None
    try:
        relative_module = module_file.relative_to(root)
    except ValueError:
        return None

    head = _git_stdout(root, "rev-parse", "--verify", "HEAD")
    if head is None or head.strip() != expected_commit:
        return None
    status = _git_stdout(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--ignore-submodules=none",
    )
    if status is None or status:
        return None
    tracked = _git(
        root,
        "ls-files",
        "--error-unmatch",
        "--",
        relative_module.as_posix(),
    )
    if tracked is None or tracked.returncode != 0:
        return None
    return ProvenanceProof("clean-git-checkout", expected_commit)


def _verify_kirin_provenance(
    module_path: os.PathLike[str] | str,
    *,
    distribution_getter: _DistributionGetter = _system_distribution,
    expected_commit: str = PINNED_KIRIN_COMMIT,
) -> ProvenanceProof:
    module_file = _resolved_file(module_path)
    if module_file is None or not module_file.is_file():
        raise CompatibilityError(
            "kirin-provenance", "the imported Kirin module path is not a file"
        )

    try:
        distribution = distribution_getter(PINNED_KIRIN_DISTRIBUTION)
    except (metadata.PackageNotFoundError, OSError, UnicodeError, ValueError):
        distribution = None
    if distribution is not None:
        proof = _pep610_vcs_proof(
            distribution, module_file, expected_commit=expected_commit
        )
        if proof is not None:
            return proof

    proof = _clean_git_checkout_proof(module_file, expected_commit=expected_commit)
    if proof is not None:
        return proof
    raise CompatibilityError(
        "kirin-provenance",
        "Kirin must have exact PEP 610 VCS provenance or be an exact clean checkout",
    )


def _callable_from_descriptor(
    descriptor: object, shape: _DescriptorShape
) -> FunctionType:
    if shape.wrapper == "function":
        if type(descriptor) is not FunctionType:
            raise CompatibilityError(
                "descriptor", f"{shape.qualname} must be a raw Python function"
            )
        return descriptor
    if type(descriptor) is not classmethod:
        raise CompatibilityError(
            "descriptor", f"{shape.qualname} must be a raw classmethod"
        )
    function = descriptor.__wrapped__
    if type(function) is not FunctionType:
        raise CompatibilityError(
            "descriptor", f"{shape.qualname} must wrap a Python function"
        )
    return function


def _verify_descriptor_shape(descriptor: object, shape: _DescriptorShape) -> None:
    function = _callable_from_descriptor(descriptor, shape)
    if function.__module__ != shape.module or function.__qualname__ != shape.qualname:
        raise CompatibilityError(
            "descriptor", f"{shape.qualname} has an unexpected owner"
        )
    if (
        inspect.isgeneratorfunction(function)
        or inspect.iscoroutinefunction(function)
        or inspect.isasyncgenfunction(function)
    ):
        raise CompatibilityError(
            "descriptor", f"{shape.qualname} must be an ordinary synchronous function"
        )
    try:
        source = inspect.getsource(function)
    except (OSError, TypeError) as error:
        raise CompatibilityError(
            "descriptor", f"{shape.qualname} has no verifiable pinned source"
        ) from error
    source_digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if source_digest != shape.source_sha256:
        raise CompatibilityError(
            "descriptor", f"{shape.qualname} does not match the pinned implementation"
        )
    try:
        parameters = tuple(inspect.signature(function).parameters.values())
    except (TypeError, ValueError) as error:
        raise CompatibilityError(
            "descriptor", f"{shape.qualname} has no supported signature"
        ) from error
    if len(parameters) != len(shape.parameters):
        raise CompatibilityError(
            "descriptor", f"{shape.qualname} has an unexpected signature"
        )
    for actual, expected in zip(parameters, shape.parameters, strict=True):
        if (
            actual.name != expected.name
            or actual.kind is not expected.kind
            or actual.default is not expected.default
        ):
            raise CompatibilityError(
                "descriptor", f"{shape.qualname} has an unexpected signature"
            )


def _verify_raw_descriptors() -> RawDescriptors:
    current = _read_raw_descriptors()
    imported = _IMPORTED_RAW_DESCRIPTORS
    if imported is None:
        raise CompatibilityError(
            "descriptor", "the imported Kirin descriptors were already malformed"
        )
    for shape, (_, _, current_descriptor), (_, _, imported_descriptor) in zip(
        _DESCRIPTOR_SHAPES, current.items(), imported.items(), strict=True
    ):
        if current_descriptor is not imported_descriptor:
            raise CompatibilityError(
                "descriptor", f"{shape.qualname} was replaced before activation"
            )
        _verify_descriptor_shape(current_descriptor, shape)
    return current


def preflight_compatibility(
    *,
    active_session: bool,
    get_profile: Callable[[], object | None] = sys.getprofile,
    version_getter: Callable[[str], str] = metadata.version,
    distribution_getter: _DistributionGetter = _system_distribution,
) -> CompatibilityReport:
    """Validate every entry-time compatibility prerequisite without mutation."""

    version = (sys.version_info.major, sys.version_info.minor, sys.version_info.micro)
    runtime = _verify_runtime(platform.python_implementation(), version)
    if active_session:
        raise CompatibilityError("active-session", "trace sessions cannot be nested")
    if get_profile() is not None:
        raise CompatibilityError(
            "profile-occupied", "the current thread profile slot is occupied"
        )
    rich_version = _verify_rich_version(version_getter)
    module_path = getattr(kirin, "__file__", None)
    if not isinstance(module_path, (str, os.PathLike)):
        raise CompatibilityError(
            "kirin-provenance", "the imported Kirin module has no filesystem path"
        )
    provenance = _verify_kirin_provenance(
        module_path, distribution_getter=distribution_getter
    )
    descriptors = _verify_raw_descriptors()
    return CompatibilityReport(runtime, rich_version, provenance, descriptors)


__all__ = (
    "PINNED_KIRIN_COMMIT",
    "PINNED_RICH_VERSION",
    "CompatibilityError",
    "CompatibilityReport",
    "ProvenanceProof",
    "RawDescriptors",
    "preflight_compatibility",
)
