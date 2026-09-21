"""Code generation user-interface widget."""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from jsonify.core.codegen import SUPPORTED_LANGUAGES, generate_code
from jsonify.core.models import JSONValue
from jsonify.ui.constants import MONOSPACE_FONT

_LANGUAGE_LABELS = {
    "csharp": "C#",
    "java": "Java",
    "typescript": "TypeScript",
    "python": "Python",
    "go": "Go",
    "kotlin": "Kotlin",
}


class CodeGenView(QWidget):
    """Widget for generating typed models from the loaded JSON payload."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._payload: JSONValue | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Code Generator")
        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        layout.addWidget(title)

        description = QLabel("Generate a typed model from the currently loaded JSON payload.")
        description.setWordWrap(True)
        layout.addWidget(description)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Language:"))

        self._language_combo = QComboBox()
        for language in SUPPORTED_LANGUAGES:
            self._language_combo.addItem(_LANGUAGE_LABELS[language], language)
        controls.addWidget(self._language_combo)

        controls.addWidget(QLabel("Root type name:"))
        self._root_name_input = QLineEdit("Root")
        self._root_name_input.setMaximumWidth(160)
        controls.addWidget(self._root_name_input)

        generate_button = QPushButton("Generate")
        generate_button.clicked.connect(self._generate)
        controls.addWidget(generate_button)

        copy_button = QPushButton("Copy")
        copy_button.clicked.connect(self._copy_output)
        controls.addWidget(copy_button)

        controls.addStretch(1)
        layout.addLayout(controls)

        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setFont(QFont(MONOSPACE_FONT))
        layout.addWidget(self._output, 1)

    def set_payload(self, payload: JSONValue) -> None:
        """Set the JSON payload to generate code from."""

        self._payload = payload
        self._output.clear()

    def clear_payload(self) -> None:
        """Clear the loaded JSON payload."""

        self._payload = None
        self._output.clear()

    def _generate(self) -> None:
        if self._payload is None:
            QMessageBox.warning(
                self, "No JSON Loaded", "Load a JSON payload before generating code."
            )
            return

        language = self._language_combo.currentData()
        root_name = self._root_name_input.text().strip() or "Root"

        code = generate_code(self._payload, language, root_name=root_name)
        self._output.setPlainText(code)

    def _copy_output(self) -> None:
        text = self._output.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
