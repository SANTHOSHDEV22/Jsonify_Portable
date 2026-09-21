"""OpenAPI response validation user-interface widget."""

from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from jsonify.core.models import JSONValue
from jsonify.core.openapi import OpenApiError
from jsonify.services.openapi_service import JsonSchemaError, OpenApiService
from jsonify.services.schema_service import SchemaValidationError, SchemaValidationResult
from jsonify.ui.constants import MONOSPACE_FONT


class OpenApiView(QWidget):
    """Widget for validating a JSON payload against an OpenAPI response schema."""

    def __init__(
        self,
        openapi_service: OpenApiService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._openapi_service = openapi_service if openapi_service is not None else OpenApiService()
        self._payload: JSONValue | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("OpenAPI Response Validation")
        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        layout.addWidget(title)

        description = QLabel(
            "Validate the currently loaded JSON payload against one operation's "
            "response schema in an OpenAPI document."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        payload_panel = QWidget()
        payload_layout = QVBoxLayout(payload_panel)
        payload_label = QLabel("Loaded JSON")
        payload_layout.addWidget(payload_label)
        self._payload_editor = QPlainTextEdit()
        self._payload_editor.setReadOnly(True)
        self._payload_editor.setFont(QFont(MONOSPACE_FONT))
        payload_layout.addWidget(self._payload_editor)
        splitter.addWidget(payload_panel)

        doc_panel = QWidget()
        doc_layout = QVBoxLayout(doc_panel)
        doc_layout.addWidget(QLabel("OpenAPI Document (JSON)"))
        self._doc_editor = QPlainTextEdit()
        self._doc_editor.setPlaceholderText("Paste an OpenAPI 3.x document here...")
        self._doc_editor.setFont(QFont(MONOSPACE_FONT))
        doc_layout.addWidget(self._doc_editor)
        splitter.addWidget(doc_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        operation_row = QHBoxLayout()
        operation_row.addWidget(QLabel("Path:"))
        self._path_input = QLineEdit()
        self._path_input.setPlaceholderText("/users/{id}")
        operation_row.addWidget(self._path_input, 1)

        operation_row.addWidget(QLabel("Method:"))
        self._method_combo = QComboBox()
        self._method_combo.addItems(["get", "post", "put", "patch", "delete"])
        operation_row.addWidget(self._method_combo)

        operation_row.addWidget(QLabel("Status:"))
        self._status_input = QLineEdit("200")
        self._status_input.setMaximumWidth(60)
        operation_row.addWidget(self._status_input)

        validate_button = QPushButton("Validate")
        validate_button.clicked.connect(self._validate)
        operation_row.addWidget(validate_button)

        layout.addLayout(operation_row)

        self._status_label = QLabel("Load JSON and paste an OpenAPI document.")
        layout.addWidget(self._status_label)

        self._results_table = QTableWidget()
        self._results_table.setColumnCount(3)
        self._results_table.setHorizontalHeaderLabels(["Path", "Message", "Rule"])
        self._results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self._results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._results_table, 1)

    def set_payload(self, payload: JSONValue) -> None:
        """Set the JSON payload to validate."""

        self._payload = payload
        self._payload_editor.setPlainText(json.dumps(payload, indent=2, ensure_ascii=False))
        self._results_table.setRowCount(0)

    def clear_payload(self) -> None:
        """Clear the loaded JSON payload."""

        self._payload = None
        self._payload_editor.clear()
        self._results_table.setRowCount(0)

    def _validate(self) -> None:
        if self._payload is None:
            QMessageBox.warning(self, "No JSON Loaded", "Load a JSON payload before validation.")
            return

        doc_text = self._doc_editor.toPlainText().strip()
        if not doc_text:
            QMessageBox.warning(self, "OpenAPI", "Paste an OpenAPI document first.")
            return

        try:
            openapi_doc = json.loads(doc_text)
        except json.JSONDecodeError as error:
            QMessageBox.critical(self, "Invalid OpenAPI Document", str(error))
            return

        if not isinstance(openapi_doc, dict):
            QMessageBox.critical(
                self, "Invalid OpenAPI Document", "The document must be a JSON object."
            )
            return

        try:
            result = self._openapi_service.validate_response(
                self._payload,
                openapi_doc,
                path=self._path_input.text().strip(),
                method=self._method_combo.currentText(),
                status=self._status_input.text().strip() or "200",
            )
        except (OpenApiError, JsonSchemaError) as error:
            QMessageBox.critical(self, "OpenAPI Validation", str(error))
            return

        self._display_result(result)

    def _display_result(self, result: SchemaValidationResult) -> None:
        self._results_table.setRowCount(0)

        if result.valid:
            self._status_label.setText("✓ Response matches the OpenAPI schema.")
            self._status_label.setStyleSheet("color: #4EC9B0; font-weight: bold;")
            return

        self._status_label.setText(f"✗ {len(result.errors)} validation error(s).")
        self._status_label.setStyleSheet("color: #F44747; font-weight: bold;")

        self._results_table.setRowCount(len(result.errors))
        for row, error in enumerate(result.errors):
            self._set_error_row(row, error)

    def _set_error_row(self, row: int, error: SchemaValidationError) -> None:
        self._results_table.setItem(row, 0, QTableWidgetItem(error.path))
        self._results_table.setItem(row, 1, QTableWidgetItem(error.message))
        self._results_table.setItem(row, 2, QTableWidgetItem(error.validator))
