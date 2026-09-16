"""
ui/main_window.py
-------------------
The Notify main window. Layout, top to bottom:

    1. Control bar: just the "Load / Parse JSON" button.
    2. Main split view (vertical divider, two side-by-side panes):
         LEFT  -> JSON editor (paste your payload here)
         RIGHT -> Viewer tabs: Tree View | Hierarchy View | Filtered View | Graph View

The Filtered View tab is a level-by-level drill-down rather than a
single "find this key anywhere" filter: after loading JSON, it shows
one dropdown listing the top-level keys. Picking one adds a further
dropdown listing the keys found *inside* that key's value (across every
payload), and so on — each dropdown narrows into the next hierarchical
level. Clicking "Show" renders every payload as a box-drawing tree
(same style as Hierarchy View), pruned to just the chosen chain of
keys, with everything below the last selected key shown in full.

The window opens maximized. Minimize / maximize / close use the
operating system's normal title-bar buttons (Qt provides these for
free on a standard QMainWindow — no custom title bar needed).
"""
from __future__ import annotations

import json
import os
import tempfile
import webbrowser
from typing import Any, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from json_utils import parse_multi_json
from widgets.graph_view import build_graph_html
from widgets.hierarchy_view import build_hierarchy_text, build_path_filtered_hierarchy_text, keys_at_path
from widgets.tree_view import create_tree_widget, populate_tree

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView

    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False

LEVEL_PLACEHOLDER = "-- choose key --"
FILTERED_VIEW_PLACEHOLDER = (
    "Pick a key at each level above (as many as you like), then click "
    "Show to see every payload's data for that chain of keys."
)

DARK_STYLESHEET = """
QMainWindow, QWidget { background-color: #1e1e1e; color: #d4d4d4; }
QWidget#controlBar { background-color: #2d2d30; border-bottom: 1px solid #3f3f46; }
QLabel { color: #d4d4d4; }
QComboBox, QPushButton, QPlainTextEdit, QTreeWidget {
    background-color: #252526;
    color: #d4d4d4;
    border: 1px solid #3f3f46;
    padding: 4px;
}
QPushButton { padding: 6px 14px; border-radius: 3px; }
QPushButton:hover { background-color: #3f3f46; }
QPushButton:pressed { background-color: #007acc; }
QTabWidget::pane { border: 1px solid #3f3f46; }
QTabBar::tab {
    background: #2d2d30; color: #d4d4d4;
    padding: 6px 14px; border: 1px solid #3f3f46; border-bottom: none;
}
QTabBar::tab:selected { background: #1e1e1e; border-bottom: 2px solid #007acc; }
QTreeWidget::item { padding: 2px; }
QHeaderView::section { background-color: #2d2d30; color: #d4d4d4; padding: 4px; border: none; }
"""


class MainWindow(QMainWindow):
    """Notify — JSON payload viewer/editor with tree, hierarchy, filtered, and graph views."""

    def __init__(self) -> None:
        super().__init__()
        self.payload: Any = None
        self._doc_count: int = 1
        self._last_graph_html: Optional[str] = None
        self.level_combos: List[QComboBox] = []

        self.setWindowTitle("Notify")
        self.setStyleSheet(DARK_STYLESHEET)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_control_bar())
        root_layout.addWidget(self._build_split_view(), stretch=1)

    def _build_control_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("controlBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        layout.addStretch(1)

        load_btn = QPushButton("▶ LOAD JSON")
        load_btn.clicked.connect(self._on_load_json)
        layout.addWidget(load_btn)

        return bar

    def _build_split_view(self) -> QSplitter:
        # Qt.Horizontal orientation = two panes side by side, divided by a
        # vertical splitter handle — left pane for editing, right for viewing.
        splitter = QSplitter(Qt.Horizontal)

        splitter.addWidget(self._build_editor_pane())
        splitter.addWidget(self._build_viewer_pane())

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([1, 1])
        return splitter

    def _build_editor_pane(self) -> QWidget:
        pane = QWidget()
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(6, 6, 6, 6)

        layout.addWidget(QLabel("JSON Editor"))

        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText(
            "Paste JSON payloads here, "
            "then click 'Load JSON'…"
        )
        self.editor.setTabStopDistance(20)
        layout.addWidget(self.editor)

        return pane

    def _build_viewer_pane(self) -> QWidget:
        pane = QWidget()
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(6, 6, 6, 6)

        layout.addWidget(QLabel("Viewer"))

        self.view_tabs = QTabWidget()
        self.tree_widget = create_tree_widget()
        self.view_tabs.addTab(self.tree_widget, "Normal View")

        self.hierarchy_view = QPlainTextEdit()
        self.hierarchy_view.setReadOnly(True)
        font = self.hierarchy_view.font()
        font.setFamily("Consolas")
        self.hierarchy_view.setFont(font)
        self.view_tabs.addTab(self.hierarchy_view, "Hierarchy View")

        self.view_tabs.addTab(self._build_filtered_tab(), "Filtered View")
        self.view_tabs.addTab(self._build_graph_tab(), "Graph View")

        layout.addWidget(self.view_tabs)
        return pane

    def _build_filtered_tab(self) -> QWidget:
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(4)

        levels_row = QWidget()
        self.levels_layout = QHBoxLayout(levels_row)
        self.levels_layout.setContentsMargins(8, 8, 8, 0)
        self.levels_layout.setSpacing(6)

        self.levels_layout.addWidget(QLabel("Drill into:"))

        # The Show button is created once and stays put — every level
        # dropdown gets inserted just before it, so it's always the
        # right-most control regardless of how many levels exist.
        self.show_filtered_btn = QPushButton("Show")
        self.show_filtered_btn.clicked.connect(self._on_show_filtered_clicked)
        self.levels_layout.addWidget(self.show_filtered_btn)
        self.levels_layout.addStretch(1)

        container_layout.addWidget(levels_row)

        self.filtered_view = QPlainTextEdit()
        self.filtered_view.setReadOnly(True)
        filtered_font = self.filtered_view.font()
        filtered_font.setFamily("Consolas")
        self.filtered_view.setFont(filtered_font)
        self.filtered_view.setPlainText(FILTERED_VIEW_PLACEHOLDER)
        container_layout.addWidget(self.filtered_view, stretch=1)

        return container

    def _build_graph_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        if HAS_WEBENGINE:
            # Embedded view is the primary path, but QWebEngineView can
            # fail to render on some machines (GPU driver issues, VMs,
            # locked-down environments) even when the module imports
            # fine and the graph HTML itself is correct. Rather than
            # debugging every possible GPU flag combination, this button
            # is always available as a guaranteed-working fallback: it
            # writes the exact same graph HTML to a temp file and opens
            # it in the system's default browser.
            open_row = QWidget()
            open_layout = QHBoxLayout(open_row)
            open_layout.setContentsMargins(8, 6, 8, 0)
            open_layout.addWidget(QLabel("If the graph below doesn't render:"))
            open_btn = QPushButton("Open Graph in Browser")
            open_btn.clicked.connect(self._open_graph_in_browser)
            open_layout.addWidget(open_btn)
            open_layout.addStretch(1)
            layout.addWidget(open_row)

            self.graph_view = QWebEngineView()
            layout.addWidget(self.graph_view, stretch=1)
            return container

        # Fallback when PySide6's QtWebEngine module isn't installed at
        # all: the graph still gets built, it just opens in the browser.
        self.graph_view = None
        note = QLabel(
            "QtWebEngine isn't installed, so the interactive graph opens in\n"
            "your default browser instead of embedding here.\n\n"
            "To embed it in-app instead, run:\n"
            "    pip install PySide6-WebEngine"
        )
        note.setWordWrap(True)
        open_btn = QPushButton("Open Graph in Browser")
        open_btn.clicked.connect(self._open_graph_in_browser)
        layout.addWidget(note)
        layout.addWidget(open_btn)
        layout.addStretch(1)
        return container

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _on_load_json(self) -> None:
        raw = self.editor.toPlainText()
        if not raw.strip():
            QMessageBox.warning(self, "Nothing to load", "Paste a JSON payload into the editor first.")
            return

        try:
            self.payload, self._doc_count = parse_multi_json(raw)
        except json.JSONDecodeError as exc:
            QMessageBox.critical(self, "Invalid JSON", f"Could not parse JSON:\n\n{exc}")
            return

        self._refresh_all_views()

    def _refresh_all_views(self) -> None:
        # --- tree view ---
        populate_tree(self.tree_widget, self.payload)

        # --- hierarchy view ---
        self.hierarchy_view.setPlainText(build_hierarchy_text(self.payload))

        # --- filtered view: reset to just the first drill-down level ---
        self._reset_filter_levels()

        # --- graph view ---
        html = build_graph_html(self.payload)
        self._last_graph_html = html
        if HAS_WEBENGINE and self.graph_view is not None:
            self.graph_view.setHtml(html)

    # -- Filtered View: level dropdowns --------------------------------
    def _reset_filter_levels(self) -> None:
        """Clear every level dropdown and start over with just level 1."""
        for combo in self.level_combos:
            self.levels_layout.removeWidget(combo)
            combo.deleteLater()
        self.level_combos = []
        self.filtered_view.setPlainText(FILTERED_VIEW_PLACEHOLDER)

        if self.payload is None:
            return

        first_level_keys = keys_at_path(self.payload, [])
        if first_level_keys:
            self._append_level_combo(first_level_keys)

    def _append_level_combo(self, keys: List[str]) -> None:
        combo = QComboBox()
        combo.addItem(LEVEL_PLACEHOLDER)
        combo.addItems(keys)
        combo.currentIndexChanged.connect(lambda _index, c=combo: self._on_level_changed(c))
        # Always insert right before the Show button, so button stays
        # the right-most control no matter how many levels exist.
        self.levels_layout.insertWidget(self.levels_layout.indexOf(self.show_filtered_btn), combo)
        self.level_combos.append(combo)

    def _current_path(self) -> List[str]:
        """The key chosen at each level so far, stopping at the first
        unset (placeholder) level — deeper combos never outrun an
        unset shallower one, since changing a combo removes everything
        after it (see `_on_level_changed`)."""
        path: List[str] = []
        for combo in self.level_combos:
            text = combo.currentText()
            if not text or text == LEVEL_PLACEHOLDER:
                break
            path.append(text)
        return path

    def _on_level_changed(self, combo: QComboBox) -> None:
        if combo not in self.level_combos:
            return  # stale signal from a combo already being torn down
        index = self.level_combos.index(combo)

        # A change at this level invalidates every level after it —
        # remove them; they'll be rebuilt below if still applicable.
        for stale in self.level_combos[index + 1 :]:
            self.levels_layout.removeWidget(stale)
            stale.deleteLater()
        self.level_combos = self.level_combos[: index + 1]

        path = self._current_path()
        if len(path) != index + 1:
            return  # this level was reset to the placeholder

        next_keys = keys_at_path(self.payload, path)
        if next_keys:
            self._append_level_combo(next_keys)

    def _on_show_filtered_clicked(self) -> None:
        if self.payload is None:
            QMessageBox.information(self, "No JSON loaded", "Paste and load a JSON payload first.")
            return

        path = self._current_path()
        self.filtered_view.setPlainText(build_path_filtered_hierarchy_text(self.payload, path))

    def _open_graph_in_browser(self) -> None:
        if not self._last_graph_html:
            QMessageBox.information(self, "No graph yet", "Load a JSON payload first.")
            return
        # Reuse the same fixed filename across every click/session instead
        # of creating a fresh randomly-named temp file each time — the
        # browser just reloads this one file with whatever the current
        # graph is, so nothing accumulates in the system temp folder no
        # matter how many times this button is clicked.
        path = os.path.join(tempfile.gettempdir(), "notify_graph_view.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(self._last_graph_html)
        webbrowser.open(f"file://{path}")