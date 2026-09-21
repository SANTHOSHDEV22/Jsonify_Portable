"""JSONPath query user-interface widget."""

from __future__ import annotations

import json

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from jsonify.core.models import JSONValue
from jsonify.services.jsonpath_service import (
    JsonPathQueryError,
    JsonPathResult,
    JsonPathService,
)
from jsonify.ui.constants import MONOSPACE_FONT


class JsonPathView(QWidget):
    """Widget for executing JSONPath queries."""

    _EXAMPLES = (
        "$",
        "$.*",
        "$..name",
        "$.users[*]",
        "$.users[*].name",
        "$.departments[*].employees[*].name",
        "$..*",
    )

    def __init__(
        self,
        jsonpath_service: JsonPathService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._jsonpath_service = (
            jsonpath_service if jsonpath_service is not None else JsonPathService()
        )

        self._payload: JSONValue | None = None
        self._results: list[JsonPathResult] = []

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the JSONPath interface."""

        layout = QVBoxLayout(self)

        title = QLabel("JSONPath Query")

        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSize(12)

        title.setFont(title_font)

        layout.addWidget(title)

        description = QLabel("Query the currently loaded JSON payload using JSONPath expressions.")

        description.setWordWrap(True)

        layout.addWidget(description)

        query_layout = QHBoxLayout()

        query_label = QLabel("JSONPath:")

        self._query_combo = QComboBox()
        self._query_combo.setEditable(True)

        self._query_combo.addItems(self._EXAMPLES)

        self._query_combo.setCurrentText("$")

        self._query_combo.setMinimumWidth(400)

        self._run_button = QPushButton("Run Query")
        self._run_button.clicked.connect(self._run_query)

        clear_button = QPushButton("Clear Results")
        clear_button.clicked.connect(self._clear_results)

        query_layout.addWidget(query_label)
        query_layout.addWidget(
            self._query_combo,
            1,
        )
        query_layout.addWidget(self._run_button)
        query_layout.addWidget(clear_button)

        layout.addLayout(query_layout)

        examples = QLabel(
            "Examples: $.users[*].name   |   $..name   |   $.departments[*].employees[*]"
        )

        layout.addWidget(examples)

        self._status_label = QLabel("Load a JSON payload to begin.")

        layout.addWidget(self._status_label)

        self._results_table = QTableWidget()

        self._results_table.setColumnCount(3)

        self._results_table.setHorizontalHeaderLabels(
            [
                "#",
                "Path",
                "Value",
            ]
        )

        self._results_table.setAlternatingRowColors(True)

        self._results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        self._results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        header = self._results_table.horizontalHeader()

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )

        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.Stretch,
        )

        layout.addWidget(
            self._results_table,
            1,
        )

        value_row = QHBoxLayout()

        value_label = QLabel("Selected Value")

        value_font = value_label.font()
        value_font.setBold(True)

        value_label.setFont(value_font)

        value_row.addWidget(value_label)
        value_row.addStretch(1)

        copy_path_button = QPushButton("Copy Path")
        copy_path_button.clicked.connect(self._copy_selected_path)
        value_row.addWidget(copy_path_button)

        copy_value_button = QPushButton("Copy Value")
        copy_value_button.clicked.connect(self._copy_selected_value)
        value_row.addWidget(copy_value_button)

        copy_all_button = QPushButton("Copy All Results (JSON)")
        copy_all_button.clicked.connect(self._copy_all_results)
        value_row.addWidget(copy_all_button)

        layout.addLayout(value_row)

        self._value_preview = QPlainTextEdit()

        self._value_preview.setReadOnly(True)

        self._value_preview.setMaximumHeight(180)

        self._value_preview.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self._value_preview.setFont(QFont(MONOSPACE_FONT))

        layout.addWidget(self._value_preview)

        self._results_table.itemSelectionChanged.connect(self._show_selected_value)

        self._query_combo.lineEdit().returnPressed.connect(self._run_query)

    def set_payload(
        self,
        payload: JSONValue,
    ) -> None:
        """Set the JSON payload queried by this widget."""

        self._payload = payload

        self._clear_results()

        self._status_label.setText("JSON loaded. Enter a JSONPath expression.")

    def clear_payload(self) -> None:
        """Remove the currently loaded JSON payload."""

        self._payload = None

        self._clear_results()

        self._status_label.setText("Load a JSON payload to begin.")

    def _run_query(self) -> None:
        """Execute the current JSONPath query."""

        if self._payload is None:
            QMessageBox.warning(
                self,
                "No JSON Loaded",
                "Load a JSON payload before running a JSONPath query.",
            )
            return

        expression = self._query_combo.currentText().strip()

        if not expression:
            QMessageBox.warning(
                self,
                "JSONPath",
                "Enter a JSONPath expression.",
            )
            return

        try:
            results = self._jsonpath_service.query(
                payload=self._payload,
                expression=expression,
            )
        except JsonPathQueryError as error:
            QMessageBox.critical(
                self,
                "Invalid JSONPath",
                str(error),
            )
            return

        self._remember_query(expression)
        self._display_results(results)

    def _remember_query(self, expression: str) -> None:
        """Add a successfully run query to the history dropdown."""

        existing_index = self._query_combo.findText(expression)
        if existing_index >= 0:
            self._query_combo.removeItem(existing_index)

        self._query_combo.insertItem(0, expression)
        self._query_combo.setCurrentIndex(0)

    def _display_results(
        self,
        results: list[JsonPathResult],
    ) -> None:
        """Display JSONPath results."""

        self._results_table.setRowCount(0)
        self._value_preview.clear()
        self._results = results

        if not results:
            self._status_label.setText("No matches found.")
            return

        self._results_table.setRowCount(len(results))

        for row, result in enumerate(results):
            number_item = QTableWidgetItem(str(row + 1))

            path_item = QTableWidgetItem(result.path)

            value_item = QTableWidgetItem(self._display_value(result.value))

            value_item.setData(
                256,
                result.value,
            )

            self._results_table.setItem(
                row,
                0,
                number_item,
            )

            self._results_table.setItem(
                row,
                1,
                path_item,
            )

            self._results_table.setItem(
                row,
                2,
                value_item,
            )

        self._status_label.setText(f"{len(results)} match(es) found.")

        if results:
            self._results_table.selectRow(0)

    def _show_selected_value(self) -> None:
        """Show the complete selected JSONPath value."""

        selected_rows = self._results_table.selectionModel().selectedRows()

        if not selected_rows:
            self._value_preview.clear()
            return

        row = selected_rows[0].row()

        value_item = self._results_table.item(
            row,
            2,
        )

        if value_item is None:
            self._value_preview.clear()
            return

        value = value_item.data(256)

        self._value_preview.setPlainText(self._pretty_value(value))

    def _clear_results(self) -> None:
        """Clear current query results."""

        self._results_table.setRowCount(0)
        self._value_preview.clear()
        self._results = []

    def _selected_row(self) -> int | None:
        selected_rows = self._results_table.selectionModel().selectedRows()
        return selected_rows[0].row() if selected_rows else None

    def _copy_selected_path(self) -> None:
        row = self._selected_row()
        if row is None or row >= len(self._results):
            return
        QApplication.clipboard().setText(self._results[row].path)

    def _copy_selected_value(self) -> None:
        row = self._selected_row()
        if row is None or row >= len(self._results):
            return
        QApplication.clipboard().setText(self._pretty_value(self._results[row].value))

    def _copy_all_results(self) -> None:
        if not self._results:
            return
        payload = [{"path": r.path, "value": r.value} for r in self._results]
        QApplication.clipboard().setText(json.dumps(payload, indent=2, ensure_ascii=False))

    @staticmethod
    def _display_value(
        value: JSONValue,
    ) -> str:
        """Return a compact display value."""

        if value is None:
            return "null"

        if isinstance(value, bool):
            return "true" if value else "false"

        if isinstance(value, str):
            return value

        if isinstance(value, (dict, list)):
            return json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
            )

        return str(value)

    @staticmethod
    def _pretty_value(
        value: JSONValue,
    ) -> str:
        """Return a formatted JSON representation."""

        return json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
        )

    def get_query(self) -> str:
        """Return the current JSONPath expression."""

        return self._query_combo.currentText().strip()

    def set_query(
        self,
        expression: str,
    ) -> None:
        """Restore a JSONPath expression."""

        self._query_combo.setCurrentText(expression)
