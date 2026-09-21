"""Batch processing dialog: validate/format/mask/convert many files."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from jsonify.services.batch_service import JSON_SUFFIXES, OPERATIONS, BatchService
from jsonify.ui.constants import MONOSPACE_FONT


class BatchDialog(QDialog):
    """Pick files, pick an operation, run it on all of them."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Batch Process")
        self.resize(720, 620)

        self._service = BatchService()

        layout = QVBoxLayout(self)

        operation_row = QHBoxLayout()
        operation_row.addWidget(QLabel("Operation:"))
        self._operation = QComboBox()
        for name, (_suffix, description) in OPERATIONS.items():
            self._operation.addItem(f"{name} — {description}", name)
        operation_row.addWidget(self._operation, 1)
        layout.addLayout(operation_row)

        layout.addWidget(QLabel("Files"))
        self._files = QListWidget()
        self._files.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout.addWidget(self._files, 2)

        file_buttons = QHBoxLayout()
        add_files = QPushButton("Add Files...")
        add_files.clicked.connect(self._add_files)
        file_buttons.addWidget(add_files)
        add_folder = QPushButton("Add Folder...")
        add_folder.clicked.connect(self._add_folder)
        file_buttons.addWidget(add_folder)
        remove = QPushButton("Remove Selected")
        remove.clicked.connect(self._remove_selected)
        file_buttons.addWidget(remove)
        file_buttons.addStretch(1)
        layout.addLayout(file_buttons)

        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Output folder:"))
        self._output_dir = QLineEdit()
        self._output_dir.setPlaceholderText("(next to each source file)")
        output_row.addWidget(self._output_dir, 1)
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse_output)
        output_row.addWidget(browse)
        layout.addLayout(output_row)

        options_row = QHBoxLayout()
        options_row.addWidget(QLabel("Indent:"))
        self._indent = QSpinBox()
        self._indent.setRange(0, 8)
        self._indent.setValue(2)
        options_row.addWidget(self._indent)
        self._in_place = QCheckBox("Overwrite originals (JSON outputs only)")
        options_row.addWidget(self._in_place)
        options_row.addStretch(1)
        layout.addLayout(options_row)

        run_row = QHBoxLayout()
        run_row.addStretch(1)
        self._run_button = QPushButton("Run")
        self._run_button.clicked.connect(self._run)
        run_row.addWidget(self._run_button)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        run_row.addWidget(close)
        layout.addLayout(run_row)

        self._results = QPlainTextEdit()
        self._results.setReadOnly(True)
        self._results.setFont(QFont(MONOSPACE_FONT))
        self._results.setPlaceholderText("Results appear here.")
        layout.addWidget(self._results, 2)

    # -----------------------------------------------------------------

    def add_paths(self, paths: list[Path]) -> None:
        """Add files to the list (duplicates ignored)."""

        existing = {self._files.item(i).text() for i in range(self._files.count())}
        for path in paths:
            if str(path) not in existing:
                self._files.addItem(str(path))
                existing.add(str(path))

    def _add_files(self) -> None:
        patterns = " ".join(f"*{suffix}" for suffix in JSON_SUFFIXES)
        names, _ = QFileDialog.getOpenFileNames(
            self, "Add JSON Files", "", f"JSON Files ({patterns});;All Files (*)"
        )
        self.add_paths([Path(name) for name in names])

    def _add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Add Folder")
        if folder:
            self.add_paths(BatchService.expand_inputs([folder]))

    def _remove_selected(self) -> None:
        for item in self._files.selectedItems():
            self._files.takeItem(self._files.row(item))

    def _browse_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Output Folder")
        if folder:
            self._output_dir.setText(folder)

    def _run(self) -> None:
        paths = [Path(self._files.item(i).text()) for i in range(self._files.count())]

        if not paths:
            self._results.setPlainText("Add at least one file first.")
            return

        output_text = self._output_dir.text().strip()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            results = self._service.process_files(
                paths,
                self._operation.currentData(),
                output_dir=Path(output_text) if output_text else None,
                indent=self._indent.value(),
                in_place=self._in_place.isChecked(),
            )
        finally:
            QApplication.restoreOverrideCursor()

        lines = []
        for result in results:
            target = f"  ->  {result.output_path}" if result.output_path else ""
            detail = "" if result.ok else f"  ({result.message})"
            lines.append(f"{'OK  ' if result.ok else 'FAIL'}  {result.path}{target}{detail}")

        failed = sum(1 for r in results if not r.ok)
        lines += ["", f"{len(results) - failed} of {len(results)} succeeded."]
        self._results.setPlainText("\n".join(lines))
