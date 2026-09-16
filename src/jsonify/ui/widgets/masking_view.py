"""Sensitive-data masking user-interface widget."""

from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from jsonify.core.models import JSONValue
from jsonify.services.masking_service import (
    MaskingService,
)
from jsonify.ui.constants import MONOSPACE_FONT


class MaskingView(QWidget):
    """Widget for masking sensitive fields in JSON."""

    def __init__(
        self,
        masking_service: MaskingService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._masking_service = (
            masking_service
            if masking_service is not None
            else MaskingService()
        )

        self._payload: JSONValue | None = None
        self._masked_payload: JSONValue | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the sensitive-data masking interface."""

        layout = QVBoxLayout(self)

        title = QLabel(
            "Sensitive-data Masking"
        )

        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSize(12)

        title.setFont(title_font)

        layout.addWidget(title)

        description = QLabel(
            "Select fields that should be masked before "
            "sharing or exporting JSON. "
            "The original loaded JSON is never modified."
        )

        description.setWordWrap(True)

        layout.addWidget(description)

        splitter = QSplitter(
            Qt.Orientation.Horizontal
        )

        controls_panel = (
            self._create_controls_panel()
        )

        preview_panel = (
            self._create_preview_panel()
        )

        splitter.addWidget(
            controls_panel
        )

        splitter.addWidget(
            preview_panel
        )

        splitter.setStretchFactor(
            0,
            0,
        )

        splitter.setStretchFactor(
            1,
            1,
        )

        splitter.setSizes(
            [320, 800]
        )

        layout.addWidget(
            splitter,
            1,
        )

        button_layout = QHBoxLayout()

        self._mask_button = QPushButton(
            "Mask Selected Fields"
        )

        self._mask_button.clicked.connect(
            self._mask_selected
        )

        detect_button = QPushButton(
            "Detect Sensitive Fields"
        )

        detect_button.clicked.connect(
            self._detect_sensitive
        )

        select_all_button = QPushButton(
            "Select All"
        )

        select_all_button.clicked.connect(
            self._select_all
        )

        clear_selection_button = QPushButton(
            "Clear Selection"
        )

        clear_selection_button.clicked.connect(
            self._clear_selection
        )

        copy_button = QPushButton(
            "Copy Masked JSON"
        )

        copy_button.clicked.connect(
            self._copy_masked_json
        )

        button_layout.addWidget(
            self._mask_button
        )

        button_layout.addWidget(
            detect_button
        )

        button_layout.addWidget(
            select_all_button
        )

        button_layout.addWidget(
            clear_selection_button
        )

        button_layout.addStretch()

        button_layout.addWidget(
            copy_button
        )

        layout.addLayout(
            button_layout
        )

        self._status_label = QLabel(
            "Load a JSON payload to begin."
        )

        layout.addWidget(
            self._status_label
        )

    def _create_controls_panel(
        self,
    ) -> QWidget:
        """Create field-selection controls."""

        panel = QWidget()

        layout = QVBoxLayout(panel)

        fields_label = QLabel(
            "Fields"
        )

        fields_font = fields_label.font()
        fields_font.setBold(True)

        fields_label.setFont(
            fields_font
        )

        layout.addWidget(
            fields_label
        )

        help_label = QLabel(
            "Check the fields that should be masked."
        )

        help_label.setWordWrap(True)

        layout.addWidget(
            help_label
        )

        self._field_list = QListWidget()

        layout.addWidget(
            self._field_list,
            1,
        )

        mode_label = QLabel(
            "Default Masking Mode"
        )

        mode_font = mode_label.font()
        mode_font.setBold(True)

        mode_label.setFont(
            mode_font
        )

        layout.addWidget(
            mode_label
        )

        self._mask_mode = QComboBox()

        self._mask_mode.addItem(
            "Full Mask",
            "full",
        )

        self._mask_mode.addItem(
            "Partial Mask",
            "partial",
        )

        layout.addWidget(
            self._mask_mode
        )

        self._auto_email = QCheckBox(
            "Use email masking for fields named email"
        )

        self._auto_email.setChecked(
            True
        )

        layout.addWidget(
            self._auto_email
        )

        return panel

    def _create_preview_panel(
        self,
    ) -> QWidget:
        """Create original and masked JSON previews."""

        panel = QWidget()

        layout = QVBoxLayout(panel)

        preview_splitter = QSplitter(
            Qt.Orientation.Horizontal
        )

        original_panel = QWidget()

        original_layout = QVBoxLayout(
            original_panel
        )

        original_label = QLabel(
            "Original JSON"
        )

        original_font = (
            original_label.font()
        )

        original_font.setBold(True)

        original_label.setFont(
            original_font
        )

        self._original_editor = (
            QPlainTextEdit()
        )

        self._original_editor.setReadOnly(
            True
        )

        self._original_editor.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.NoWrap
        )

        self._original_editor.setFont(
            QFont(MONOSPACE_FONT)
        )

        original_layout.addWidget(
            original_label
        )

        original_layout.addWidget(
            self._original_editor
        )

        masked_panel = QWidget()

        masked_layout = QVBoxLayout(
            masked_panel
        )

        masked_label = QLabel(
            "Masked JSON"
        )

        masked_font = (
            masked_label.font()
        )

        masked_font.setBold(True)

        masked_label.setFont(
            masked_font
        )

        self._masked_editor = (
            QPlainTextEdit()
        )

        self._masked_editor.setReadOnly(
            True
        )

        self._masked_editor.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.NoWrap
        )

        self._masked_editor.setFont(
            QFont(MONOSPACE_FONT)
        )

        masked_layout.addWidget(
            masked_label
        )

        masked_layout.addWidget(
            self._masked_editor
        )

        preview_splitter.addWidget(
            original_panel
        )

        preview_splitter.addWidget(
            masked_panel
        )

        preview_splitter.setStretchFactor(
            0,
            1,
        )

        preview_splitter.setStretchFactor(
            1,
            1,
        )

        layout.addWidget(
            preview_splitter
        )

        return panel

    def set_payload(
        self,
        payload: JSONValue,
    ) -> None:
        """Set the currently loaded JSON payload."""

        self._payload = payload
        self._masked_payload = None

        self._original_editor.setPlainText(
            self._pretty_json(
                payload
            )
        )

        self._masked_editor.clear()

        self._populate_fields()

        self._status_label.setText(
            "JSON loaded. Select fields to mask."
        )

    def clear_payload(self) -> None:
        """Remove the currently loaded payload."""

        self._payload = None
        self._masked_payload = None

        self._original_editor.clear()
        self._masked_editor.clear()

        self._field_list.clear()

        self._status_label.setText(
            "Load a JSON payload to begin."
        )

    def _populate_fields(self) -> None:
        """Populate all available JSON field names."""

        self._field_list.clear()

        if self._payload is None:
            return

        fields = (
            self._masking_service
            .get_fields(self._payload)
        )

        for field in fields:
            item = QListWidgetItem(
                field
            )

            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
            )

            item.setCheckState(
                Qt.CheckState.Unchecked
            )

            self._field_list.addItem(
                item
            )

    def _detect_sensitive(self) -> None:
        """Automatically select likely sensitive fields."""

        if self._payload is None:
            QMessageBox.warning(
                self,
                "No JSON Loaded",
                "Load JSON before detecting "
                "sensitive fields.",
            )
            return

        detected = {
            field.casefold()
            for field
            in self._masking_service.detect_fields(
                self._payload
            )
        }

        count = 0

        for index in range(
            self._field_list.count()
        ):
            item = (
                self._field_list.item(
                    index
                )
            )

            if (
                item.text().casefold()
                in detected
            ):
                item.setCheckState(
                    Qt.CheckState.Checked
                )

                count += 1

        if count == 0:
            self._status_label.setText(
                "No known sensitive field names detected. "
                "Select fields manually if needed."
            )
        else:
            self._status_label.setText(
                f"{count} likely sensitive field(s) selected. "
                "Review them before masking."
            )

    def _mask_selected(self) -> None:
        """Mask all selected fields."""

        if self._payload is None:
            QMessageBox.warning(
                self,
                "No JSON Loaded",
                "Load JSON before masking fields.",
            )
            return

        selected_fields = (
            self._selected_fields()
        )

        if not selected_fields:
            QMessageBox.warning(
                self,
                "Sensitive-data Masking",
                "Select at least one field to mask.",
            )
            return

        email_fields: set[str] = set()
        partial_fields: set[str] = set()

        if self._auto_email.isChecked():
            email_fields = {
                field
                for field in selected_fields
                if field.casefold()
                in {
                    "email",
                    "email_address",
                    "emailaddress",
                }
            }

        if (
            self._mask_mode.currentData()
            == "partial"
        ):
            partial_fields = (
                set(selected_fields)
                - email_fields
            )

        self._masked_payload = (
            self._masking_service.mask(
                payload=self._payload,
                fields=selected_fields,
                email_fields=email_fields,
                partial_fields=partial_fields,
            )
        )

        self._masked_editor.setPlainText(
            self._pretty_json(
                self._masked_payload
            )
        )

        self._status_label.setText(
            f"{len(selected_fields)} field(s) masked. "
            "Original JSON remains unchanged."
        )

    def _selected_fields(
        self,
    ) -> list[str]:
        """Return checked field names."""

        selected: list[str] = []

        for index in range(
            self._field_list.count()
        ):
            item = (
                self._field_list.item(
                    index
                )
            )

            if (
                item.checkState()
                == Qt.CheckState.Checked
            ):
                selected.append(
                    item.text()
                )

        return selected

    def _select_all(self) -> None:
        """Select all available fields."""

        for index in range(
            self._field_list.count()
        ):
            self._field_list.item(
                index
            ).setCheckState(
                Qt.CheckState.Checked
            )

    def _clear_selection(self) -> None:
        """Clear all field selections."""

        for index in range(
            self._field_list.count()
        ):
            self._field_list.item(
                index
            ).setCheckState(
                Qt.CheckState.Unchecked
            )

    def _copy_masked_json(self) -> None:
        """Copy masked JSON to the system clipboard."""

        if self._masked_payload is None:
            QMessageBox.warning(
                self,
                "Sensitive-data Masking",
                "Mask the JSON before copying it.",
            )
            return

        clipboard = (
            QApplication.clipboard()
        )

        clipboard.setText(
            self._pretty_json(
                self._masked_payload
            )
        )

        self._status_label.setText(
            "Masked JSON copied to clipboard."
        )

    @staticmethod
    def _pretty_json(
        value: JSONValue,
    ) -> str:
        """Format JSON for display."""

        return json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
        )