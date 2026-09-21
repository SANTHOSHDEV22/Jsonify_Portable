"""JSON <-> YAML/XML/CSV conversion user-interface widget."""

from __future__ import annotations

import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from jsonify.core.converters import (
    ConversionError,
    csv_to_json,
    json_to_csv,
    json_to_xml,
    json_to_yaml,
    xml_to_json,
    yaml_to_json,
)
from jsonify.core.models import JSONValue
from jsonify.core.plugins import get_registry
from jsonify.ui.constants import MONOSPACE_FONT

_FORMATS = ("YAML", "XML", "CSV")


class ConvertersView(QWidget):
    """Widget for converting between JSON and YAML/XML/CSV."""

    payload_loaded = Signal(object)
    """Emitted with a parsed JSON value when "Load into Jsonify" is clicked."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._payload: JSONValue | None = None
        self._converted_payload: JSONValue | None = None
        self._has_converted_payload = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Format Converters")
        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        layout.addWidget(title)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._create_export_panel())
        splitter.addWidget(self._create_import_panel())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

    def _create_export_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        layout.addWidget(QLabel("JSON → Other Format (uses the loaded payload)"))

        row = QHBoxLayout()
        row.addWidget(QLabel("To:"))
        self._export_format = QComboBox()
        self._export_format.addItems(
            [*_FORMATS, *(n for n, c in get_registry().converters.items() if c.from_json)]
        )
        row.addWidget(self._export_format)

        convert_button = QPushButton("Convert")
        convert_button.clicked.connect(self._convert_from_json)
        row.addWidget(convert_button)

        copy_button = QPushButton("Copy")
        copy_button.clicked.connect(self._copy_export_output)
        row.addWidget(copy_button)
        row.addStretch(1)

        layout.addLayout(row)

        self._export_output = QPlainTextEdit()
        self._export_output.setReadOnly(True)
        self._export_output.setFont(QFont(MONOSPACE_FONT))
        layout.addWidget(self._export_output, 1)

        return panel

    def _create_import_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        layout.addWidget(QLabel("Other Format → JSON"))

        row = QHBoxLayout()
        row.addWidget(QLabel("From:"))
        self._import_format = QComboBox()
        self._import_format.addItems(
            [*_FORMATS, *(n for n, c in get_registry().converters.items() if c.to_json)]
        )
        row.addWidget(self._import_format)

        convert_button = QPushButton("Convert")
        convert_button.clicked.connect(self._convert_to_json)
        row.addWidget(convert_button)

        self._load_button = QPushButton("Load into Jsonify")
        self._load_button.setEnabled(False)
        self._load_button.clicked.connect(self._load_into_jsonify)
        row.addWidget(self._load_button)
        row.addStretch(1)

        layout.addLayout(row)

        self._import_input = QPlainTextEdit()
        self._import_input.setPlaceholderText("Paste YAML, XML, or CSV here...")
        self._import_input.setFont(QFont(MONOSPACE_FONT))
        layout.addWidget(self._import_input, 1)

        self._import_output = QPlainTextEdit()
        self._import_output.setReadOnly(True)
        self._import_output.setFont(QFont(MONOSPACE_FONT))
        layout.addWidget(self._import_output, 1)

        return panel

    def set_payload(self, payload: JSONValue) -> None:
        """Set the JSON payload to convert from."""

        self._payload = payload
        self._export_output.clear()

    def clear_payload(self) -> None:
        """Clear the loaded JSON payload."""

        self._payload = None
        self._export_output.clear()

    def _convert_from_json(self) -> None:
        if self._payload is None:
            QMessageBox.warning(self, "No JSON Loaded", "Load a JSON payload first.")
            return

        target = self._export_format.currentText()

        try:
            plugin = get_registry().converters.get(target)
            if plugin is not None and plugin.from_json is not None:
                text = plugin.from_json(self._payload)
            elif target == "YAML":
                text = json_to_yaml(self._payload)
            elif target == "XML":
                text = json_to_xml(self._payload)
            else:
                text = json_to_csv(self._payload)
        except (ConversionError, ValueError) as error:
            QMessageBox.critical(self, "Conversion Failed", str(error))
            return

        self._export_output.setPlainText(text)

    def _copy_export_output(self) -> None:
        text = self._export_output.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def _convert_to_json(self) -> None:
        source = self._import_format.currentText()
        text = self._import_input.toPlainText()

        if not text.strip():
            QMessageBox.warning(self, "Convert to JSON", "Paste some content first.")
            return

        try:
            plugin = get_registry().converters.get(source)
            if plugin is not None and plugin.to_json is not None:
                payload = plugin.to_json(text)
            elif source == "YAML":
                payload = yaml_to_json(text)
            elif source == "XML":
                payload = xml_to_json(text)
            else:
                payload = csv_to_json(text)
        except (ConversionError, ValueError) as error:
            QMessageBox.critical(self, "Conversion Failed", str(error))
            self._load_button.setEnabled(False)
            return

        self._import_output.setPlainText(json.dumps(payload, indent=2, ensure_ascii=False))
        self._converted_payload = payload
        self._has_converted_payload = True
        self._load_button.setEnabled(True)

    def _load_into_jsonify(self) -> None:
        if self._has_converted_payload:
            self.payload_loaded.emit(self._converted_payload)
