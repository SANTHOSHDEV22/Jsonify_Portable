"""
main.py
-------
Entry point for the Notify desktop app.

Run with:
    python main.py

Opens maximized, titled "Notify", with the standard OS window controls
(minimize / maximize-restore / close) that come built in with a Qt
QMainWindow — no extra setup needed for those.
"""
from __future__ import annotations

import sys

# NOTE ON GRAPH VIEW RENDERING: QWebEngineView (used for the Graph View
# tab) depends on Chromium's GPU/compositor stack, which can fail to
# initialize on some Windows machines — VMs, restricted GPU drivers, or
# a QtWebEngine build without a software-rendering fallback compiled in.
# No combination of QTWEBENGINE_CHROMIUM_FLAGS fixes this on every
# machine, and a wrong combination (e.g. --disable-gpu together with
# --use-gl=swiftshader) can make Chromium refuse to start at all — so
# this app does NOT force any GPU flags by default. If the embedded
# graph doesn't render on your machine, use the "Open Graph in Browser"
# button on the Graph View tab instead — it writes the identical graph
# to a temp HTML file and opens it in your default browser, which does
# not depend on QtWebEngine at all.

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Notify")

    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()