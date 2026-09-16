"""Main application window for Jsonify."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
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

from jsonify.core.licensing import Feature
from jsonify.core.models import JSONValue
from jsonify.core.session import JsonifySession

from jsonify.services import (
    JsonService,
)
from jsonify.services.large_json_service import LargeJsonService
from jsonify.services.license_factory import create_license_service
from jsonify.services.license_service import LicenseError
from jsonify.services.license_storage import LicenseStorage
from jsonify.services.session_service import SessionError, SessionService

from jsonify.ui.constants import (
    DARK_STYLESHEET,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    EDITOR_PLACEHOLDER,
    FILTERED_VIEW_PLACEHOLDER,
    LEVEL_PLACEHOLDER,
    MESSAGE_INVALID_JSON_TITLE,
    MESSAGE_NO_JSON,
    MESSAGE_NO_JSON_TITLE,
    MESSAGE_NOTHING_TO_LOAD,
    MESSAGE_NOTHING_TO_LOAD_TITLE,
    MONOSPACE_FONT,
    WINDOW_TITLE,
)

from jsonify.ui.widgets.advanced_graph_view import AdvancedGraphView
from jsonify.ui.widgets.api_view import ApiView
from jsonify.ui.widgets.diff_view import DiffView
from jsonify.ui.widgets.export_view import ExportView
from jsonify.ui.widgets.hierarchy_view import (
    build_hierarchy_text,
    build_path_filtered_hierarchy_text,
    keys_at_path,
)
from jsonify.ui.widgets.jsonpath_view import JsonPathView
from jsonify.ui.widgets.lazy_tree_view import LazyJsonTreeView
from jsonify.ui.widgets.license_view import LicenseView
from jsonify.ui.widgets.masking_view import MaskingView
from jsonify.ui.widgets.schema_view import SchemaView


class MainWindow(QMainWindow):
    """Main window for viewing and exploring JSON payloads."""

    def __init__(
        self,
        json_service: JsonService | None = None,
    ) -> None:
        """Initialize Jsonify."""

        super().__init__()

        # -------------------------------------------------------------
        # Core services
        # -------------------------------------------------------------

        self._json_service = (
            json_service
            if json_service is not None
            else JsonService()
        )

        self._large_json_service = LargeJsonService()

        self._session_service = SessionService()

        self._license_service = create_license_service()

        self._license_storage = LicenseStorage()

        # -------------------------------------------------------------
        # Current JSON state
        # -------------------------------------------------------------

        self._payload: JSONValue | None = None

        # Important:
        # JSON "null" becomes Python None.
        # Therefore _payload is None cannot be used to determine whether
        # JSON has actually been loaded.
        self._has_payload = False

        self._document_count = 0

        # -------------------------------------------------------------
        # Saved-session state
        # -------------------------------------------------------------

        self._current_session: JsonifySession | None = None

        self._current_session_path: Path | None = None

        # -------------------------------------------------------------
        # Filter state
        # -------------------------------------------------------------

        self._level_combos: list[QComboBox] = []

        # -------------------------------------------------------------
        # Setup
        # -------------------------------------------------------------

        self._setup_window()

        self._load_saved_license()

        self._setup_ui()

        self._setup_menu()

        self._setup_licensed_features()

        self._refresh_license_access()

    # =================================================================
    # Window setup
    # =================================================================

    def _setup_window(self) -> None:
        """Configure the main application window."""

        self.setWindowTitle(WINDOW_TITLE)

        self.resize(
            DEFAULT_WINDOW_WIDTH,
            DEFAULT_WINDOW_HEIGHT,
        )

        self.setStyleSheet(
            DARK_STYLESHEET
        )

        self.statusBar().showMessage(
            "Ready"
        )

    # =================================================================
    # Main UI
    # =================================================================

    def _setup_ui(self) -> None:
        """Build the main user interface."""

        central_widget = QWidget()

        self.setCentralWidget(
            central_widget
        )

        root_layout = QVBoxLayout(
            central_widget
        )

        root_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        root_layout.setSpacing(
            0
        )

        root_layout.addWidget(
            self._create_control_bar()
        )

        root_layout.addWidget(
            self._create_split_view(),
            stretch=1,
        )

    # =================================================================
    # Menu
    # =================================================================

    def _setup_menu(self) -> None:
        """Create the application menu."""

        menu_bar = self.menuBar()

        # -------------------------------------------------------------
        # File menu
        # -------------------------------------------------------------

        file_menu = menu_bar.addMenu(
            "&File"
        )

        load_action = QAction(
            "Load JSON",
            self,
        )

        load_action.setShortcut(
            QKeySequence.StandardKey.Open
        )

        load_action.triggered.connect(
            self._load_json
        )

        file_menu.addAction(
            load_action
        )

        file_menu.addSeparator()

        self._open_session_action = QAction(
            "Open Session...",
            self,
        )

        self._open_session_action.setShortcut(
            QKeySequence(
                "Ctrl+Shift+O"
            )
        )

        self._open_session_action.triggered.connect(
            self._open_session
        )

        file_menu.addAction(
            self._open_session_action
        )

        self._save_session_action = QAction(
            "Save Session",
            self,
        )

        self._save_session_action.setShortcut(
            QKeySequence(
                "Ctrl+Shift+S"
            )
        )

        self._save_session_action.triggered.connect(
            self._save_session
        )

        file_menu.addAction(
            self._save_session_action
        )

        self._save_session_as_action = QAction(
            "Save Session As...",
            self,
        )

        self._save_session_as_action.triggered.connect(
            self._save_session_as
        )

        file_menu.addAction(
            self._save_session_as_action
        )

        file_menu.addSeparator()

        exit_action = QAction(
            "Exit",
            self,
        )

        exit_action.setShortcut(
            QKeySequence.StandardKey.Quit
        )

        exit_action.triggered.connect(
            self.close
        )

        file_menu.addAction(
            exit_action
        )

        # -------------------------------------------------------------
        # License menu
        # -------------------------------------------------------------

        license_menu = menu_bar.addMenu(
            "&License"
        )

        manage_license_action = QAction(
            "Manage License",
            self,
        )

        manage_license_action.triggered.connect(
            self._show_license_tab
        )

        license_menu.addAction(
            manage_license_action
        )

    # =================================================================
    # Control bar
    # =================================================================

    def _create_control_bar(
        self,
    ) -> QWidget:
        """Create the application control bar."""

        control_bar = QWidget()

        control_bar.setObjectName(
            "controlBar"
        )

        layout = QHBoxLayout(
            control_bar
        )

        layout.setContentsMargins(
            10,
            8,
            10,
            8,
        )

        layout.setSpacing(
            8
        )

        self._payload_status = QLabel(
            "No JSON loaded"
        )

        layout.addWidget(
            self._payload_status
        )

        layout.addStretch(
            1
        )

        self._load_button = QPushButton(
            "▶ LOAD JSON"
        )

        self._load_button.clicked.connect(
            self._load_json
        )

        layout.addWidget(
            self._load_button
        )

        return control_bar

    # =================================================================
    # Split view
    # =================================================================

    def _create_split_view(
        self,
    ) -> QSplitter:
        """Create editor/viewer split layout."""

        splitter = QSplitter(
            Qt.Orientation.Horizontal
        )

        splitter.addWidget(
            self._create_editor_panel()
        )

        splitter.addWidget(
            self._create_viewer_panel()
        )

        splitter.setStretchFactor(
            0,
            1,
        )

        splitter.setStretchFactor(
            1,
            1,
        )

        splitter.setSizes(
            [
                650,
                850,
            ]
        )

        return splitter

    # =================================================================
    # Editor
    # =================================================================

    def _create_editor_panel(
        self,
    ) -> QWidget:
        """Create JSON editor panel."""

        panel = QWidget()

        layout = QVBoxLayout(
            panel
        )

        layout.setContentsMargins(
            6,
            6,
            6,
            6,
        )

        layout.addWidget(
            QLabel("JSON Editor")
        )

        self._editor = QPlainTextEdit()

        self._editor.setPlaceholderText(
            EDITOR_PLACEHOLDER
        )

        self._editor.setTabStopDistance(
            20
        )

        font = self._editor.font()

        font.setFamily(
            MONOSPACE_FONT
        )

        self._editor.setFont(
            font
        )

        layout.addWidget(
            self._editor
        )

        return panel

    # =================================================================
    # Viewer
    # =================================================================

    def _create_viewer_panel(
        self,
    ) -> QWidget:
        """Create visualization panel."""

        panel = QWidget()

        layout = QVBoxLayout(
            panel
        )

        layout.setContentsMargins(
            6,
            6,
            6,
            6,
        )

        layout.addWidget(
            QLabel("Viewer")
        )

        self._view_tabs = QTabWidget()

        # -------------------------------------------------------------
        # Core/free views
        # -------------------------------------------------------------

        self._create_tree_tab()

        self._create_hierarchy_tab()

        self._filtered_view_container = (
            self._create_filtered_tab()
        )

        self._view_tabs.addTab(
            self._filtered_view_container,
            "Filtered View",
        )

        # -------------------------------------------------------------
        # Advanced graph
        # -------------------------------------------------------------

        self._graph_view = (
            AdvancedGraphView()
        )

        self._view_tabs.addTab(
            self._graph_view,
            "Graph",
        )

        # -------------------------------------------------------------
        # JSON Diff
        # -------------------------------------------------------------

        self._diff_view = DiffView()

        self._view_tabs.addTab(
            self._diff_view,
            "JSON Diff",
        )

        # -------------------------------------------------------------
        # JSONPath
        # -------------------------------------------------------------

        self._jsonpath_view = (
            JsonPathView()
        )

        self._view_tabs.addTab(
            self._jsonpath_view,
            "JSONPath",
        )

        # -------------------------------------------------------------
        # Schema Validation
        # -------------------------------------------------------------

        self._schema_view = (
            SchemaView()
        )

        self._view_tabs.addTab(
            self._schema_view,
            "Schema",
        )

        # -------------------------------------------------------------
        # Sensitive Data Masking
        # -------------------------------------------------------------

        self._masking_view = (
            MaskingView()
        )

        self._view_tabs.addTab(
            self._masking_view,
            "Data Masking",
        )

        # -------------------------------------------------------------
        # API Response Viewer
        # -------------------------------------------------------------

        self._api_view = ApiView()

        self._view_tabs.addTab(
            self._api_view,
            "API Viewer",
        )

        # -------------------------------------------------------------
        # Export
        # -------------------------------------------------------------

        self._export_view = (
            ExportView()
        )

        self._view_tabs.addTab(
            self._export_view,
            "Export",
        )

        # -------------------------------------------------------------
        # License
        # -------------------------------------------------------------

        self._license_view = LicenseView(
            self._license_service
        )

        self._license_view.license_changed.connect(
            self._refresh_license_access
        )

        self._view_tabs.addTab(
            self._license_view,
            "License",
        )

        layout.addWidget(
            self._view_tabs
        )

        return panel

    # =================================================================
    # Tree View
    # =================================================================

    def _create_tree_tab(
        self,
    ) -> None:
        """Create optimized lazy JSON tree."""

        self._tree_view = (
            LazyJsonTreeView()
        )

        self._view_tabs.addTab(
            self._tree_view,
            "Normal View",
        )

    # =================================================================
    # Hierarchy View
    # =================================================================

    def _create_hierarchy_tab(
        self,
    ) -> None:
        """Create text hierarchy view."""

        self._hierarchy_view = (
            QPlainTextEdit()
        )

        self._hierarchy_view.setReadOnly(
            True
        )

        font = (
            self._hierarchy_view.font()
        )

        font.setFamily(
            MONOSPACE_FONT
        )

        self._hierarchy_view.setFont(
            font
        )

        self._view_tabs.addTab(
            self._hierarchy_view,
            "Hierarchy View",
        )

    # =================================================================
    # Filtered View
    # =================================================================

    def _create_filtered_tab(
        self,
    ) -> QWidget:
        """Create hierarchical filtered JSON view."""

        container = QWidget()

        container_layout = QVBoxLayout(
            container
        )

        container_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        container_layout.setSpacing(
            4
        )

        levels_row = QWidget()

        self._levels_layout = QHBoxLayout(
            levels_row
        )

        self._levels_layout.setContentsMargins(
            8,
            8,
            8,
            0,
        )

        self._levels_layout.setSpacing(
            6
        )

        self._levels_layout.addWidget(
            QLabel("Drill into:")
        )

        self._show_filtered_button = (
            QPushButton("Show")
        )

        self._show_filtered_button.clicked.connect(
            self._show_filtered
        )

        self._levels_layout.addWidget(
            self._show_filtered_button
        )

        self._levels_layout.addStretch(
            1
        )

        container_layout.addWidget(
            levels_row
        )

        self._filtered_view = (
            QPlainTextEdit()
        )

        self._filtered_view.setReadOnly(
            True
        )

        font = (
            self._filtered_view.font()
        )

        font.setFamily(
            MONOSPACE_FONT
        )

        self._filtered_view.setFont(
            font
        )

        self._filtered_view.setPlainText(
            FILTERED_VIEW_PLACEHOLDER
        )

        container_layout.addWidget(
            self._filtered_view,
            stretch=1,
        )

        return container

    # =================================================================
    # JSON Loading
    # =================================================================

    def _load_json(self) -> None:
        """Parse editor content and refresh all views."""

        raw_text = (
            self._editor
            .toPlainText()
            .strip()
        )

        if not raw_text:
            QMessageBox.warning(
                self,
                MESSAGE_NOTHING_TO_LOAD_TITLE,
                MESSAGE_NOTHING_TO_LOAD,
            )

            return

        try:
            payload, document_count = (
                self._json_service
                .parse_multiple(
                    raw_text
                )
            )

        except json.JSONDecodeError as exc:
            QMessageBox.critical(
                self,
                MESSAGE_INVALID_JSON_TITLE,
                (
                    "Could not parse JSON:"
                    f"\n\n{exc}"
                ),
            )

            return

        # Only update state after successful parsing.

        self._payload = payload

        self._has_payload = True

        self._document_count = (
            document_count
        )

        # Ordinary JSON load is no longer associated
        # with the previously opened session.

        self._current_session = None

        self._current_session_path = None

        self._refresh_all_views()

    # =================================================================
    # Refresh all views
    # =================================================================

    def _refresh_all_views(
        self,
    ) -> None:
        """Refresh all JSON tools."""

        if not self._has_payload:
            return

        payload = self._payload

        # JSONValue includes None, so this is intentionally allowed.

        self._refresh_tree_view(
            payload
        )

        self._refresh_hierarchy_view(
            payload
        )

        self._reset_filter_levels()

        self._refresh_graph_view(
            payload
        )

        self._refresh_jsonpath_view(
            payload
        )

        self._refresh_schema_view(
            payload
        )

        self._refresh_masking_view(
            payload
        )

        self._refresh_export_view(
            payload
        )

        self._refresh_payload_status(
            payload
        )

    # =================================================================
    # Tree refresh
    # =================================================================

    def _refresh_tree_view(
        self,
        payload: JSONValue,
    ) -> None:
        """Refresh lazy tree."""

        self._tree_view.set_payload(
            payload
        )

    # =================================================================
    # Hierarchy refresh
    # =================================================================

    def _refresh_hierarchy_view(
        self,
        payload: JSONValue,
    ) -> None:
        """Refresh hierarchy visualization."""

        size_info = (
            self._large_json_service
            .analyze(payload)
        )

        preview_limit = (
            self._large_json_service
            .settings
            .hierarchy_preview_nodes
        )

        if (
            size_info.total_nodes
            > preview_limit
        ):
            message = (
                "Large JSON detected.\n\n"
                f"{size_info.total_nodes:,} nodes\n"
                f"{size_info.containers:,} containers\n"
                f"{size_info.primitives:,} primitive values\n"
                f"Maximum depth: {size_info.max_depth}\n\n"
                "The complete hierarchy is not "
                "automatically generated to keep "
                "Jsonify responsive.\n\n"
                f"Hierarchy safety limit: "
                f"{preview_limit:,} nodes."
            )

            self._hierarchy_view.setPlainText(
                message
            )

            return

        hierarchy = (
            build_hierarchy_text(
                payload
            )
        )

        self._hierarchy_view.setPlainText(
            hierarchy
        )

    # =================================================================
    # Graph refresh
    # =================================================================

    def _refresh_graph_view(
        self,
        payload: JSONValue,
    ) -> None:
        """Refresh advanced graph."""

        self._graph_view.set_payload(
            payload
        )

    # =================================================================
    # JSONPath refresh
    # =================================================================

    def _refresh_jsonpath_view(
        self,
        payload: JSONValue,
    ) -> None:
        """Refresh JSONPath payload."""

        self._jsonpath_view.set_payload(
            payload
        )

    # =================================================================
    # Schema refresh
    # =================================================================

    def _refresh_schema_view(
        self,
        payload: JSONValue,
    ) -> None:
        """Refresh schema validation payload."""

        self._schema_view.set_payload(
            payload
        )

    # =================================================================
    # Masking refresh
    # =================================================================

    def _refresh_masking_view(
        self,
        payload: JSONValue,
    ) -> None:
        """Refresh sensitive-data masking payload."""

        self._masking_view.set_payload(
            payload
        )

    # =================================================================
    # Export refresh
    # =================================================================

    def _refresh_export_view(
        self,
        payload: JSONValue,
    ) -> None:
        """Refresh export source payload."""

        if hasattr(
            self._export_view,
            "set_payload",
        ):
            self._export_view.set_payload(
                payload
            )

        if hasattr(
            self._export_view,
            "set_graph_view",
        ):
            self._export_view.set_graph_view(
                self._graph_view
            )

    # =================================================================
    # Payload status / Large JSON information
    # =================================================================

    def _refresh_payload_status(
        self,
        payload: JSONValue,
    ) -> None:
        """Display JSON size information."""

        size_info = (
            self._large_json_service
            .analyze(payload)
        )

        large_text = ""

        if (
            self._large_json_service
            .should_use_lazy_tree(
                size_info
            )
        ):
            large_text = " | Large JSON"

        status = (
            f"{size_info.total_nodes:,} nodes"
            f" | Depth {size_info.max_depth}"
            f" | {self._document_count:,} document(s)"
            f"{large_text}"
        )

        self._payload_status.setText(
            status
        )

        self.statusBar().showMessage(
            f"JSON loaded | {status}",
            5000,
        )

    # =================================================================
    # Filter levels
    # =================================================================

    def _reset_filter_levels(
        self,
    ) -> None:
        """Reset filtered-view dropdowns."""

        for combo in (
            self._level_combos
        ):
            self._levels_layout.removeWidget(
                combo
            )

            combo.deleteLater()

        self._level_combos.clear()

        self._filtered_view.setPlainText(
            FILTERED_VIEW_PLACEHOLDER
        )

        if not self._has_payload:
            return

        first_level_keys = keys_at_path(
            self._payload,
            [],
        )

        if first_level_keys:
            self._add_level_combo(
                first_level_keys
            )

    def _add_level_combo(
        self,
        keys: list[str],
    ) -> None:
        """Add hierarchy-level selector."""

        combo = QComboBox()

        combo.addItem(
            LEVEL_PLACEHOLDER
        )

        combo.addItems(
            keys
        )

        combo.currentIndexChanged.connect(
            lambda _index, current=combo:
            self._on_level_changed(
                current
            )
        )

        button_index = (
            self._levels_layout
            .indexOf(
                self._show_filtered_button
            )
        )

        self._levels_layout.insertWidget(
            button_index,
            combo,
        )

        self._level_combos.append(
            combo
        )

    def _current_filter_path(
        self,
    ) -> list[str]:
        """Return selected hierarchy path."""

        path: list[str] = []

        for combo in (
            self._level_combos
        ):
            selected_key = (
                combo.currentText()
            )

            if (
                not selected_key
                or selected_key
                == LEVEL_PLACEHOLDER
            ):
                break

            path.append(
                selected_key
            )

        return path

    def _on_level_changed(
        self,
        combo: QComboBox,
    ) -> None:
        """Handle hierarchy-level change."""

        if (
            combo
            not in self._level_combos
        ):
            return

        index = (
            self._level_combos
            .index(combo)
        )

        stale_combos = (
            self._level_combos[
                index + 1 :
            ]
        )

        for stale_combo in (
            stale_combos
        ):
            self._levels_layout.removeWidget(
                stale_combo
            )

            stale_combo.deleteLater()

        self._level_combos = (
            self._level_combos[
                : index + 1
            ]
        )

        path = (
            self._current_filter_path()
        )

        if (
            len(path)
            != index + 1
        ):
            return

        if not self._has_payload:
            return

        next_keys = keys_at_path(
            self._payload,
            path,
        )

        if next_keys:
            self._add_level_combo(
                next_keys
            )

    def _show_filtered(
        self,
    ) -> None:
        """Render selected filtered hierarchy."""

        if not self._has_payload:
            QMessageBox.information(
                self,
                MESSAGE_NO_JSON_TITLE,
                MESSAGE_NO_JSON,
            )

            return

        path = (
            self._current_filter_path()
        )

        result = (
            build_path_filtered_hierarchy_text(
                self._payload,
                path,
            )
        )

        self._filtered_view.setPlainText(
            result
        )

    # =================================================================
    # Saved Sessions
    # =================================================================

    def _build_current_session(
        self,
    ) -> JsonifySession | None:
        """Build session from current application state."""

        if not self._has_payload:
            QMessageBox.information(
                self,
                MESSAGE_NO_JSON_TITLE,
                MESSAGE_NO_JSON,
            )

            return None

        selected_tab = (
            self._view_tabs.tabText(
                self._view_tabs.currentIndex()
            )
        )

        # Remove visual PRO suffix if present.

        selected_tab = (
            selected_tab
            .replace(
                "  PRO",
                "",
            )
        )

        jsonpath_query = ""

        if hasattr(
            self._jsonpath_view,
            "get_query",
        ):
            jsonpath_query = (
                self._jsonpath_view
                .get_query()
            )

        name = "Untitled Session"

        if (
            self._current_session
            is not None
        ):
            name = (
                self._current_session.name
            )

        return (
            self._session_service
            .create_session(
                name=name,
                payload=self._payload,
                selected_tab=selected_tab,
                jsonpath_query=jsonpath_query,
            )
        )

    def _save_session(
        self,
    ) -> None:
        """Save current session."""

        if not (
            self._license_service
            .has_feature(
                Feature.SAVED_SESSIONS
            )
        ):
            self._show_pro_required(
                "Saved Sessions"
            )

            return

        if (
            self._current_session_path
            is None
        ):
            self._save_session_as()

            return

        session = (
            self._build_current_session()
        )

        if session is None:
            return

        if (
            self._current_session
            is not None
        ):
            session.name = (
                self._current_session.name
            )

            session.created_at = (
                self._current_session
                .created_at
            )

        try:
            saved_path = (
                self._session_service
                .save(
                    session,
                    self._current_session_path,
                )
            )

        except SessionError as error:
            QMessageBox.critical(
                self,
                "Save Session",
                str(error),
            )

            return

        self._current_session = (
            session
        )

        self._current_session_path = (
            saved_path
        )

        self.statusBar().showMessage(
            (
                "Session saved: "
                f"{saved_path.name}"
            ),
            5000,
        )

    def _save_session_as(
        self,
    ) -> None:
        """Save current session to a new file."""

        if not (
            self._license_service
            .has_feature(
                Feature.SAVED_SESSIONS
            )
        ):
            self._show_pro_required(
                "Saved Sessions"
            )

            return

        session = (
            self._build_current_session()
        )

        if session is None:
            return

        file_name, _ = (
            QFileDialog.getSaveFileName(
                self,
                "Save Jsonify Session",
                session.name,
                (
                    "Jsonify Session "
                    "(*.jsonify)"
                ),
            )
        )

        if not file_name:
            return

        session_name = (
            Path(file_name).stem
        )

        session.name = (
            session_name
            or "Untitled Session"
        )

        try:
            saved_path = (
                self._session_service
                .save(
                    session,
                    file_name,
                )
            )

        except SessionError as error:
            QMessageBox.critical(
                self,
                "Save Session",
                str(error),
            )

            return

        self._current_session = (
            session
        )

        self._current_session_path = (
            saved_path
        )

        self.statusBar().showMessage(
            (
                "Session saved: "
                f"{saved_path.name}"
            ),
            5000,
        )

    def _open_session(
        self,
    ) -> None:
        """Open a Jsonify session."""

        if not (
            self._license_service
            .has_feature(
                Feature.SAVED_SESSIONS
            )
        ):
            self._show_pro_required(
                "Saved Sessions"
            )

            return

        file_name, _ = (
            QFileDialog.getOpenFileName(
                self,
                "Open Jsonify Session",
                "",
                (
                    "Jsonify Session "
                    "(*.jsonify)"
                ),
            )
        )

        if not file_name:
            return

        try:
            session = (
                self._session_service
                .load(file_name)
            )

        except SessionError as error:
            QMessageBox.critical(
                self,
                "Open Session",
                str(error),
            )

            return

        self._current_session = (
            session
        )

        self._current_session_path = (
            Path(file_name)
        )

        self._restore_session(
            session
        )

    def _restore_session(
        self,
        session: JsonifySession,
    ) -> None:
        """Restore saved session."""

        self._payload = (
            session.payload
        )

        self._has_payload = True

        self._document_count = 1

        self._editor.setPlainText(
            json.dumps(
                session.payload,
                indent=2,
                ensure_ascii=False,
            )
        )

        self._refresh_all_views()

        if (
            session.workspace
            .jsonpath_query
            and hasattr(
                self._jsonpath_view,
                "set_query",
            )
        ):
            self._jsonpath_view.set_query(
                session.workspace
                .jsonpath_query
            )

        self._restore_selected_tab(
            session.workspace
            .selected_tab
        )

        self.statusBar().showMessage(
            (
                "Session loaded: "
                f"{session.name}"
            ),
            5000,
        )

    def _restore_selected_tab(
        self,
        tab_name: str,
    ) -> None:
        """Restore selected tab by name."""

        if not tab_name:
            return

        for index in range(
            self._view_tabs.count()
        ):
            current_name = (
                self._view_tabs
                .tabText(index)
                .replace(
                    "  PRO",
                    "",
                )
            )

            if (
                current_name
                == tab_name
            ):
                if (
                    self._view_tabs
                    .isTabEnabled(index)
                ):
                    self._view_tabs.setCurrentIndex(
                        index
                    )

                return

    # =================================================================
    # Licensing
    # =================================================================

    def _load_saved_license(
        self,
    ) -> None:
        """Load locally activated license."""

        license_path = (
            self._license_storage
            .get_license_path()
        )

        if not license_path.exists():
            return

        try:
            self._license_service.activate_file(
                license_path
            )

        except (
            LicenseError,
            OSError,
        ):
            self._license_service.reset_to_free()

    def _setup_licensed_features(
        self,
    ) -> None:
        """Map Pro features to UI tabs."""

        self._licensed_tabs: dict[
            Feature,
            tuple[QWidget, str],
        ] = {
            Feature.JSON_DIFF: (
                self._diff_view,
                "JSON Diff",
            ),
            Feature.JSONPATH: (
                self._jsonpath_view,
                "JSONPath",
            ),
            Feature.SCHEMA_VALIDATION: (
                self._schema_view,
                "Schema",
            ),
            Feature.DATA_MASKING: (
                self._masking_view,
                "Data Masking",
            ),
            Feature.API_VIEWER: (
                self._api_view,
                "API Viewer",
            ),
            Feature.EXPORT: (
                self._export_view,
                "Export",
            ),
        }

    def _refresh_license_access(
        self,
    ) -> None:
        """Refresh Free/Pro feature access."""

        for (
            feature,
            (
                widget,
                base_name,
            ),
        ) in self._licensed_tabs.items():

            index = (
                self._view_tabs
                .indexOf(widget)
            )

            if index < 0:
                continue

            allowed = (
                self._license_service
                .has_feature(feature)
            )

            self._view_tabs.setTabEnabled(
                index,
                allowed,
            )

            if allowed:
                tab_name = base_name

            else:
                tab_name = (
                    f"{base_name}  PRO"
                )

            self._view_tabs.setTabText(
                index,
                tab_name,
            )

        # -------------------------------------------------------------
        # Saved Sessions
        # -------------------------------------------------------------

        session_allowed = (
            self._license_service
            .has_feature(
                Feature.SAVED_SESSIONS
            )
        )

        self._save_session_action.setEnabled(
            session_allowed
        )

        self._save_session_as_action.setEnabled(
            session_allowed
        )

        self._open_session_action.setEnabled(
            session_allowed
        )

        # -------------------------------------------------------------
        # Advanced Graph
        # -------------------------------------------------------------

        advanced_graph_allowed = (
            self._license_service
            .has_feature(
                Feature.ADVANCED_GRAPH
            )
        )

        if hasattr(
            self._graph_view,
            "set_pro_features_enabled",
        ):
            self._graph_view.set_pro_features_enabled(
                advanced_graph_allowed
            )

        # -------------------------------------------------------------
        # License tab
        # -------------------------------------------------------------

        self._license_view.refresh()

        license_info = (
            self._license_service
            .current_license
        )

        if license_info.is_pro:
            self.statusBar().showMessage(
                "Jsonify Pro activated",
                3000,
            )

    def _show_license_tab(
        self,
    ) -> None:
        """Open License tab."""

        index = (
            self._view_tabs
            .indexOf(
                self._license_view
            )
        )

        if index >= 0:
            self._view_tabs.setCurrentIndex(
                index
            )

    def _show_pro_required(
        self,
        feature_name: str,
    ) -> None:
        """Inform user that a feature requires Pro."""

        result = QMessageBox.information(
            self,
            "Jsonify Pro",
            (
                f"{feature_name} is available "
                "with Jsonify Pro.\n\n"
                "Open the License tab to "
                "activate a Pro license."
            ),
            (
                QMessageBox.StandardButton.Ok
            ),
        )

        _ = result

    # =================================================================
    # Close
    # =================================================================

    def closeEvent(
        self,
        event,
    ) -> None:
        """Handle application close."""

        event.accept()