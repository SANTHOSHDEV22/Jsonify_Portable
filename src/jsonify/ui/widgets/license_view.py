"""Jsonify production license and Pro purchase UI."""

from __future__ import annotations

import re
import webbrowser

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from jsonify.core.licensing import PRO_FEATURES, Feature
from jsonify.services.license_purchase_service import (
    LicensePurchaseService,
    PurchaseError,
)
from jsonify.services.license_service import LicenseError, LicenseService
from jsonify.services.license_storage import LicenseStorage


PRO_PRICE_TEXT = "₹250"
PRO_FEATURE_LABELS: dict[Feature, str] = {
    Feature.JSON_DIFF: "JSON Diff — compare two JSON documents",
    Feature.JSONPATH: "JSONPath — query complex payloads",
    Feature.SCHEMA_VALIDATION: "Schema Validation — validate JSON against a schema",
    Feature.DATA_MASKING: "Data Masking — hide sensitive values",
    Feature.SAVED_SESSIONS: "Saved Sessions — preserve your work",
    Feature.API_VIEWER: "API Viewer — send requests and inspect JSON responses",
    Feature.EXPORT: "Export — JSON plus graph SVG, PNG and PDF",
    Feature.LARGE_JSON: "Large JSON — work with larger payloads",
    Feature.ADVANCED_GRAPH: "Advanced Graph — interactive graph visualization",
}


class PurchaseDialog(QDialog):
    """Collect purchaser details before opening secure checkout."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Purchase Jsonify Pro")
        self.setMinimumWidth(430)

        layout = QVBoxLayout(self)

        heading = QLabel(f"Jsonify Pro — {PRO_PRICE_TEXT}")
        font = heading.font()
        font.setPointSize(14)
        font.setBold(True)
        heading.setFont(font)
        layout.addWidget(heading)

        info = QLabel(
            "One-time Pro purchase. Enter the name and email address that "
            "should receive the license code."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Your name")
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("you@example.com")
        form.addRow("Name:", self.name_edit)
        form.addRow("Email:", self.email_edit)
        layout.addLayout(form)

        security = QLabel(
            "Payment is completed in your browser. Jsonify does not store "
            "card, UPI, or banking credentials."
        )
        security.setWordWrap(True)
        layout.addWidget(security)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
        )
        self.purchase_button = self.buttons.addButton(
            f"Continue to Payment — {PRO_PRICE_TEXT}",
            QDialogButtonBox.ButtonRole.AcceptRole,
        )
        self.purchase_button.clicked.connect(self._validate_and_accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def _validate_and_accept(self) -> None:
        name = self.name_edit.text().strip()
        email = self.email_edit.text().strip()

        if len(name) < 2:
            QMessageBox.warning(self, "Purchase Jsonify Pro", "Enter your name.")
            return

        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            QMessageBox.warning(
                self,
                "Purchase Jsonify Pro",
                "Enter a valid email address.",
            )
            return

        self.accept()

    @property
    def purchaser(self) -> tuple[str, str]:
        return (
            self.name_edit.text().strip(),
            self.email_edit.text().strip(),
        )


class ActivationDialog(QDialog):
    """Paste and activate a signed Jsonify license code."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Activate Jsonify Pro")
        self.setMinimumSize(600, 330)

        layout = QVBoxLayout(self)

        title = QLabel("Enter your Jsonify Pro license code")
        font = title.font()
        font.setPointSize(13)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        info = QLabel(
            "After payment, the license code is sent to your email. "
            "Copy the complete code and paste it below."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.code_edit = QTextEdit()
        self.code_edit.setPlaceholderText("JPRO1-...")
        layout.addWidget(self.code_edit, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
        )
        activate = buttons.addButton(
            "Activate Pro",
            QDialogButtonBox.ButtonRole.AcceptRole,
        )
        activate.clicked.connect(self._accept_if_present)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept_if_present(self) -> None:
        if not self.code_edit.toPlainText().strip():
            QMessageBox.warning(
                self,
                "License Activation",
                "Paste your license code first.",
            )
            return
        self.accept()

    @property
    def license_code(self) -> str:
        return self.code_edit.toPlainText().strip()


class LicenseView(QWidget):
    """License management and Jsonify Pro purchase interface."""

    license_changed = Signal()

    def __init__(
        self,
        license_service: LicenseService,
        parent: QWidget | None = None,
        purchase_service: LicensePurchaseService | None = None,
    ) -> None:
        super().__init__(parent)

        self._license_service = license_service
        self._storage = LicenseStorage()
        self._purchase_service = (
            purchase_service
            if purchase_service is not None
            else LicensePurchaseService()
        )

        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Jsonify License")
        font = title.font()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        self._pages = QStackedWidget()
        layout.addWidget(self._pages, 1)

        self._free_page = self._build_free_page()
        self._pro_page = self._build_pro_page()

        self._pages.addWidget(self._free_page)
        self._pages.addWidget(self._pro_page)

    def _build_free_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        heading = QLabel("Upgrade to Jsonify Pro")
        font = heading.font()
        font.setPointSize(16)
        font.setBold(True)
        heading.setFont(font)
        layout.addWidget(heading)

        price = QLabel(f"{PRO_PRICE_TEXT} — one-time purchase")
        price_font = price.font()
        price_font.setPointSize(13)
        price_font.setBold(True)
        price.setFont(price_font)
        layout.addWidget(price)

        description = QLabel(
            "Unlock the complete Jsonify toolkit. Your signed license code "
            "is delivered to the email used during purchase."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(line)

        feature_heading = QLabel("Jsonify Pro includes")
        feature_font = feature_heading.font()
        feature_font.setBold(True)
        feature_heading.setFont(feature_font)
        layout.addWidget(feature_heading)

        for feature in sorted(PRO_FEATURES, key=lambda item: item.value):
            label = QLabel(f"✓  {PRO_FEATURE_LABELS.get(feature, feature.value)}")
            label.setWordWrap(True)
            layout.addWidget(label)

        layout.addStretch()

        note = QLabel(
            "Already purchased? Use the license code from your email."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QHBoxLayout()

        purchase = QPushButton(f"Purchase Pro — {PRO_PRICE_TEXT}")
        purchase.clicked.connect(self._purchase)
        buttons.addWidget(purchase)

        activate = QPushButton("I Have a License Code")
        activate.clicked.connect(self._activate_code)
        buttons.addWidget(activate)

        buttons.addStretch()
        layout.addLayout(buttons)

        return page

    def _build_pro_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        heading = QLabel("Jsonify Pro")
        font = heading.font()
        font.setPointSize(16)
        font.setBold(True)
        heading.setFont(font)
        layout.addWidget(heading)

        self._pro_message = QLabel("Pro is active on this installation.")
        layout.addWidget(self._pro_message)

        form = QFormLayout()
        self._tier = QLabel()
        self._licensed_to = QLabel()
        self._email = QLabel()
        self._license_id = QLabel()
        self._expires = QLabel()

        form.addRow("Plan:", self._tier)
        form.addRow("Licensed to:", self._licensed_to)
        form.addRow("Email:", self._email)
        form.addRow("License ID:", self._license_id)
        form.addRow("Expires:", self._expires)
        layout.addLayout(form)

        buttons = QHBoxLayout()

        change_license = QPushButton("Enter Another License Code")
        change_license.clicked.connect(self._activate_code)
        buttons.addWidget(change_license)

        deactivate = QPushButton("Deactivate")
        deactivate.clicked.connect(self._deactivate)
        buttons.addWidget(deactivate)

        buttons.addStretch()
        layout.addLayout(buttons)
        layout.addStretch()

        return page

    def refresh(self) -> None:
        """Refresh displayed license state."""

        license_info = self._license_service.current_license

        if license_info.is_pro:
            self._pages.setCurrentWidget(self._pro_page)
            self._tier.setText(license_info.tier.value.upper())
            self._licensed_to.setText(license_info.licensed_to or "-")
            self._email.setText(license_info.email or "-")
            self._license_id.setText(license_info.license_id or "-")
            self._expires.setText(license_info.expires_at or "No expiration")
        else:
            self._pages.setCurrentWidget(self._free_page)

    def _purchase(self) -> None:
        """Collect purchaser data and open server-created checkout."""

        dialog = PurchaseDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        name, email = dialog.purchaser

        try:
            session = self._purchase_service.create_checkout(name, email)
        except PurchaseError as error:
            QMessageBox.critical(self, "Purchase Jsonify Pro", str(error))
            return

        opened = webbrowser.open(session.checkout_url)
        if not opened:
            QMessageBox.information(
                self,
                "Purchase Jsonify Pro",
                "Open this checkout URL in your browser:\n\n"
                f"{session.checkout_url}",
            )
            return

        QMessageBox.information(
            self,
            "Purchase Jsonify Pro",
            "Checkout opened in your browser. After the ₹250 payment is "
            "verified, your Jsonify Pro license code will be emailed to "
            f"{email}. Return here and choose 'I Have a License Code'.",
        )

    def _activate_code(self) -> None:
        """Activate a signed license code."""

        dialog = ActivationDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            document = self._license_service.decode_license_code(
                dialog.license_code
            )
            self._license_service.activate_code(dialog.license_code)
            self._storage.save_document(document)
        except (LicenseError, OSError) as error:
            QMessageBox.critical(self, "License Activation", str(error))
            return

        self.refresh()
        self.license_changed.emit()

        QMessageBox.information(
            self,
            "Jsonify Pro",
            "Jsonify Pro has been activated successfully.",
        )

    def _deactivate(self) -> None:
        """Return this installation to Free mode."""

        answer = QMessageBox.question(
            self,
            "Deactivate Jsonify Pro",
            "Deactivate Jsonify Pro on this installation?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self._storage.remove_license()
        except OSError as error:
            QMessageBox.critical(self, "Deactivate License", str(error))
            return

        self._license_service.reset_to_free()
        self.refresh()
        self.license_changed.emit()
