"""Build Jsonify for production.

    python scripts/build.py                 PyInstaller one-folder build -> dist/Jsonify/
    python scripts/build.py --clean         remove build/ and dist/ first
    python scripts/build.py --portable      also write dist/Jsonify-<version>-portable.zip
    python scripts/build.py --installer     also compile installer/Jsonify.iss (Inno Setup)

The build produces two executables in one folder:
    Jsonify.exe        the desktop app (no console window)
    jsonify-cli.exe    the command-line interface (console)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
APP_DIR = DIST / "Jsonify"
IS_WINDOWS = sys.platform.startswith("win")
EXE_NAME = "Jsonify.exe" if IS_WINDOWS else "Jsonify"

_INNO_CANDIDATES = (
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
)


def read_version() -> str:
    sys.path.insert(0, str(ROOT / "src"))
    from jsonify import __version__

    return __version__


def run(command: list[str]) -> None:
    print("\n>", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def build_app(clean: bool) -> None:
    if clean:
        for folder in (ROOT / "build", DIST):
            if folder.exists():
                print(f"Removing {folder}")
                shutil.rmtree(folder)

    command = [sys.executable, "-m", "PyInstaller", "Jsonify.spec", "--noconfirm"]
    if clean:
        command.append("--clean")
    run(command)

    executable = APP_DIR / EXE_NAME
    if not executable.is_file():
        raise SystemExit(f"Build finished but {executable} was not created.")

    print(f"\nBuilt: {executable}")


def make_portable(version: str) -> Path:
    """Zip the build together with a ``portable.flag`` marker file.

    The marker makes the app keep all of its data in a ``data`` folder next to
    the executable, so the extracted folder can be run from any location.
    """

    staging = DIST / "Jsonify-portable" / "Jsonify"
    if staging.parent.exists():
        shutil.rmtree(staging.parent)

    shutil.copytree(APP_DIR, staging)
    (staging / "portable.flag").write_text(
        "Presence of this file makes Jsonify store its data in the 'data' folder next to it.\n",
        encoding="utf-8",
    )

    archive = shutil.make_archive(
        str(DIST / f"Jsonify-{version}-portable"), "zip", root_dir=staging.parent
    )
    shutil.rmtree(staging.parent)
    print(f"\nPortable package: {archive}")
    return Path(archive)


def make_installer() -> None:
    compiler = shutil.which("ISCC") or next((p for p in _INNO_CANDIDATES if Path(p).is_file()), None)
    if compiler is None:
        raise SystemExit(
            "Inno Setup (ISCC.exe) was not found. Install it from https://jrsoftware.org/isinfo.php "
            "or add it to PATH, then re-run with --installer."
        )

    run([compiler, str(ROOT / "installer" / "Jsonify.iss")])
    print(f"\nInstaller written to: {ROOT / 'installer-output'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Jsonify for production.")
    parser.add_argument("--clean", action="store_true", help="remove build/ and dist/ first")
    parser.add_argument("--portable", action="store_true", help="also create a portable .zip")
    parser.add_argument("--installer", action="store_true", help="also compile the Inno Setup installer")
    args = parser.parse_args()

    version = read_version()
    print(f"Building Jsonify {version}")

    try:
        build_app(args.clean)
        if args.portable:
            make_portable(version)
        if args.installer:
            make_installer()
    except subprocess.CalledProcessError as error:
        print(f"\nBuild step failed (exit code {error.returncode}).", file=sys.stderr)
        return error.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
