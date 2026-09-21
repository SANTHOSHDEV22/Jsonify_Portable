"""Where Jsonify keeps its local data — including portable mode.

Portable mode keeps every setting, history file and recovery snapshot in a
``data`` folder next to the application instead of the user profile, so the
whole app can live on a USB stick or a shared drive without installation.

Portable mode is enabled when any of these is true:
    - the ``JSONIFY_PORTABLE`` environment variable is set (``--portable`` sets it),
    - a file named ``portable.flag`` sits next to the executable / project root.

``JSONIFY_DATA_DIR`` overrides the location entirely.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PORTABLE_ENV = "JSONIFY_PORTABLE"
DATA_DIR_ENV = "JSONIFY_DATA_DIR"
PORTABLE_FLAG_FILE = "portable.flag"


def app_root() -> Path:
    """Folder containing the executable (frozen) or the project root (source)."""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    # src/jsonify/core/app_paths.py -> project root is three levels up.
    return Path(__file__).resolve().parents[3]


def is_portable() -> bool:
    """Return whether portable mode is active."""

    if os.environ.get(PORTABLE_ENV):
        return True

    return (app_root() / PORTABLE_FLAG_FILE).is_file()


def data_dir() -> Path:
    """Return the directory for Jsonify's local data files (not created here)."""

    override = os.environ.get(DATA_DIR_ENV)
    if override:
        return Path(override).expanduser()

    if is_portable():
        return app_root() / "data"

    return Path.home() / ".jsonify"
