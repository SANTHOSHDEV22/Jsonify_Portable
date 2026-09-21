"""Empty-state "welcome" screen shown when no documents are open."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from jsonify.ui.constants import APP_NAME


class WelcomeView(QWidget):
    """Shown in place of the document tabs when nothing is open."""

    new_document_requested = Signal()
    open_file_requested = Signal()
    open_session_requested = Signal()
    recent_file_selected = Signal(str)

    def __init__(
        self, recent_files: list[str] | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(16)
        layout.addStretch(1)

        title = QLabel(APP_NAME)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 28px; font-weight: 600;")
        layout.addWidget(title)

        subtitle = QLabel("Open a JSON file, paste a payload, or restore a session to get started.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        buttons_row = QHBoxLayout()
        buttons_row.addStretch(1)

        new_button = QPushButton("New Document")
        new_button.clicked.connect(self.new_document_requested)
        buttons_row.addWidget(new_button)

        open_button = QPushButton("Open File...")
        open_button.clicked.connect(self.open_file_requested)
        buttons_row.addWidget(open_button)

        open_session_button = QPushButton("Open Session...")
        open_session_button.clicked.connect(self.open_session_requested)
        buttons_row.addWidget(open_session_button)

        buttons_row.addStretch(1)
        layout.addLayout(buttons_row)

        self._recent_label = QLabel("Recent Files")
        self._recent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._recent_label)

        self._recent_list = QListWidget()
        self._recent_list.setMaximumWidth(520)
        self._recent_list.itemDoubleClicked.connect(self._on_item_activated)
        recent_row = QHBoxLayout()
        recent_row.addStretch(1)
        recent_row.addWidget(self._recent_list)
        recent_row.addStretch(1)
        layout.addLayout(recent_row)

        layout.addStretch(2)

        self.set_recent_files(recent_files or [])

    def set_recent_files(self, recent_files: list[str]) -> None:
        """Refresh the recent-files list."""

        self._recent_list.clear()

        for path in recent_files:
            item = QListWidgetItem(path)
            item.setData(Qt.ItemDataRole.UserRole, path)
            self._recent_list.addItem(item)

        self._recent_label.setVisible(bool(recent_files))
        self._recent_list.setVisible(bool(recent_files))

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.recent_file_selected.emit(path)
