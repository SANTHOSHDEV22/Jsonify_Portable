"""Application entry point for Jsonify."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from jsonify.ui.constants import APP_NAME, APP_VERSION
from jsonify.ui.main_window import MainWindow


def main() -> int:
    """Start the Jsonify desktop application."""

    app = QApplication(sys.argv)

    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Jsonify")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())