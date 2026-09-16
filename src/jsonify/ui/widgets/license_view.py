"""Jsonify license manager UI."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from jsonify.services.license_service import (
    LicenseError,
    LicenseService,
)
from jsonify.services.license_storage import (
    LicenseStorage,
)


class LicenseView(QWidget):
    """License management interface."""

    license_changed = Signal()

    def __init__(
        self,
        license_service: LicenseService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._license_service = (
            license_service
        )

        self._storage = LicenseStorage()

        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        """Build the license UI."""

        layout = QVBoxLayout(self)

        title = QLabel(
            "Jsonify License"
        )

        title_font = title.font()
        title_font.setPointSize(14)
        title_font.setBold(True)

        title.setFont(
            title_font
        )

        layout.addWidget(
            title
        )

        self._status = QLabel()

        status_font = self._status.font()
        status_font.setPointSize(12)
        status_font.setBold(True)

        self._status.setFont(
            status_font
        )

        layout.addWidget(
            self._status
        )

        form = QFormLayout()

        self._tier = QLabel()
        self._licensed_to = QLabel()
        self._license_id = QLabel()
        self._expires = QLabel()

        form.addRow(
            "Plan:",
            self._tier,
        )

        form.addRow(
            "Licensed to:",
            self._licensed_to,
        )

        form.addRow(
            "License ID:",
            self._license_id,
        )

        form.addRow(
            "Expires:",
            self._expires,
        )

        layout.addLayout(
            form
        )

        buttons = QHBoxLayout()

        activate = QPushButton(
            "Activate License..."
        )

        activate.clicked.connect(
            self._activate
        )

        deactivate = QPushButton(
            "Deactivate"
        )

        deactivate.clicked.connect(
            self._deactivate
        )

        buttons.addWidget(
            activate
        )

        buttons.addWidget(
            deactivate
        )

        buttons.addStretch()

        layout.addLayout(
            buttons
        )

        layout.addStretch()

    def refresh(self) -> None:
        """Refresh displayed license state."""

        license_info = (
            self._license_service
            .current_license
        )

        if license_info.is_pro:
            self._status.setText(
                "Jsonify Pro"
            )
        else:
            self._status.setText(
                "Jsonify Free"
            )

        self._tier.setText(
            license_info.tier.value.upper()
        )

        self._licensed_to.setText(
            license_info.licensed_to
            or "-"
        )

        self._license_id.setText(
            license_info.license_id
            or "-"
        )

        self._expires.setText(
            license_info.expires_at
            or "No expiration"
            if license_info.is_pro
            else "-"
        )

    def _activate(self) -> None:
        """Activate a signed license."""

        file_name, _ = (
            QFileDialog.getOpenFileName(
                self,
                "Activate Jsonify License",
                "",
                (
                    "Jsonify License "
                    "(*.jsonify-license)"
                ),
            )
        )

        if not file_name:
            return

        try:
            self._license_service.activate_file(
                file_name
            )

            self._storage.save_license(
                file_name
            )

        except (
            LicenseError,
            OSError,
        ) as error:
            QMessageBox.critical(
                self,
                "License Activation",
                str(error),
            )
            return

        self.refresh()

        self.license_changed.emit()

        QMessageBox.information(
            self,
            "Jsonify Pro",
            (
                "Jsonify Pro has been "
                "activated successfully."
            ),
        )

    def _deactivate(self) -> None:
        """Return this installation to Free mode."""

        self._storage.remove_license()

        self._license_service.reset_to_free()

        self.refresh()

        self.license_changed.emit()