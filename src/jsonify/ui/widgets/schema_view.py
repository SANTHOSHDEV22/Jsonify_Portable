"""JSON Schema validation user-interface widget."""

from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
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
from jsonify.services.schema_service import (
    JsonSchemaError,
    SchemaService,
    SchemaValidationError,
    SchemaValidationResult,
)
from jsonify.ui.constants import MONOSPACE_FONT


class SchemaView(QWidget):
    """Widget for validating JSON against a JSON Schema."""

    def __init__(
        self,
        schema_service: SchemaService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._schema_service = schema_service if schema_service is not None else SchemaService()

        self._payload: JSONValue | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the Schema Validation interface."""

        layout = QVBoxLayout(self)

        title = QLabel("JSON Schema Validation")

        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSize(12)

        title.setFont(title_font)

        layout.addWidget(title)

        description = QLabel("Validate the currently loaded JSON payload against a JSON Schema.")

        description.setWordWrap(True)

        layout.addWidget(description)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        payload_panel = self._create_payload_panel()
        schema_panel = self._create_schema_panel()

        splitter.addWidget(payload_panel)
        splitter.addWidget(schema_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, 1)

        controls = QHBoxLayout()

        self._validate_button = QPushButton("Validate")

        self._validate_button.clicked.connect(self._validate)

        example_button = QPushButton("Example Schema")

        example_button.clicked.connect(self._load_example_schema)

        generate_button = QPushButton("Generate from Sample")
        generate_button.setToolTip("Infer a JSON Schema from the currently loaded JSON payload")
        generate_button.clicked.connect(self._generate_schema_from_payload)

        clear_button = QPushButton("Clear Schema")

        clear_button.clicked.connect(self._clear_schema)

        self._status_label = QLabel("Load JSON and enter a schema.")

        controls.addWidget(self._validate_button)

        controls.addWidget(example_button)

        controls.addWidget(generate_button)

        controls.addWidget(clear_button)

        controls.addSpacing(15)

        controls.addWidget(self._status_label)

        controls.addStretch()

        layout.addLayout(controls)

        errors_label = QLabel("Validation Results")

        errors_font = errors_label.font()
        errors_font.setBold(True)

        errors_label.setFont(errors_font)

        layout.addWidget(errors_label)

        self._results_table = QTableWidget()

        self._results_table.setColumnCount(5)

        self._results_table.setHorizontalHeaderLabels(
            [
                "Path",
                "Rule",
                "Message",
                "Expected",
                "Actual",
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
            QHeaderView.ResizeMode.ResizeToContents,
        )

        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.Stretch,
        )

        header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.Stretch,
        )

        header.setSectionResizeMode(
            4,
            QHeaderView.ResizeMode.Stretch,
        )

        layout.addWidget(
            self._results_table,
            1,
        )

    def _create_payload_panel(self) -> QWidget:
        """Create the read-only payload panel."""

        panel = QWidget()

        layout = QVBoxLayout(panel)

        label = QLabel("Loaded JSON")

        label_font = label.font()
        label_font.setBold(True)

        label.setFont(label_font)

        self._payload_editor = QPlainTextEdit()

        self._payload_editor.setReadOnly(True)

        self._payload_editor.setPlaceholderText("Load JSON from Jsonify first.")

        self._payload_editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self._payload_editor.setFont(QFont(MONOSPACE_FONT))

        layout.addWidget(label)
        layout.addWidget(self._payload_editor)

        return panel

    def _create_schema_panel(self) -> QWidget:
        """Create the editable JSON Schema panel."""

        panel = QWidget()

        layout = QVBoxLayout(panel)

        label = QLabel("JSON Schema")

        label_font = label.font()
        label_font.setBold(True)

        label.setFont(label_font)

        self._schema_editor = QPlainTextEdit()

        self._schema_editor.setPlaceholderText("Paste a JSON Schema here...")

        self._schema_editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self._schema_editor.setFont(QFont(MONOSPACE_FONT))

        layout.addWidget(label)
        layout.addWidget(self._schema_editor)

        return panel

    def set_payload(
        self,
        payload: JSONValue,
    ) -> None:
        """Set the JSON payload to validate."""

        self._payload = payload

        self._payload_editor.setPlainText(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            )
        )

        self._results_table.setRowCount(0)

        self._status_label.setText("JSON loaded. Enter a schema and validate.")

    def clear_payload(self) -> None:
        """Clear the loaded JSON payload."""

        self._payload = None

        self._payload_editor.clear()

        self._results_table.setRowCount(0)

        self._status_label.setText("Load JSON and enter a schema.")

    def _validate(self) -> None:
        """Validate the loaded payload."""

        if self._payload is None:
            QMessageBox.warning(
                self,
                "No JSON Loaded",
                "Load a JSON payload before validation.",
            )
            return

        schema_text = self._schema_editor.toPlainText().strip()

        if not schema_text:
            QMessageBox.warning(
                self,
                "Schema Validation",
                "Enter a JSON Schema before validating.",
            )
            return

        try:
            parsed_schema = json.loads(schema_text)
        except json.JSONDecodeError as error:
            QMessageBox.critical(
                self,
                "Invalid JSON Schema",
                (
                    f"The schema contains invalid JSON.\n\n"
                    f"{error.msg}\n"
                    f"Line: {error.lineno}\n"
                    f"Column: {error.colno}"
                ),
            )
            return

        if not isinstance(
            parsed_schema,
            dict,
        ):
            QMessageBox.critical(
                self,
                "Invalid JSON Schema",
                "The JSON Schema must be a JSON object.",
            )
            return

        try:
            result = self._schema_service.validate(
                payload=self._payload,
                schema=parsed_schema,
            )
        except JsonSchemaError as error:
            QMessageBox.critical(
                self,
                "Invalid JSON Schema",
                str(error),
            )
            return

        self._display_result(result)

    def _display_result(
        self,
        result: SchemaValidationResult,
    ) -> None:
        """Display validation result."""

        self._results_table.setRowCount(0)

        if result.valid:
            self._status_label.setText("✓ JSON is valid against the schema.")

            self._status_label.setStyleSheet("color: #4EC9B0; font-weight: bold;")

            return

        self._status_label.setText(f"✗ Validation failed: {len(result.errors)} error(s).")

        self._status_label.setStyleSheet("color: #F44747; font-weight: bold;")

        self._results_table.setRowCount(len(result.errors))

        for row, error in enumerate(result.errors):
            self._set_error_row(
                row,
                error,
            )

    def _set_error_row(
        self,
        row: int,
        error: SchemaValidationError,
    ) -> None:
        """Insert one validation error."""

        path_item = QTableWidgetItem(error.path)

        rule_item = QTableWidgetItem(error.validator)

        message_item = QTableWidgetItem(error.message)

        expected_item = QTableWidgetItem(self._display_value(error.expected))

        actual_item = QTableWidgetItem(self._display_value(error.actual))

        error_color = QColor("#F44747")

        path_item.setForeground(error_color)

        path_font = path_item.font()
        path_font.setBold(True)

        path_item.setFont(path_font)

        self._results_table.setItem(
            row,
            0,
            path_item,
        )

        self._results_table.setItem(
            row,
            1,
            rule_item,
        )

        self._results_table.setItem(
            row,
            2,
            message_item,
        )

        self._results_table.setItem(
            row,
            3,
            expected_item,
        )

        self._results_table.setItem(
            row,
            4,
            actual_item,
        )

    def _load_example_schema(self) -> None:
        """Load a useful example JSON Schema."""

        example = {
            "$schema": ("https://json-schema.org/draft/2020-12/schema"),
            "type": "object",
            "properties": {
                "id": {
                    "type": "integer",
                },
                "name": {
                    "type": "string",
                    "minLength": 1,
                },
                "email": {
                    "type": "string",
                },
                "active": {
                    "type": "boolean",
                },
            },
            "required": [
                "id",
                "name",
            ],
            "additionalProperties": True,
        }

        self._schema_editor.setPlainText(
            json.dumps(
                example,
                indent=2,
            )
        )

    def _generate_schema_from_payload(self) -> None:
        """Fill the schema editor with a schema inferred from the loaded payload."""

        if self._payload is None:
            QMessageBox.warning(
                self, "No JSON Loaded", "Load a JSON payload before generating a schema."
            )
            return

        schema = self._schema_service.generate_schema(self._payload)
        self._schema_editor.setPlainText(json.dumps(schema, indent=2, ensure_ascii=False))
        self._status_label.setText("Schema generated from the loaded payload.")
        self._status_label.setStyleSheet("")

    def _clear_schema(self) -> None:
        """Clear schema and validation results."""

        self._schema_editor.clear()

        self._results_table.setRowCount(0)

        self._status_label.setStyleSheet("")

        if self._payload is None:
            self._status_label.setText("Load JSON and enter a schema.")
        else:
            self._status_label.setText("JSON loaded. Enter a schema and validate.")

    @staticmethod
    def _display_value(
        value: Any,
    ) -> str:
        """Convert a value to readable JSON text."""

        if value is None:
            return "null"

        if isinstance(value, bool):
            return "true" if value else "false"

        if isinstance(
            value,
            (dict, list),
        ):
            return json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
            )

        return str(value)
