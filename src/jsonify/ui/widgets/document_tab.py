"""A single open JSON document: its editor plus its full set of tool views.

Jsonify supports multiple documents open at once (see ``MainWindow``'s
document ``QTabWidget``). Each open document gets its own ``DocumentTab``,
which owns the editor/viewer split and every per-document tool view (tree,
hierarchy, filtered, graph, diff, JSONPath, schema, masking, API, export)
plus that document's saved-session state.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from jsonify.core.analyzer import analyze_json
from jsonify.core.diagnostics import measure_document
from jsonify.core.filter import FilterCriteria, filter_json
from jsonify.core.formatter import beautify, minify, normalize
from jsonify.core.models import JSONValue
from jsonify.core.parser import find_duplicate_keys
from jsonify.core.plugins import get_registry
from jsonify.core.pointer import from_json_pointer, to_json_path, to_json_pointer
from jsonify.core.repair import attempt_repair
from jsonify.core.search import search_json
from jsonify.core.session import JsonifySession
from jsonify.core.traversal import calculate_json_stats, to_table_rows
from jsonify.services import JsonService
from jsonify.services.large_json_service import LargeJsonService
from jsonify.services.session_service import SessionError, SessionService
from jsonify.ui.constants import (
    FILTERED_VIEW_PLACEHOLDER,
    LEVEL_PLACEHOLDER,
    MESSAGE_INVALID_JSON_TITLE,
    MESSAGE_NO_JSON,
    MESSAGE_NO_JSON_TITLE,
    MESSAGE_NOTHING_TO_LOAD,
    MESSAGE_NOTHING_TO_LOAD_TITLE,
    MONOSPACE_FONT,
)
from jsonify.ui.widgets.advanced_graph_view import AdvancedGraphView
from jsonify.ui.widgets.api_view import ApiView
from jsonify.ui.widgets.code_editor import CodeEditor
from jsonify.ui.widgets.codegen_view import CodeGenView
from jsonify.ui.widgets.converters_view import ConvertersView
from jsonify.ui.widgets.devtools_view import DevToolsView
from jsonify.ui.widgets.diff_view import DiffView
from jsonify.ui.widgets.export_view import ExportView
from jsonify.ui.widgets.hierarchy_view import (
    build_hierarchy_text,
    build_path_filtered_hierarchy_text,
    keys_at_path,
)
from jsonify.ui.widgets.jq_view import JqView
from jsonify.ui.widgets.jsonpath_view import JsonPathView
from jsonify.ui.widgets.lazy_tree_view import LazyJsonTreeModel, LazyJsonTreeView
from jsonify.ui.widgets.masking_view import MaskingView
from jsonify.ui.widgets.notes_view import NotesView
from jsonify.ui.widgets.openapi_view import OpenApiView
from jsonify.ui.widgets.schema_view import SchemaView


class DocumentTab(QWidget):
    """One open JSON document: its editor plus every tool view over it."""

    title_changed = Signal(str)
    status_changed = Signal(str)

    def __init__(
        self,
        json_service: JsonService | None = None,
        large_json_service: LargeJsonService | None = None,
        session_service: SessionService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._json_service = json_service if json_service is not None else JsonService()
        self._large_json_service = large_json_service or LargeJsonService()
        self._session_service = session_service or SessionService()

        # Current JSON state.
        self._payload: JSONValue | None = None

        # JSON "null" becomes Python None, so `_payload is None` cannot be
        # used to determine whether JSON has actually been loaded.
        self._has_payload = False
        self._document_count = 0

        # Identity: a document is either a plain opened/pasted JSON file,
        # or a restored/saved Jsonify session — tracked separately since
        # they use different file formats and "Save" targets.
        self.file_path: Path | None = None
        self._is_jsonl = False
        self._current_session: JsonifySession | None = None
        self._current_session_path: Path | None = None
        self._is_dirty = False

        # Filter (drill-into) state.
        self._level_combos: list[QComboBox] = []

        # Bookmarked nodes and per-node notes, keyed by JSON Pointer.
        self._bookmarks: list[str] = []
        self._annotations: dict[str, str] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._create_split_view(), stretch=1)

        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(self.focus_search_box)

    # =================================================================
    # Identity / tab title
    # =================================================================

    def display_name(self) -> str:
        """Return the name to show on this document's tab."""

        if self.file_path is not None:
            base = self.file_path.name
        elif self._current_session is not None:
            base = self._current_session.name
        else:
            base = "Untitled"

        return f"{base} ●" if self._is_dirty else base

    def _mark_dirty(self, dirty: bool = True) -> None:
        if self._is_dirty == dirty:
            return
        self._is_dirty = dirty
        self.title_changed.emit(self.display_name())

    # =================================================================
    # Split view
    # =================================================================

    def _create_split_view(self) -> QSplitter:
        """Create editor/viewer split layout."""

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._create_editor_panel())
        splitter.addWidget(self._create_viewer_panel())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([650, 850])
        return splitter

    # =================================================================
    # Editor
    # =================================================================

    def _create_editor_panel(self) -> QWidget:
        """Create JSON editor panel."""

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 6, 6, 6)

        header = QHBoxLayout()
        header.addWidget(QLabel("JSON Editor"))
        header.addStretch(1)

        format_button = QToolButton()
        format_button.setText("Format ▾")
        format_button.setStyleSheet("QToolButton::menu-indicator { image: none; }")
        format_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        format_menu = QMenu(format_button)

        beautify_action = QAction("Beautify (2-space indent)", self)
        beautify_action.triggered.connect(lambda: self._format_editor(indent=2))
        format_menu.addAction(beautify_action)

        beautify_tab_action = QAction("Beautify (4-space indent)", self)
        beautify_tab_action.triggered.connect(lambda: self._format_editor(indent=4))
        format_menu.addAction(beautify_tab_action)

        minify_action = QAction("Minify", self)
        minify_action.triggered.connect(self._minify_editor)
        format_menu.addAction(minify_action)

        normalize_action = QAction("Normalize (sort keys)", self)
        normalize_action.triggered.connect(self._normalize_editor)
        format_menu.addAction(normalize_action)

        format_button.setMenu(format_menu)
        header.addWidget(format_button)

        self._repair_button = QPushButton("Repair")
        self._repair_button.setToolTip("Attempt to fix common JSON syntax mistakes")
        self._repair_button.clicked.connect(self._repair_editor)
        header.addWidget(self._repair_button)

        self._load_button = QPushButton("▶ LOAD JSON")
        self._load_button.clicked.connect(self._load_json)
        header.addWidget(self._load_button)

        layout.addLayout(header)

        self._duplicate_key_banner = QLabel()
        self._duplicate_key_banner.setWordWrap(True)
        self._duplicate_key_banner.setStyleSheet(
            "background-color: #5A1D1D; color: #ffffff; padding: 6px; border-radius: 3px;"
        )
        self._duplicate_key_banner.setVisible(False)
        layout.addWidget(self._duplicate_key_banner)

        self._editor = CodeEditor()
        self._editor.setPlaceholderText("Paste JSON payloads here, then click 'Load JSON'...")
        self._editor.fileDropped.connect(self._on_file_dropped)
        self._editor.textChanged.connect(lambda: self._mark_dirty(True))

        layout.addWidget(self._editor)

        return panel

    def _on_file_dropped(self, local_path: str) -> None:
        self.open_file(Path(local_path))

    def _on_api_send_to_diff(self, text: str, is_old: bool) -> None:
        if is_old:
            self._diff_view.set_old_text(text)
        else:
            self._diff_view.set_new_text(text)
        self._select_category("diff")

    def _send_payload_to_viewer(self, payload: JSONValue) -> None:
        """Load ``payload`` into this document's editor (from an API
        response, a converter, or a jq/JSONPath result)."""

        self._editor.setPlainText(beautify(payload, indent=2))
        self._load_json()
        self._select_category("json")

    def _on_api_response_loaded(self, payload: JSONValue) -> None:
        self._send_payload_to_viewer(payload)

    def _on_masked_payload_changed(self, payload: JSONValue | None) -> None:
        self._export_view.set_masked_payload(payload)

    def _on_converted_payload_loaded(self, payload: JSONValue) -> None:
        self._send_payload_to_viewer(payload)

    def _send_text_to_request_body(self, text: str) -> None:
        """Put jq/JSONPath result text into the API client's JSON body."""

        self._api_view.set_json_body(text)
        self._select_category("api")

    # =================================================================
    # Formatter
    # =================================================================

    def _format_editor(self, *, indent: int) -> None:
        try:
            payload = json.loads(self._editor.toPlainText())
        except json.JSONDecodeError as exc:
            QMessageBox.critical(
                self, MESSAGE_INVALID_JSON_TITLE, f"Could not parse JSON:\n\n{exc}"
            )
            return

        self._editor.setPlainText(beautify(payload, indent=indent))

    def _minify_editor(self) -> None:
        try:
            payload = json.loads(self._editor.toPlainText())
        except json.JSONDecodeError as exc:
            QMessageBox.critical(
                self, MESSAGE_INVALID_JSON_TITLE, f"Could not parse JSON:\n\n{exc}"
            )
            return

        self._editor.setPlainText(minify(payload))

    def _normalize_editor(self) -> None:
        try:
            payload = json.loads(self._editor.toPlainText())
        except json.JSONDecodeError as exc:
            QMessageBox.critical(
                self, MESSAGE_INVALID_JSON_TITLE, f"Could not parse JSON:\n\n{exc}"
            )
            return

        self._editor.setPlainText(beautify(normalize(payload), indent=2))

    # =================================================================
    # Repair
    # =================================================================

    def _repair_editor(self) -> None:
        raw_text = self._editor.toPlainText()

        if not raw_text.strip():
            QMessageBox.information(self, MESSAGE_NOTHING_TO_LOAD_TITLE, MESSAGE_NOTHING_TO_LOAD)
            return

        result = attempt_repair(raw_text)

        if not result.applied_fixes:
            QMessageBox.information(
                self,
                "Repair JSON",
                "No safely recoverable issues were found."
                if not result.is_valid
                else "This JSON is already valid — nothing to repair.",
            )
            return

        fixes_text = "\n".join(f"• {fix}" for fix in result.applied_fixes)
        validity = (
            "The result is valid JSON."
            if result.is_valid
            else ("The result is still not valid JSON, but these fixes were applied anyway.")
        )

        confirmed = QMessageBox.question(
            self,
            "Repair JSON",
            f"The following fixes can be applied:\n\n{fixes_text}\n\n{validity}\n\nApply them?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirmed == QMessageBox.StandardButton.Yes:
            self._editor.setPlainText(result.text)

    # =================================================================
    # Viewer
    # =================================================================

    def _create_viewer_panel(self) -> QWidget:
        """Create the visualization panel: an activity bar of tool
        categories on the left, and a stacked area on the right showing
        whichever category is selected."""

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(QLabel("Viewer"))

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        activity_bar = QWidget()
        self._activity_bar_layout = QVBoxLayout(activity_bar)
        self._activity_bar_layout.setContentsMargins(0, 4, 0, 4)
        self._activity_bar_layout.setSpacing(2)
        self._activity_bar_layout.addStretch(1)

        activity_bar_scroll = QScrollArea()
        activity_bar_scroll.setWidget(activity_bar)
        activity_bar_scroll.setWidgetResizable(True)
        activity_bar_scroll.setFixedWidth(68)
        activity_bar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        activity_bar_scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        self._activity_group = QButtonGroup(self)
        self._activity_group.setExclusive(True)

        self._sidebar_stack = QStackedWidget()
        self._category_indices: dict[str, int] = {}
        self._category_buttons: dict[str, QToolButton] = {}

        body_layout.addWidget(activity_bar_scroll)
        body_layout.addWidget(self._sidebar_stack, stretch=1)
        layout.addWidget(body, stretch=1)

        # -----------------------------------------------------------------
        # "JSON" category: the core tree/hierarchy/filtered/graph views,
        # grouped under one activity-bar entry since they're switched
        # between constantly while exploring a single payload.
        # -----------------------------------------------------------------

        self._json_tools_tabs = QTabWidget()
        self._create_tree_tab()
        self._create_hierarchy_tab()

        self._filtered_view_container = self._create_filtered_tab()
        self._json_tools_tabs.addTab(self._filtered_view_container, "Filtered View")

        self._graph_view = AdvancedGraphView()
        self._json_tools_tabs.addTab(self._graph_view, "Graph")

        self._create_table_tab()
        self._create_analyzer_tab()
        self._create_notes_tab()
        self._create_diagnostics_tab()

        json_category = QWidget()
        json_category_layout = QVBoxLayout(json_category)
        json_category_layout.setContentsMargins(0, 0, 0, 0)
        json_category_layout.setSpacing(4)
        json_category_layout.addWidget(self._create_search_bar())
        json_category_layout.addWidget(self._json_tools_tabs, stretch=1)

        self._add_activity_category(
            "json",
            "JSON",
            "JSON views: tree, hierarchy, filter, graph, table, analyzer",
            json_category,
        )

        self._advanced_filter_container = self._create_advanced_filter_tab()
        self._add_activity_category(
            "filter",
            "Filter",
            "Advanced filter (preserves hierarchy)",
            self._advanced_filter_container,
        )

        self._diff_view = DiffView()
        self._add_activity_category("diff", "Diff", "JSON Diff", self._diff_view)

        self._jsonpath_view = JsonPathView()
        self._jsonpath_view.send_to_viewer.connect(self._send_payload_to_viewer)
        self._jsonpath_view.send_to_request_body.connect(self._send_text_to_request_body)
        self._add_activity_category("query", "Query", "JSONPath", self._jsonpath_view)

        self._jq_view = JqView()
        self._jq_view.send_to_viewer.connect(self._send_payload_to_viewer)
        self._jq_view.send_to_request_body.connect(self._send_text_to_request_body)
        self._add_activity_category("jq", "jq", "jq-lite query", self._jq_view)

        self._schema_view = SchemaView()
        self._add_activity_category("schema", "Schema", "Schema Validation", self._schema_view)

        self._openapi_view = OpenApiView()
        self._add_activity_category(
            "openapi", "OpenAPI", "OpenAPI Response Validation", self._openapi_view
        )

        self._converters_view = ConvertersView()
        self._converters_view.payload_loaded.connect(self._on_converted_payload_loaded)
        self._add_activity_category(
            "convert", "Convert", "JSON <-> YAML/XML/CSV", self._converters_view
        )

        self._codegen_view = CodeGenView()
        self._add_activity_category("codegen", "Code", "Code Generator", self._codegen_view)

        self._masking_view = MaskingView()
        self._masking_view.masked_payload_changed.connect(self._on_masked_payload_changed)
        self._add_activity_category("mask", "Mask", "Data Masking", self._masking_view)

        self._api_view = ApiView()
        self._api_view.send_to_diff.connect(self._on_api_send_to_diff)
        self._api_view.response_loaded.connect(self._on_api_response_loaded)
        self._add_activity_category("api", "API", "API Viewer", self._api_view)

        self._export_view = ExportView()
        self._add_activity_category("export", "Export", "Export", self._export_view)

        self._devtools_view = DevToolsView()
        self._add_activity_category(
            "tools", "Tools", "JWT, Base64, escape, timestamp, UUID, hash", self._devtools_view
        )

        self._select_category("json")

        return panel

    def _add_activity_category(self, key: str, label: str, tooltip: str, widget: QWidget) -> None:
        """Register one activity-bar entry and its sidebar content widget."""

        button = QToolButton()
        button.setObjectName("activityBarButton")
        button.setText(label)
        button.setToolTip(tooltip)
        button.setCheckable(True)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._activity_group.addButton(button)
        # Insert before the trailing stretch so buttons stack top-down.
        self._activity_bar_layout.insertWidget(self._activity_bar_layout.count() - 1, button)

        index = self._sidebar_stack.addWidget(widget)
        self._category_indices[key] = index
        self._category_buttons[key] = button
        button.clicked.connect(lambda _checked=False, k=key: self._select_category(k))

    def _select_category(self, key: str) -> None:
        index = self._category_indices.get(key)
        button = self._category_buttons.get(key)

        if index is None or button is None:
            return

        self._sidebar_stack.setCurrentIndex(index)
        button.setChecked(True)

    def _current_category_key(self) -> str:
        current_index = self._sidebar_stack.currentIndex()
        for key, index in self._category_indices.items():
            if index == current_index:
                return key
        return "json"

    # =================================================================
    # Tree View
    # =================================================================

    def _create_tree_tab(self) -> None:
        """Create optimized lazy JSON tree, with a type-inspector footer."""

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._tree_view = LazyJsonTreeView()
        self._tree_view.node_selected.connect(self._update_type_inspector)
        self._tree_view.bookmark_requested.connect(self._on_bookmark_requested)
        self._tree_view.annotate_requested.connect(self._on_annotate_requested)
        layout.addWidget(self._tree_view, stretch=1)

        self._type_inspector_label = QLabel("Select a node to inspect its type and path.")
        self._type_inspector_label.setWordWrap(True)
        layout.addWidget(self._type_inspector_label)

        self._json_tools_tabs.addTab(container, "Normal View")

    def _update_type_inspector(self, node) -> None:
        if node is None:
            self._type_inspector_label.setText("Select a node to inspect its type and path.")
            return

        segments = node.path_segments()
        type_name = LazyJsonTreeModel.type_name(node.value)

        details = f"Type: {type_name}"
        if isinstance(node.value, dict):
            details += f"  |  {len(node.value)} key(s)"
        elif isinstance(node.value, list):
            details += f"  |  {len(node.value)} item(s)"

        details += f"\nJSONPath: {to_json_path(segments)}"
        details += f"\nJSON Pointer: {to_json_pointer(segments) or '(root)'}"

        self._type_inspector_label.setText(details)

    # =================================================================
    # Hierarchy View
    # =================================================================

    def _create_hierarchy_tab(self) -> None:
        """Create text hierarchy view."""

        self._hierarchy_view = QPlainTextEdit()
        self._hierarchy_view.setReadOnly(True)

        font = self._hierarchy_view.font()
        font.setFamily(MONOSPACE_FONT)
        self._hierarchy_view.setFont(font)

        self._json_tools_tabs.addTab(self._hierarchy_view, "Hierarchy View")

    # =================================================================
    # Filtered View
    # =================================================================

    def _create_filtered_tab(self) -> QWidget:
        """Create hierarchical filtered JSON view."""

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(4)

        levels_row = QWidget()
        self._levels_layout = QHBoxLayout(levels_row)
        self._levels_layout.setContentsMargins(8, 8, 8, 0)
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

        container_layout.addWidget(self._filtered_view, stretch=1)

        return container

    # =================================================================
    # Search (Ctrl+F)
    # =================================================================

    def _create_search_bar(self) -> QWidget:
        """Create the key/value search bar shown above the JSON sub-tabs."""

        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(4, 4, 4, 0)
        layout.setSpacing(6)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search keys/values... (Ctrl+F)")
        self._search_box.returnPressed.connect(self._go_to_next_match)
        layout.addWidget(self._search_box, stretch=1)

        self._search_target = QComboBox()
        self._search_target.addItems(["Both", "Keys", "Values"])
        layout.addWidget(self._search_target)

        self._search_case_sensitive = QCheckBox("Case")
        layout.addWidget(self._search_case_sensitive)

        self._search_regex = QCheckBox("Regex")
        layout.addWidget(self._search_regex)

        prev_button = QPushButton("◀")
        prev_button.setFixedWidth(32)
        prev_button.clicked.connect(self._go_to_prev_match)
        layout.addWidget(prev_button)

        next_button = QPushButton("▶")
        next_button.setFixedWidth(32)
        next_button.clicked.connect(self._go_to_next_match)
        layout.addWidget(next_button)

        self._search_match_label = QLabel("")
        layout.addWidget(self._search_match_label)

        for widget in (self._search_target, self._search_case_sensitive, self._search_regex):
            widget_signal = (
                widget.currentIndexChanged if isinstance(widget, QComboBox) else widget.toggled
            )
            widget_signal.connect(lambda *_args: self._run_search())

        self._search_box.textChanged.connect(self._run_search)

        self._search_matches: list = []
        self._search_match_index = -1

        return bar

    def focus_search_box(self) -> None:
        """Select the JSON category and focus its search box (Ctrl+F)."""

        self._select_category("json")
        self._search_box.setFocus()
        self._search_box.selectAll()

    def _run_search(self) -> None:
        query = self._search_box.text()

        if not query or not self._has_payload:
            self._search_matches = []
            self._search_match_index = -1
            self._search_match_label.setText("")
            return

        target_map = {"Both": "both", "Keys": "key", "Values": "value"}
        target = target_map[self._search_target.currentText()]

        self._search_matches = search_json(
            self._payload,
            query,
            target=target,
            case_sensitive=self._search_case_sensitive.isChecked(),
            use_regex=self._search_regex.isChecked(),
        )
        self._search_match_index = -1

        if self._search_matches:
            self._go_to_next_match()
        else:
            self._search_match_label.setText("0 / 0")

    def _go_to_next_match(self) -> None:
        self._step_search(1)

    def _go_to_prev_match(self) -> None:
        self._step_search(-1)

    def _step_search(self, direction: int) -> None:
        if not self._search_matches:
            self._run_search()
            if not self._search_matches:
                return

        count = len(self._search_matches)
        self._search_match_index = (self._search_match_index + direction) % count

        match = self._search_matches[self._search_match_index]
        self._search_match_label.setText(f"{self._search_match_index + 1} / {count}")

        self._select_category("json")
        self._json_tools_tabs.setCurrentWidget(self._tree_view.parentWidget())
        self._tree_view.select_path(match.segments)

    # =================================================================
    # Table View
    # =================================================================

    def _create_table_tab(self) -> None:
        """Create a sortable table view for arrays of objects."""

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table_filter_box = QLineEdit()
        self._table_filter_box.setPlaceholderText("Filter rows...")
        self._table_filter_box.textChanged.connect(self._apply_table_filter)
        layout.addWidget(self._table_filter_box)

        self._table_view = QTableWidget()
        self._table_view.setSortingEnabled(True)
        self._table_view.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table_view, stretch=1)

        self._table_full_rows: list[list[JSONValue]] = []
        self._table_columns: list[str] = []

        self._json_tools_tabs.addTab(container, "Table")

    def _refresh_table_view(self, payload: JSONValue) -> None:
        columns, rows = to_table_rows(payload)

        self._table_full_rows = rows
        self._table_columns = columns

        self._populate_table(rows)

    def _populate_table(self, rows: list[list[JSONValue]]) -> None:
        self._table_view.setSortingEnabled(False)
        self._table_view.setColumnCount(len(self._table_columns))
        self._table_view.setHorizontalHeaderLabels(
            self._table_columns or ["(not an array of objects)"]
        )
        self._table_view.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            for col_index, cell in enumerate(row):
                text = (
                    ""
                    if cell is None
                    else (minify(cell) if isinstance(cell, dict | list) else str(cell))
                )
                self._table_view.setItem(row_index, col_index, QTableWidgetItem(text))

        self._table_view.setSortingEnabled(True)

    def _apply_table_filter(self, text: str) -> None:
        if not text:
            self._populate_table(self._table_full_rows)
            return

        needle = text.lower()
        filtered = [
            row
            for row in self._table_full_rows
            if any(needle in str(cell).lower() for cell in row if cell is not None)
        ]
        self._populate_table(filtered)

    # =================================================================
    # JSON Analyzer
    # =================================================================

    def _create_analyzer_tab(self) -> None:
        """Create the heuristic-analysis report panel."""

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self._analyzer_output = QPlainTextEdit()
        self._analyzer_output.setReadOnly(True)
        font = self._analyzer_output.font()
        font.setFamily(MONOSPACE_FONT)
        self._analyzer_output.setFont(font)
        layout.addWidget(self._analyzer_output)

        self._json_tools_tabs.addTab(container, "Analyzer")

    def _refresh_analyzer_view(self, payload: JSONValue) -> None:
        report = analyze_json(payload)

        lines: list[str] = []
        for category, findings in report.by_category().items():
            lines.append(f"=== {category.replace('_', ' ').title()} ({len(findings)}) ===")
            for finding in findings:
                lines.append(f"  {finding.path}: {finding.message}")
            lines.append("")

        for name, messages in get_registry().run_analyzers(payload).items():
            lines.append(f"=== Plugin: {name} ({len(messages)}) ===")
            lines.extend(f"  {message}" for message in messages)
            lines.append("")

        self._analyzer_output.setPlainText("\n".join(lines) if lines else "No issues found.")

    # =================================================================
    # Bookmarks & annotations
    # =================================================================

    def _create_notes_tab(self) -> None:
        self._notes_view = NotesView()
        self._notes_view.navigate_requested.connect(self._navigate_to_pointer)
        self._notes_view.bookmark_removed.connect(self._remove_bookmark)
        self._notes_view.annotation_removed.connect(self._remove_annotation)
        self._notes_view.annotation_edit_requested.connect(self._edit_annotation)
        self._json_tools_tabs.addTab(self._notes_view, "Notes")

    def _refresh_notes(self) -> None:
        self._notes_view.set_data(self._bookmarks, self._annotations)

    def _on_bookmark_requested(self, segments: list) -> None:
        pointer = to_json_pointer(segments)

        if pointer in self._bookmarks:
            self._bookmarks.remove(pointer)
            self.status_changed.emit(f"Bookmark removed: {pointer or '(root)'}")
        else:
            self._bookmarks.append(pointer)
            self.status_changed.emit(f"Bookmarked: {pointer or '(root)'}")

        self._refresh_notes()

    def _on_annotate_requested(self, segments: list) -> None:
        self._edit_annotation(to_json_pointer(segments))

    def _edit_annotation(self, pointer: str) -> None:
        text, accepted = QInputDialog.getMultiLineText(
            self,
            "Node Note",
            f"Note for {pointer or '(root)'} (leave empty to remove):",
            self._annotations.get(pointer, ""),
        )

        if not accepted:
            return

        if text.strip():
            self._annotations[pointer] = text.strip()
        else:
            self._annotations.pop(pointer, None)

        self._refresh_notes()

    def _remove_bookmark(self, pointer: str) -> None:
        if pointer in self._bookmarks:
            self._bookmarks.remove(pointer)
            self._refresh_notes()

    def _remove_annotation(self, pointer: str) -> None:
        if self._annotations.pop(pointer, None) is not None:
            self._refresh_notes()

    def _navigate_to_pointer(self, pointer: str) -> None:
        try:
            segments = from_json_pointer(pointer)
        except ValueError:
            return

        self._select_category("json")
        self._json_tools_tabs.setCurrentWidget(self._tree_view.parentWidget())

        if not self._tree_view.select_path(segments):
            self.status_changed.emit(f"{pointer or '(root)'} no longer exists in this document.")

    # =================================================================
    # Diagnostics
    # =================================================================

    def _create_diagnostics_tab(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)

        row = QHBoxLayout()
        run_button = QPushButton("Run Diagnostics")
        run_button.setToolTip("Re-parse the editor text and measure time, memory and structure")
        run_button.clicked.connect(self._run_diagnostics)
        row.addWidget(run_button)
        row.addStretch(1)
        layout.addLayout(row)

        self._diagnostics_output = QPlainTextEdit()
        self._diagnostics_output.setReadOnly(True)
        font = self._diagnostics_output.font()
        font.setFamily(MONOSPACE_FONT)
        self._diagnostics_output.setFont(font)
        self._diagnostics_output.setPlaceholderText(
            "Press 'Run Diagnostics' to measure parsing time, memory use and node count."
        )
        layout.addWidget(self._diagnostics_output, 1)

        self._json_tools_tabs.addTab(container, "Diagnostics")

    def _run_diagnostics(self) -> None:
        text = self._editor.toPlainText().strip()

        if not text:
            QMessageBox.warning(self, MESSAGE_NOTHING_TO_LOAD_TITLE, MESSAGE_NOTHING_TO_LOAD)
            return

        try:
            report, _value = measure_document(text)
        except json.JSONDecodeError as exc:
            self._diagnostics_output.setPlainText(f"Invalid JSON: {exc}")
            return

        self._diagnostics_output.setPlainText(report.format())

    # =================================================================
    # Advanced Filter
    # =================================================================

    def _create_advanced_filter_tab(self) -> QWidget:
        """Create the hierarchy-preserving advanced filter panel."""

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        form_row = QHBoxLayout()

        self._filter_key_box = QLineEdit()
        self._filter_key_box.setPlaceholderText("Key contains...")
        form_row.addWidget(self._filter_key_box)

        self._filter_value_box = QLineEdit()
        self._filter_value_box.setPlaceholderText("Value contains...")
        form_row.addWidget(self._filter_value_box)

        self._filter_type_box = QComboBox()
        self._filter_type_box.addItems(
            ["Any type", "object", "array", "string", "number", "boolean", "null"]
        )
        form_row.addWidget(self._filter_type_box)

        apply_button = QPushButton("Apply Filter")
        apply_button.clicked.connect(self._apply_advanced_filter)
        form_row.addWidget(apply_button)

        layout.addLayout(form_row)

        self._filter_output = CodeEditor()
        self._filter_output.setReadOnly(True)
        layout.addWidget(self._filter_output, stretch=1)

        return container

    def _apply_advanced_filter(self) -> None:
        if not self._has_payload:
            QMessageBox.information(self, MESSAGE_NO_JSON_TITLE, MESSAGE_NO_JSON)
            return

        type_choice = self._filter_type_box.currentText()
        criteria = FilterCriteria(
            key_contains=self._filter_key_box.text(),
            value_contains=self._filter_value_box.text(),
            type_name="" if type_choice == "Any type" else type_choice,
        )

        result = filter_json(self._payload, criteria)

        if result is None:
            self._filter_output.setPlainText("(no matches)")
        else:
            self._filter_output.setPlainText(beautify(result, indent=2))

    # =================================================================
    # File / JSON loading
    # =================================================================

    def open_file(self, path: Path) -> None:
        """Load a JSON file from disk into this document."""

        try:
            text = path.read_text(encoding="utf-8")
        except OSError as error:
            QMessageBox.critical(self, "Open File", f"Could not read file:\n\n{error}")
            return

        self.file_path = path
        self._is_jsonl = path.suffix.lower() in (".jsonl", ".ndjson")
        self._bookmarks = []
        self._annotations = {}
        self._current_session = None
        self._current_session_path = None
        self._editor.setPlainText(text)
        self._load_json()
        self._mark_dirty(False)

    def load_text(self, text: str) -> None:
        """Load raw JSON text into the editor and parse it."""

        self._editor.setPlainText(text)
        self._load_json()

    def load_from_editor(self) -> None:
        """Parse whatever text is currently in the editor (the "Load JSON" action)."""

        self._load_json()

    def editor_text(self) -> str:
        """Return the raw text currently in the editor."""

        return self._editor.toPlainText()

    def has_content(self) -> bool:
        """Return whether this document has any editor text or a loaded payload."""

        return bool(self._editor.toPlainText().strip()) or self._has_payload

    def apply_theme(self, theme: dict[str, str]) -> None:
        """Apply a theme's syntax-highlighting colors to this document's editor."""

        self._editor.apply_theme(theme)

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
            payload, document_count = self._json_service.parse_multiple(raw_text)
        except json.JSONDecodeError as exc:
            QMessageBox.critical(
                self,
                MESSAGE_INVALID_JSON_TITLE,
                f"Could not parse JSON:\n\n{exc}",
            )
            return

        # Only update state after successful parsing.
        self._payload = payload
        self._has_payload = True
        self._document_count = document_count

        # An ordinary JSON load is no longer associated with the
        # previously opened session.
        self._current_session = None
        self._current_session_path = None

        self._update_duplicate_key_banner(raw_text)
        self._refresh_all_views()
        self._mark_dirty(False)

    def _update_duplicate_key_banner(self, raw_text: str) -> None:
        duplicates = find_duplicate_keys(raw_text)

        if not duplicates:
            self._duplicate_key_banner.setVisible(False)
            return

        summary = "  •  ".join(duplicates[:5])
        if len(duplicates) > 5:
            summary += f"  •  (+{len(duplicates) - 5} more)"

        self._duplicate_key_banner.setText(f"⚠ Duplicate keys detected: {summary}")
        self._duplicate_key_banner.setVisible(True)

    # =================================================================
    # Refresh all views
    # =================================================================

    def _refresh_all_views(self) -> None:
        """Refresh all JSON tools."""

        if not self._has_payload:
            return

        payload = self._payload

        # JSONValue includes None, so this is intentionally allowed.
        self._tree_view.set_payload(payload)
        self._refresh_hierarchy_view(payload)
        self._reset_filter_levels()
        self._graph_view.set_payload(payload)
        self._jsonpath_view.set_payload(payload)
        self._jq_view.set_payload(payload)
        self._schema_view.set_payload(payload)
        self._openapi_view.set_payload(payload)
        self._converters_view.set_payload(payload)
        self._codegen_view.set_payload(payload)
        self._masking_view.set_payload(payload)
        self._refresh_export_view(payload)
        self._refresh_payload_status(payload)
        self._refresh_table_view(payload)
        self._refresh_analyzer_view(payload)
        self._update_type_inspector(None)
        self._refresh_notes()
        self._run_search()

    def _refresh_hierarchy_view(self, payload: JSONValue) -> None:
        """Refresh hierarchy visualization."""

        size_info = self._large_json_service.analyze(payload)
        preview_limit = self._large_json_service.settings.hierarchy_preview_nodes

        if size_info.total_nodes > preview_limit:
            message = (
                "Large JSON detected.\n\n"
                f"{size_info.total_nodes:,} nodes\n"
                f"{size_info.containers:,} containers\n"
                f"{size_info.primitives:,} primitive values\n"
                f"Maximum depth: {size_info.max_depth}\n\n"
                "The complete hierarchy is not automatically generated to "
                "keep Jsonify responsive.\n\n"
                f"Hierarchy safety limit: {preview_limit:,} nodes."
            )
            self._hierarchy_view.setPlainText(message)
            return

        self._hierarchy_view.setPlainText(build_hierarchy_text(payload))

    def _refresh_export_view(self, payload: JSONValue) -> None:
        """Refresh export source payload."""

        if hasattr(self._export_view, "set_payload"):
            self._export_view.set_payload(payload)

        if hasattr(self._export_view, "set_graph_view"):
            self._export_view.set_graph_view(self._graph_view)

    def _refresh_payload_status(self, payload: JSONValue) -> None:
        """Display JSON size information."""

        size_info = self._large_json_service.analyze(payload)
        large_text = ""

        if self._large_json_service.should_use_lazy_tree(size_info):
            large_text = " | Large JSON"

        stats = calculate_json_stats(payload)
        file_size = len(self._editor.toPlainText().encode("utf-8"))
        doc_label = "records (NDJSON)" if self._is_jsonl else "document(s)"

        status = (
            f"{size_info.total_nodes:,} nodes"
            f" | Depth {size_info.max_depth}"
            f" | {self._document_count:,} {doc_label}"
            f" | {stats['strings']} str, {stats['numbers']} num, "
            f"{stats['booleans']} bool, {stats['nulls']} null"
            f" | {file_size:,} bytes"
            f"{large_text}"
        )

        self.status_changed.emit(f"JSON loaded | {status}")

    # =================================================================
    # Filter levels
    # =================================================================

    def _reset_filter_levels(self) -> None:
        """Reset filtered-view dropdowns."""

        for combo in self._level_combos:
            self._levels_layout.removeWidget(combo)
            combo.deleteLater()

        self._level_combos.clear()
        self._filtered_view.setPlainText(FILTERED_VIEW_PLACEHOLDER)

        if not self._has_payload:
            return

        first_level_keys = keys_at_path(self._payload, [])

        if first_level_keys:
            self._add_level_combo(first_level_keys)

    def _add_level_combo(self, keys: list[str]) -> None:
        """Add hierarchy-level selector."""

        combo = QComboBox()
        combo.addItem(LEVEL_PLACEHOLDER)
        combo.addItems(keys)
        combo.currentIndexChanged.connect(
            lambda _index, current=combo: self._on_level_changed(current)
        )

        button_index = self._levels_layout.indexOf(self._show_filtered_button)
        self._levels_layout.insertWidget(button_index, combo)
        self._level_combos.append(combo)

    def _current_filter_path(self) -> list[str]:
        """Return selected hierarchy path."""

        path: list[str] = []

        for combo in self._level_combos:
            selected_key = combo.currentText()

            if not selected_key or selected_key == LEVEL_PLACEHOLDER:
                break

            path.append(selected_key)

        return path

    def _on_level_changed(self, combo: QComboBox) -> None:
        """Handle hierarchy-level change."""

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

        if not self._has_payload:
            return

        next_keys = keys_at_path(self._payload, path)

        if next_keys:
            self._add_level_combo(next_keys)

    def _show_filtered(self) -> None:
        """Render selected filtered hierarchy."""

        if not self._has_payload:
            QMessageBox.information(self, MESSAGE_NO_JSON_TITLE, MESSAGE_NO_JSON)
            return

        path = self._current_filter_path()
        result = build_path_filtered_hierarchy_text(self._payload, path)
        self._filtered_view.setPlainText(result)

    # =================================================================
    # Saved Sessions
    # =================================================================

    def _build_current_session(self) -> JsonifySession | None:
        """Build session from current application state."""

        if not self._has_payload:
            QMessageBox.information(self, MESSAGE_NO_JSON_TITLE, MESSAGE_NO_JSON)
            return None

        selected_tab = self._current_category_key()
        if selected_tab == "json":
            selected_tab = (
                f"json:{self._json_tools_tabs.tabText(self._json_tools_tabs.currentIndex())}"
            )

        jsonpath_query = ""
        if hasattr(self._jsonpath_view, "get_query"):
            jsonpath_query = self._jsonpath_view.get_query()

        name = "Untitled Session"
        if self._current_session is not None:
            name = self._current_session.name

        return self._session_service.create_session(
            name=name,
            payload=self._payload,
            selected_tab=selected_tab,
            jsonpath_query=jsonpath_query,
            bookmarks=list(self._bookmarks),
            annotations=dict(self._annotations),
        )

    def save_session(self) -> None:
        """Save current session."""

        if self._current_session_path is None:
            self.save_session_as()
            return

        session = self._build_current_session()
        if session is None:
            return

        if self._current_session is not None:
            session.name = self._current_session.name
            session.created_at = self._current_session.created_at

        try:
            saved_path = self._session_service.save(session, self._current_session_path)
        except SessionError as error:
            QMessageBox.critical(self, "Save Session", str(error))
            return

        self._current_session = session
        self._current_session_path = saved_path
        self.file_path = None
        self._mark_dirty(False)
        self.status_changed.emit(f"Session saved: {saved_path.name}")

    def save_session_as(self) -> None:
        """Save current session to a new file."""

        session = self._build_current_session()
        if session is None:
            return

        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save Jsonify Session",
            session.name,
            "Jsonify Session (*.jsonify)",
        )

        if not file_name:
            return

        session_name = Path(file_name).stem
        session.name = session_name or "Untitled Session"

        try:
            saved_path = self._session_service.save(session, file_name)
        except SessionError as error:
            QMessageBox.critical(self, "Save Session", str(error))
            return

        self._current_session = session
        self._current_session_path = saved_path
        self.file_path = None
        self._mark_dirty(False)
        self.status_changed.emit(f"Session saved: {saved_path.name}")

    def open_session_dialog(self) -> None:
        """Prompt for and open a Jsonify session file into this document."""

        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open Jsonify Session",
            "",
            "Jsonify Session (*.jsonify)",
        )

        if not file_name:
            return

        self.open_session_file(Path(file_name))

    def open_session_file(self, path: Path) -> None:
        """Load a Jsonify session file into this document."""

        try:
            session = self._session_service.load(path)
        except SessionError as error:
            QMessageBox.critical(self, "Open Session", str(error))
            return

        self._current_session = session
        self._current_session_path = path
        self.file_path = None
        self._restore_session(session)

    def _restore_session(self, session: JsonifySession) -> None:
        """Restore saved session."""

        self._payload = session.payload
        self._has_payload = True
        self._document_count = 1

        self._editor.setPlainText(json.dumps(session.payload, indent=2, ensure_ascii=False))

        self._bookmarks = list(session.workspace.bookmarks)
        self._annotations = dict(session.workspace.annotations)

        self._refresh_all_views()

        if session.workspace.jsonpath_query and hasattr(self._jsonpath_view, "set_query"):
            self._jsonpath_view.set_query(session.workspace.jsonpath_query)

        self._restore_selected_tab(session.workspace.selected_tab)
        self._mark_dirty(False)
        self.status_changed.emit(f"Session loaded: {session.name}")

    # Maps session `selected_tab` values saved before the activity-bar
    # redesign onto the current category (and, for JSON sub-views, the
    # sub-tab name within the "JSON" category).
    _LEGACY_TAB_NAMES = {
        "Normal View": "json:Normal View",
        "Hierarchy View": "json:Hierarchy View",
        "Filtered View": "json:Filtered View",
        "Graph": "json:Graph",
        "JSON Diff": "diff",
        "JSONPath": "query",
        "Schema": "schema",
        "Data Masking": "mask",
        "API Viewer": "api",
        "Export": "export",
    }

    def _restore_selected_tab(self, tab_name: str) -> None:
        """Restore the selected activity-bar category (and JSON sub-tab)."""

        if not tab_name:
            return

        tab_name = self._LEGACY_TAB_NAMES.get(tab_name, tab_name)

        if tab_name.startswith("json:"):
            self._select_category("json")
            sub_tab_name = tab_name.split(":", 1)[1]

            for index in range(self._json_tools_tabs.count()):
                if self._json_tools_tabs.tabText(index) == sub_tab_name:
                    self._json_tools_tabs.setCurrentIndex(index)
                    return

            return

        self._select_category(tab_name)
