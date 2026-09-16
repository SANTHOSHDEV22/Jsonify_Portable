"""Main application window for Jsonify."""

from __future__ import annotations

import json

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
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

from jsonify.core.models import JSONValue
from jsonify.services import GraphService, JsonService
from jsonify.ui.constants import (
    DARK_STYLESHEET,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    EDITOR_PLACEHOLDER,
    FILTERED_VIEW_PLACEHOLDER,
    LEVEL_PLACEHOLDER,
    MESSAGE_INVALID_JSON_TITLE,
    MESSAGE_NO_GRAPH,
    MESSAGE_NO_GRAPH_TITLE,
    MESSAGE_NO_JSON,
    MESSAGE_NO_JSON_TITLE,
    MESSAGE_NOTHING_TO_LOAD,
    MESSAGE_NOTHING_TO_LOAD_TITLE,
    MONOSPACE_FONT,
    WINDOW_TITLE,
)
from jsonify.ui.widgets.graph_view import build_graph_html
from jsonify.ui.widgets.hierarchy_view import (
    build_hierarchy_text,
    build_path_filtered_hierarchy_text,
    keys_at_path,
)
from jsonify.ui.widgets.tree_view import (
    create_tree_widget,
    populate_tree,
)

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView

    HAS_WEBENGINE = True

except ImportError:
    QWebEngineView = None
    HAS_WEBENGINE = False


class MainWindow(QMainWindow):
    """Main window for viewing and exploring JSON payloads."""

    def __init__(
        self,
        json_service: JsonService | None = None,
        graph_service: GraphService | None = None,
    ) -> None:
        super().__init__()

        self._json_service = json_service or JsonService()
        self._graph_service = graph_service or GraphService()

        self._payload: JSONValue | None = None
        self._document_count = 0
        self._last_graph_html: str | None = None

        self._level_combos: list[QComboBox] = []

        self._setup_window()
        self._setup_ui()

    # -----------------------------------------------------------------
    # Window setup
    # -----------------------------------------------------------------

    def _setup_window(self) -> None:
        """Configure the main application window."""

        self.setWindowTitle(WINDOW_TITLE)

        self.resize(
            DEFAULT_WINDOW_WIDTH,
            DEFAULT_WINDOW_HEIGHT,
        )

        self.setStyleSheet(DARK_STYLESHEET)

    # -----------------------------------------------------------------
    # Main UI
    # -----------------------------------------------------------------

    def _setup_ui(self) -> None:
        """Build the main user interface."""

        central_widget = QWidget()

        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)

        root_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        root_layout.setSpacing(0)

        root_layout.addWidget(self._create_control_bar())

        root_layout.addWidget(
            self._create_split_view(),
            stretch=1,
        )

    # -----------------------------------------------------------------
    # Control bar
    # -----------------------------------------------------------------

    def _create_control_bar(self) -> QWidget:
        """Create the application control bar."""

        control_bar = QWidget()

        control_bar.setObjectName("controlBar")

        layout = QHBoxLayout(control_bar)

        layout.setContentsMargins(
            10,
            8,
            10,
            8,
        )

        layout.setSpacing(8)

        layout.addStretch(1)

        self._load_button = QPushButton("▶ LOAD JSON")

        self._load_button.clicked.connect(self._load_json)

        layout.addWidget(self._load_button)

        return control_bar

    # -----------------------------------------------------------------
    # Split view
    # -----------------------------------------------------------------

    def _create_split_view(self) -> QSplitter:
        """Create the editor/viewer split layout."""

        splitter = QSplitter(Qt.Orientation.Horizontal)

        splitter.addWidget(self._create_editor_panel())

        splitter.addWidget(self._create_viewer_panel())

        splitter.setStretchFactor(
            0,
            1,
        )

        splitter.setStretchFactor(
            1,
            1,
        )

        splitter.setSizes([700, 700])

        return splitter

    # -----------------------------------------------------------------
    # Editor
    # -----------------------------------------------------------------

    def _create_editor_panel(self) -> QWidget:
        """Create the JSON editor panel."""

        panel = QWidget()

        layout = QVBoxLayout(panel)

        layout.setContentsMargins(
            6,
            6,
            6,
            6,
        )

        layout.addWidget(QLabel("JSON Editor"))

        self._editor = QPlainTextEdit()

        self._editor.setPlaceholderText(EDITOR_PLACEHOLDER)

        self._editor.setTabStopDistance(20)

        layout.addWidget(self._editor)

        return panel

    # -----------------------------------------------------------------
    # Viewer
    # -----------------------------------------------------------------

    def _create_viewer_panel(self) -> QWidget:
        """Create the JSON visualization panel."""

        panel = QWidget()

        layout = QVBoxLayout(panel)

        layout.setContentsMargins(
            6,
            6,
            6,
            6,
        )

        layout.addWidget(QLabel("Viewer"))

        self._view_tabs = QTabWidget()

        self._create_tree_tab()
        self._create_hierarchy_tab()

        self._view_tabs.addTab(
            self._create_filtered_tab(),
            "Filtered View",
        )

        self._view_tabs.addTab(
            self._create_graph_tab(),
            "Graph View",
        )

        layout.addWidget(self._view_tabs)

        return panel

    # -----------------------------------------------------------------
    # Tree tab
    # -----------------------------------------------------------------

    def _create_tree_tab(self) -> None:
        """Create the normal JSON tree view."""

        self._tree_widget = create_tree_widget()

        self._view_tabs.addTab(
            self._tree_widget,
            "Normal View",
        )

    # -----------------------------------------------------------------
    # Hierarchy tab
    # -----------------------------------------------------------------

    def _create_hierarchy_tab(self) -> None:
        """Create the text hierarchy view."""

        self._hierarchy_view = QPlainTextEdit()

        self._hierarchy_view.setReadOnly(True)

        font = self._hierarchy_view.font()

        font.setFamily(MONOSPACE_FONT)

        self._hierarchy_view.setFont(font)

        self._view_tabs.addTab(
            self._hierarchy_view,
            "Hierarchy View",
        )

    # -----------------------------------------------------------------
    # Filtered tab
    # -----------------------------------------------------------------

    def _create_filtered_tab(self) -> QWidget:
        """Create hierarchical filtered JSON view."""

        container = QWidget()

        container_layout = QVBoxLayout(container)

        container_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        container_layout.setSpacing(4)

        levels_row = QWidget()

        self._levels_layout = QHBoxLayout(levels_row)

        self._levels_layout.setContentsMargins(
            8,
            8,
            8,
            0,
        )

        self._levels_layout.setSpacing(6)

        self._levels_layout.addWidget(QLabel("Drill into:"))

        self._show_filtered_button = QPushButton("Show")

        self._show_filtered_button.clicked.connect(self._show_filtered)

        self._levels_layout.addWidget(self._show_filtered_button)

        self._levels_layout.addStretch(1)

        container_layout.addWidget(levels_row)

        self._filtered_view = QPlainTextEdit()

        self._filtered_view.setReadOnly(True)

        font = self._filtered_view.font()

        font.setFamily(MONOSPACE_FONT)

        self._filtered_view.setFont(font)

        self._filtered_view.setPlainText(FILTERED_VIEW_PLACEHOLDER)

        container_layout.addWidget(
            self._filtered_view,
            stretch=1,
        )

        return container

    # -----------------------------------------------------------------
    # Graph tab
    # -----------------------------------------------------------------

    def _create_graph_tab(self) -> QWidget:
        """Create the interactive graph visualization tab."""

        container = QWidget()

        layout = QVBoxLayout(container)

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.setSpacing(4)

        if HAS_WEBENGINE:
            self._create_embedded_graph_view(layout)

        else:
            self._create_graph_fallback(layout)

        return container

    def _create_embedded_graph_view(
        self,
        layout: QVBoxLayout,
    ) -> None:
        """Create embedded WebEngine graph view."""

        controls = QWidget()

        controls_layout = QHBoxLayout(controls)

        controls_layout.setContentsMargins(
            8,
            6,
            8,
            0,
        )

        controls_layout.addWidget(QLabel("If the graph does not render:"))

        open_button = QPushButton("Open Graph in Browser")

        open_button.clicked.connect(self._open_graph_in_browser)

        controls_layout.addWidget(open_button)

        controls_layout.addStretch(1)

        layout.addWidget(controls)

        self._graph_view = QWebEngineView()

        layout.addWidget(
            self._graph_view,
            stretch=1,
        )

    def _create_graph_fallback(
        self,
        layout: QVBoxLayout,
    ) -> None:
        """Create fallback UI when Qt WebEngine is unavailable."""

        self._graph_view = None

        message = QLabel(
            "QtWebEngine is not installed.\n\n"
            "The interactive graph can still be opened "
            "in your default browser."
        )

        message.setWordWrap(True)

        layout.addWidget(message)

        open_button = QPushButton("Open Graph in Browser")

        open_button.clicked.connect(self._open_graph_in_browser)

        layout.addWidget(open_button)

        layout.addStretch(1)

    # -----------------------------------------------------------------
    # JSON loading
    # -----------------------------------------------------------------

    def _load_json(self) -> None:
        """Parse editor content and refresh all views."""

        raw_text = self._editor.toPlainText().strip()

        if not raw_text:
            QMessageBox.warning(
                self,
                MESSAGE_NOTHING_TO_LOAD_TITLE,
                MESSAGE_NOTHING_TO_LOAD,
            )

            return

        try:
            (
                self._payload,
                self._document_count,
            ) = self._json_service.parse_multiple(raw_text)

        except json.JSONDecodeError as exc:
            QMessageBox.critical(
                self,
                MESSAGE_INVALID_JSON_TITLE,
                f"Could not parse JSON:\n\n{exc}",
            )

            return

        self._refresh_all_views()

    # -----------------------------------------------------------------
    # Refresh
    # -----------------------------------------------------------------

    def _refresh_all_views(self) -> None:
        """Refresh every visualization using the current payload."""

        if self._payload is None:
            return

        self._refresh_tree_view()
        self._refresh_hierarchy_view()
        self._reset_filter_levels()
        self._refresh_graph_view()

    def _refresh_tree_view(self) -> None:
        """Refresh normal tree visualization."""

        populate_tree(
            self._tree_widget,
            self._payload,
        )

    def _refresh_hierarchy_view(self) -> None:
        """Refresh hierarchy text visualization."""

        hierarchy = build_hierarchy_text(self._payload)

        self._hierarchy_view.setPlainText(hierarchy)

    def _refresh_graph_view(self) -> None:
        """Generate and display the graph visualization."""

        if self._payload is None:
            return

        html = build_graph_html(self._payload)

        self._last_graph_html = html

        if HAS_WEBENGINE and self._graph_view is not None:
            self._graph_view.setHtml(html)

    # -----------------------------------------------------------------
    # Filter levels
    # -----------------------------------------------------------------

    def _reset_filter_levels(self) -> None:
        """Reset filtered-view dropdowns."""

        for combo in self._level_combos:
            self._levels_layout.removeWidget(combo)

            combo.deleteLater()

        self._level_combos.clear()

        self._filtered_view.setPlainText(FILTERED_VIEW_PLACEHOLDER)

        if self._payload is None:
            return

        first_level_keys = keys_at_path(
            self._payload,
            [],
        )

        if first_level_keys:
            self._add_level_combo(first_level_keys)

    def _add_level_combo(
        self,
        keys: list[str],
    ) -> None:
        """Add another hierarchy-level selector."""

        combo = QComboBox()

        combo.addItem(LEVEL_PLACEHOLDER)

        combo.addItems(keys)

        combo.currentIndexChanged.connect(
            lambda _index, current=combo: self._on_level_changed(current)
        )

        button_index = self._levels_layout.indexOf(self._show_filtered_button)

        self._levels_layout.insertWidget(
            button_index,
            combo,
        )

        self._level_combos.append(combo)

    def _current_filter_path(
        self,
    ) -> list[str]:
        """Return currently selected hierarchy path."""

        path: list[str] = []

        for combo in self._level_combos:
            selected_key = combo.currentText()

            if not selected_key or selected_key == LEVEL_PLACEHOLDER:
                break

            path.append(selected_key)

        return path

    def _on_level_changed(
        self,
        combo: QComboBox,
    ) -> None:
        """Handle changes to a hierarchy-level selector."""

        if combo not in self._level_combos:
            return

        index = self._level_combos.index(combo)

        stale_combos = self._level_combos[index + 1 :]

        for stale_combo in stale_combos:
            self._levels_layout.removeWidget(stale_combo)

            stale_combo.deleteLater()

        self._level_combos = self._level_combos[: index + 1]

        path = self._current_filter_path()

        if len(path) != index + 1:
            return

        if self._payload is None:
            return

        next_keys = keys_at_path(
            self._payload,
            path,
        )

        if next_keys:
            self._add_level_combo(next_keys)

    def _show_filtered(self) -> None:
        """Render JSON matching the selected hierarchy path."""

        if self._payload is None:
            QMessageBox.information(
                self,
                MESSAGE_NO_JSON_TITLE,
                MESSAGE_NO_JSON,
            )

            return

        path = self._current_filter_path()

        result = build_path_filtered_hierarchy_text(
            self._payload,
            path,
        )

        self._filtered_view.setPlainText(result)

    # -----------------------------------------------------------------
    # Graph browser fallback
    # -----------------------------------------------------------------

    def _open_graph_in_browser(self) -> None:
        """Open the generated graph using the system browser."""

        if not self._last_graph_html:
            QMessageBox.information(
                self,
                MESSAGE_NO_GRAPH_TITLE,
                MESSAGE_NO_GRAPH,
            )

            return

        graph_path = self._graph_service.save_html(self._last_graph_html)

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(graph_path)))
