"""Guards for the packaging / launch experience of a fresh clone."""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

import jsonify

ROOT = Path(__file__).resolve().parent.parent


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _requirement_names(path: Path) -> set[str]:
    names = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "-")):
            continue
        names.add(re.split(r"[<>=!~\[ ]", line, maxsplit=1)[0].lower())
    return names


def test_requirements_txt_matches_pyproject_dependencies() -> None:
    declared = {
        re.split(r"[<>=!~\[ ]", dep, maxsplit=1)[0].lower()
        for dep in _pyproject()["project"]["dependencies"]
    }

    assert _requirement_names(ROOT / "requirements.txt") == declared


def test_dev_and_build_requirements_include_runtime_requirements() -> None:
    for name in ("requirements-dev.txt", "requirements-build.txt"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "-r requirements.txt" in text


def test_dev_requirements_match_pyproject_dev_extra() -> None:
    extras = _pyproject()["project"]["optional-dependencies"]["dev"]
    declared = {re.split(r"[<>=!~\[ ]", dep, maxsplit=1)[0].lower() for dep in extras}

    assert _requirement_names(ROOT / "requirements-dev.txt") >= declared


def test_version_is_single_sourced() -> None:
    from jsonify.cli import VERSION
    from jsonify.ui.constants import APP_VERSION

    assert _pyproject()["project"]["version"] == jsonify.__version__
    assert APP_VERSION == VERSION == jsonify.__version__

    installer = (ROOT / "installer" / "Jsonify.iss").read_text(encoding="utf-8")
    match = re.search(r'#define MyAppVersion "([^"]+)"', installer)
    assert match and match.group(1) == jsonify.__version__


def test_launch_and_build_files_exist() -> None:
    for name in (
        "run_dev.cmd",
        "run_dev.sh",
        "run_prod.cmd",
        "build_prod.cmd",
        "run_jsonify.cmd",
        "Jsonify.spec",
        "scripts/build.py",
        "installer/Jsonify.iss",
        "README.md",
    ):
        assert (ROOT / name).is_file(), name


def test_spec_builds_gui_and_cli_executables() -> None:
    spec = (ROOT / "Jsonify.spec").read_text(encoding="utf-8")

    assert 'name="Jsonify"' in spec
    assert 'name="jsonify-cli"' in spec
    assert "jsonify.resources" in spec


def test_cli_runs_as_a_module_without_a_display() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "jsonify", "--version"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert result.returncode == 0
    assert jsonify.__version__ in result.stdout


def test_bundled_resources_are_present() -> None:
    from importlib.resources import files

    resources = files("jsonify.resources")

    assert resources.joinpath("d3.min.js").is_file()
    assert resources.joinpath("jsonify.png").is_file()
