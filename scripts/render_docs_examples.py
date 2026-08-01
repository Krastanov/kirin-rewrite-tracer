"""Render the canonical EXAMPLES.md programs as part of every MkDocs build."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.files import File, Files

ROOT = Path(__file__).resolve().parents[1]
FUSION_PROJECT = ROOT / "scripts" / "docs_fusion_env"
EXAMPLE_OUTPUTS = {
    "1": "dce-trace.html",
    "2": "fold-trace.html",
    "3": "inline-trace.html",
    "4": "scf2cf-trace.html",
    "5": "fusion-trace.html",
    "6.1": "nonconvergent-trace.html",
    "6.2": "crash-trace.html",
    "6.3": None,
}
HEADING_PATTERN = re.compile(r"^(?:## (\d+)\.|### (\d+\.\d+))", re.MULTILINE)
PYTHON_BLOCK_PATTERN = re.compile(r"```python\n(.*?)\n```", re.DOTALL)
TRACE_DATA_PATTERN = re.compile(
    r'(?P<open><script nonce="[^"]+" type="application/json" '
    r'id="trace-data">)(?P<data>.*?)(?P<close></script>)',
    re.DOTALL,
)
LANES_VERSION_PATTERN = re.compile(
    r"`bloqade-lanes` ([0-9][0-9.]*) works against that commit"
)
RICH_REQUIREMENT_PATTERN = re.compile(r"uv pip install bloqade-lanes (rich==[^\s]+)")
KIRIN_REQUIREMENT_PATTERN = re.compile(
    r'uv pip install --no-deps "(kirin-toolchain @ [^"]+)"'
)


def _python_block(section: str, description: str) -> str:
    match = PYTHON_BLOCK_PATTERN.search(section)
    if match is None:
        raise RuntimeError(f"{description} has no Python code block")
    return match.group(1) + "\n"


def _programs(markdown: str) -> tuple[str, dict[str, str]]:
    helper_start = markdown.index("## A helper you will reuse")
    helper_end = markdown.index("## 1.", helper_start)
    helper = _python_block(markdown[helper_start:helper_end], "tree helper")

    matches = list(HEADING_PATTERN.finditer(markdown))
    programs: dict[str, str] = {}
    for index, match in enumerate(matches):
        number = match.group(1) or match.group(2)
        if number is None:  # pragma: no cover - guaranteed by the pattern
            raise RuntimeError("example heading lost its number")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        code = PYTHON_BLOCK_PATTERN.search(markdown[match.end() : end])
        if code is not None:
            if number in programs:
                raise RuntimeError(f"EXAMPLES.md repeats example number {number}")
            programs[number] = code.group(1) + "\n"

    if programs.keys() != EXAMPLE_OUTPUTS.keys():
        raise RuntimeError(
            "EXAMPLES.md scenarios changed; update the documentation renderer "
            "and gallery"
        )
    return helper, programs


def _requirement(pattern: re.Pattern[str], markdown: str, description: str) -> str:
    match = pattern.search(markdown)
    if match is None:
        raise RuntimeError(f"EXAMPLES.md no longer declares {description}")
    return match.group(1)


def _command_environment(
    updates: dict[str, str] | None = None,
) -> dict[str, str]:
    environment = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV"):
        environment.pop(name, None)
    environment["PYTHONHASHSEED"] = "0"
    environment["PYTHONNOUSERSITE"] = "1"
    if updates is not None:
        environment.update(updates)
    return environment


def _run(
    command: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    environment_updates: dict[str, str] | None = None,
) -> None:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=_command_environment(environment_updates),
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(
            f"command timed out after {timeout_seconds}s: {' '.join(command)}"
        ) from error
    if completed.returncode == 0:
        return
    detail = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    raise RuntimeError(f"command failed ({' '.join(command)}):\n{detail}")


def _fusion_python(
    temporary_root: Path,
    *,
    lanes_version: str,
    rich_requirement: str,
    kirin_requirement: str,
) -> Path:
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required to render the bloqade-lanes example")

    project = (FUSION_PROJECT / "pyproject.toml").read_text(encoding="utf-8")
    requirements = (
        f"bloqade-lanes=={lanes_version}",
        rich_requirement,
        kirin_requirement,
    )
    missing = []
    for requirement in requirements:
        if requirement not in project:
            missing.append(requirement)
    if missing:
        raise RuntimeError(
            "the locked fusion environment disagrees with EXAMPLES.md: "
            f"{', '.join(missing)}"
        )

    environment = temporary_root / "fusion-environment"
    _run(
        [
            uv,
            "sync",
            "--project",
            str(FUSION_PROJECT),
            "--locked",
            "--python",
            sys.executable,
            "--no-install-project",
        ],
        cwd=ROOT,
        timeout_seconds=300,
        environment_updates={"UV_PROJECT_ENVIRONMENT": str(environment)},
    )
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    _run(
        [uv, "pip", "install", "--python", str(python), "--no-deps", str(ROOT)],
        cwd=ROOT,
        timeout_seconds=300,
    )
    return python


def _portable_filename(filename: str, *, run_dir: Path, number: str) -> str:
    path = Path(filename)
    try:
        return (Path("examples") / number / path.relative_to(run_dir)).as_posix()
    except ValueError:
        pass

    if "site-packages" in path.parts:
        index = path.parts.index("site-packages")
        return Path(*path.parts[index:]).as_posix()

    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        pass

    return path.name


def _normalize_stack_paths(export: Path, *, run_dir: Path, number: str) -> None:
    document = export.read_text(encoding="utf-8")
    match = TRACE_DATA_PATTERN.search(document)
    if match is None:
        raise RuntimeError(f"{export.name} has no embedded trace data")

    payload = json.loads(match.group("data"))
    for stack in payload["trace"]["stacks"]:
        for frame in stack["frames"]:
            frame["filename"] = _portable_filename(
                frame["filename"], run_dir=run_dir, number=number
            )

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
    replacement = f"{match.group('open')}{serialized}{match.group('close')}"
    export.write_text(
        document[: match.start()] + replacement + document[match.end() :],
        encoding="utf-8",
    )


def render_examples() -> dict[str, bytes]:
    markdown = (ROOT / "EXAMPLES.md").read_text(encoding="utf-8")
    helper, programs = _programs(markdown)
    lanes_version = _requirement(
        LANES_VERSION_PATTERN, markdown, "the compatible bloqade-lanes version"
    )
    rich_requirement = _requirement(
        RICH_REQUIREMENT_PATTERN, markdown, "the Rich requirement"
    )
    kirin_requirement = _requirement(
        KIRIN_REQUIREMENT_PATTERN, markdown, "the pinned Kirin requirement"
    )
    with tempfile.TemporaryDirectory(prefix="kirin-rewrite-tracer-docs-") as raw:
        temporary_root = Path(raw)
        fusion_python = _fusion_python(
            temporary_root,
            lanes_version=lanes_version,
            rich_requirement=rich_requirement,
            kirin_requirement=kirin_requirement,
        )
        for number, program in programs.items():
            run_dir = temporary_root / f"example-{number.replace('.', '-')}"
            run_dir.mkdir()
            (run_dir / "tree.py").write_text(helper, encoding="utf-8")
            script = run_dir / "example.py"
            script.write_text(program, encoding="utf-8")
            interpreter = fusion_python if number == "5" else Path(sys.executable)
            _run(
                [str(interpreter), str(script)],
                cwd=run_dir,
                timeout_seconds=120,
            )

            output_name = EXAMPLE_OUTPUTS[number]
            if output_name is None:
                continue
            generated = run_dir / output_name
            if not generated.is_file():
                raise RuntimeError(f"example {number} did not create {output_name}")
            _normalize_stack_paths(generated, run_dir=run_dir, number=number)
        rendered = {}
        for number, output_name in EXAMPLE_OUTPUTS.items():
            if output_name is None:
                continue
            example_dir = temporary_root / f"example-{number.replace('.', '-')}"
            rendered[output_name] = (example_dir / output_name).read_bytes()

    expected = {name for name in EXAMPLE_OUTPUTS.values() if name is not None}
    if rendered.keys() != expected:
        raise RuntimeError("the rendered visualization set is incomplete")
    return rendered


def _validate_visualizations(directory: Path) -> None:
    expected = {name for name in EXAMPLE_OUTPUTS.values() if name is not None}
    actual = {path.name for path in directory.glob("*.html")}
    if actual != expected:
        raise RuntimeError(
            "documentation visualization set differs: "
            f"expected {sorted(expected)}, found {sorted(actual)}"
        )

    for output_name in sorted(expected):
        export = directory / output_name
        if not export.is_file():
            raise RuntimeError(f"documentation build omitted {output_name}")
        document = export.read_text(encoding="utf-8")
        match = TRACE_DATA_PATTERN.search(document)
        if match is None:
            raise RuntimeError(f"{output_name} has no embedded trace data")
        payload = json.loads(match.group("data"))
        filenames = (
            frame["filename"]
            for stack in payload["trace"]["stacks"]
            for frame in stack["frames"]
        )
        absolute = []
        for filename in filenames:
            if Path(filename).is_absolute():
                absolute.append(filename)
        if absolute:
            raise RuntimeError(
                f"{output_name} contains absolute stack paths: {absolute}"
            )


def on_files(files: Files, *, config: MkDocsConfig) -> Files:
    """Inject freshly rendered trace viewers as virtual MkDocs files."""

    for output_name, content in render_examples().items():
        files.append(
            File.generated(
                config,
                f"visualizations/{output_name}",
                content=content,
            )
        )
    return files


def on_post_build(*, config: MkDocsConfig) -> None:
    """Prove every expected viewer reached the completed site."""

    _validate_visualizations(Path(config.site_dir) / "visualizations")
