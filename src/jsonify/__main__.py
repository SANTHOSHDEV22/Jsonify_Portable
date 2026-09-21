"""Application entry point for Jsonify.

``jsonify`` / ``python -m jsonify`` opens the desktop app.
``jsonify <command> ...`` runs the command-line interface (see ``jsonify --help``).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    """Dispatch to the CLI or start the desktop application."""

    args = list(sys.argv[1:] if argv is None else argv)

    if "--portable" in args:
        args.remove("--portable")
        os.environ["JSONIFY_PORTABLE"] = "1"

    # Imported lazily so CLI use never requires Qt (or a display).
    from jsonify.cli import COMMANDS
    from jsonify.cli import main as cli_main

    if args and (args[0] in COMMANDS or args[0] in ("-h", "--help", "--version")):
        return cli_main(args)

    return run_gui(args)


def run_gui(paths: list[str] | None = None) -> int:
    """Start the Jsonify desktop application, optionally opening files."""

    from importlib.resources import files

    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from jsonify.ui.constants import APP_NAME, APP_VERSION
    from jsonify.ui.main_window import MainWindow

    app = QApplication(sys.argv[:1])

    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Jsonify")

    icon_path = files("jsonify.resources").joinpath("jsonify.png")
    app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()

    existing = [Path(p) for p in (paths or []) if Path(p).is_file()]
    if existing:
        window.open_paths(existing)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
