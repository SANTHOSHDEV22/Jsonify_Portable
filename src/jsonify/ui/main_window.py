"""Main application window for Jsonify."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QActionGroup, QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from jsonify.core.app_paths import data_dir, is_portable
from jsonify.core.plugins import get_registry
from jsonify.services import JsonService, SessionService
from jsonify.services.large_json_service import LargeJsonService
from jsonify.services.update_service import UpdateCheckError, UpdateInfo, UpdateService
from jsonify.services.workspace_state_service import WorkspaceStateService
from jsonify.ui.constants import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    WINDOW_TITLE,
)
from jsonify.ui.theme import (
    SYSTEM_THEME_ID,
    build_stylesheet,
    get_theme,
    list_themes,
    resolve_system_theme,
)
from jsonify.ui.widgets.batch_dialog import BatchDialog
from jsonify.ui.widgets.command_palette import CommandPalette
from jsonify.ui.widgets.document_tab import DocumentTab
from jsonify.ui.widgets.welcome_view import WelcomeView

# How often the open-tabs recovery snapshot is refreshed, in milliseconds.
_AUTOSAVE_INTERVAL_MS = 30_000

_JSON_FILE_FILTER = "JSON Files (*.json *.jsonl *.ndjson);;All Files (*)"
_SESSION_FILE_FILTER = "Jsonify Session (*.jsonify)"
_THEME_SETTING_KEY = "theme"
_UPDATE_SETTING_KEY = "check_updates"


class _UpdateWorker(QThread):
    """Runs the (network) update check off the UI thread."""

    finished_with = Signal(object)
    failed = Signal(str)

    def __init__(self, current_version: str, parent=None) -> None:
        super().__init__(parent)
        self._current_version = current_version

    def run(self) -> None:
        try:
            self.finished_with.emit(UpdateService().check(self._current_version))
        except UpdateCheckError as error:
            self.failed.emit(str(error))


class MainWindow(QMainWindow):
    """Main window for viewing and exploring JSON payloads."""

    def __init__(
        self,
        json_service: JsonService | None = None,
    ) -> None:
        """Initialize Jsonify."""

        super().__init__()

        # -------------------------------------------------------------
        # Shared services (stateless enough to share across documents)
        # -------------------------------------------------------------

        self._json_service_override = json_service
        self._large_json_service = LargeJsonService()
        self._session_service = SessionService()
        self._workspace_state = WorkspaceStateService()

        # Plugins are loaded before any document exists so every view sees them.
        get_registry().load(data_dir() / "plugins")
        self._update_worker: _UpdateWorker | None = None
        self._update_check_is_manual = False

        # -------------------------------------------------------------
        # Theme state
        # -------------------------------------------------------------

        self._theme_id: str = self._workspace_state.get_setting(_THEME_SETTING_KEY, SYSTEM_THEME_ID)

        # -------------------------------------------------------------
        # Setup
        # -------------------------------------------------------------

        self._setup_window()
        self._setup_ui()
        self._setup_menu()
        self._apply_theme(self._theme_id, persist=False)

        self._tab_cycle_next = QShortcut(QKeySequence("Ctrl+Tab"), self)
        self._tab_cycle_next.activated.connect(self._cycle_document_tab_next)

        self._tab_cycle_prev = QShortcut(QKeySequence("Ctrl+Shift+Tab"), self)
        self._tab_cycle_prev.activated.connect(self._cycle_document_tab_prev)

        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(_AUTOSAVE_INTERVAL_MS)
        self._autosave_timer.timeout.connect(self._write_recovery_snapshot)
        self._autosave_timer.start()

        QTimer.singleShot(0, self._offer_crash_recovery)
        if self._workspace_state.get_setting(_UPDATE_SETTING_KEY, False):
            QTimer.singleShot(2000, lambda: self._check_for_updates(manual=False))

    # =================================================================
    # Window setup
    # =================================================================

    def _setup_window(self) -> None:
        """Configure the main application window."""

        self.setWindowTitle(WINDOW_TITLE)
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        self.statusBar().showMessage("Ready")

    # =================================================================
    # Main UI
    # =================================================================

    def _setup_ui(self) -> None:
        """Build the main user interface."""

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._stack = QStackedWidget()

        self._welcome = WelcomeView(self._workspace_state.get_recent_files())
        self._welcome.new_document_requested.connect(self.new_document)
        self._welcome.open_file_requested.connect(self._open_file_dialog)
        self._welcome.open_session_requested.connect(self._open_session)
        self._welcome.recent_file_selected.connect(self._open_recent_file)

        self._doc_tabs = QTabWidget()
        self._doc_tabs.setTabsClosable(True)
        self._doc_tabs.setMovable(True)
        self._doc_tabs.setDocumentMode(True)
        self._doc_tabs.tabCloseRequested.connect(self._close_tab)
        self._doc_tabs.currentChanged.connect(self._on_current_tab_changed)

        new_tab_button = QPushButton("+ New")
        new_tab_button.setToolTip("New document (Ctrl+N)")
        new_tab_button.clicked.connect(self.new_document)
        self._doc_tabs.setCornerWidget(new_tab_button)

        self._stack.addWidget(self._welcome)
        self._stack.addWidget(self._doc_tabs)

        root_layout.addWidget(self._stack, stretch=1)

        self._update_stack_visibility()

    # =================================================================
    # Menu
    # =================================================================

    def _setup_menu(self) -> None:
        """Create the application menu."""

        menu_bar = self.menuBar()

        # -------------------------------------------------------------
        # File menu
        # -------------------------------------------------------------

        file_menu = menu_bar.addMenu("&File")

        new_action = QAction("New Document", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_document)
        file_menu.addAction(new_action)

        open_file_action = QAction("Open File...", self)
        open_file_action.setShortcut(QKeySequence.StandardKey.Open)
        open_file_action.triggered.connect(self._open_file_dialog)
        file_menu.addAction(open_file_action)

        load_action = QAction("Load JSON From Editor", self)
        load_action.setShortcut(QKeySequence("Ctrl+Return"))
        load_action.triggered.connect(self._load_json)
        file_menu.addAction(load_action)

        palette_action = QAction("Command Palette...", self)
        palette_action.setShortcut(QKeySequence("Ctrl+Shift+P"))
        palette_action.triggered.connect(self._show_command_palette)
        file_menu.addAction(palette_action)

        self._recent_menu = QMenu("Open Recent", self)
        file_menu.addMenu(self._recent_menu)
        self._refresh_recent_menu()

        file_menu.addSeparator()

        self._open_session_action = QAction("Open Session...", self)
        self._open_session_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        self._open_session_action.triggered.connect(self._open_session)
        file_menu.addAction(self._open_session_action)

        self._save_session_action = QAction("Save Session", self)
        self._save_session_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self._save_session_action.triggered.connect(self._save_session)
        file_menu.addAction(self._save_session_action)

        self._save_session_as_action = QAction("Save Session As...", self)
        self._save_session_as_action.triggered.connect(self._save_session_as)
        file_menu.addAction(self._save_session_as_action)

        batch_action = QAction("Batch Process...", self)
        batch_action.triggered.connect(self._show_batch_dialog)
        file_menu.addAction(batch_action)

        file_menu.addSeparator()

        close_tab_action = QAction("Close Document", self)
        close_tab_action.setShortcut(QKeySequence.StandardKey.Close)
        close_tab_action.triggered.connect(self._close_current_tab)
        file_menu.addAction(close_tab_action)

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # -------------------------------------------------------------
        # Settings menu
        # -------------------------------------------------------------

        settings_menu = menu_bar.addMenu("&Settings")
        theme_menu = settings_menu.addMenu("Theme")

        self._theme_group = QActionGroup(self)
        self._theme_group.setExclusive(True)
        self._theme_actions: dict[str, QAction] = {}

        system_action = QAction("Follow System", self)
        system_action.setCheckable(True)
        system_action.triggered.connect(lambda: self._apply_theme(SYSTEM_THEME_ID))
        self._theme_group.addAction(system_action)
        theme_menu.addAction(system_action)
        self._theme_actions[SYSTEM_THEME_ID] = system_action

        theme_menu.addSeparator()

        for theme in list_themes():
            theme_action = QAction(theme.name, self)
            theme_action.setCheckable(True)
            theme_action.triggered.connect(
                lambda _checked=False, theme_id=theme.id: self._apply_theme(theme_id)
            )
            self._theme_group.addAction(theme_action)
            theme_menu.addAction(theme_action)
            self._theme_actions[theme.id] = theme_action

        settings_menu.addSeparator()

        self._update_check_action = QAction("Check for Updates on Startup", self)
        self._update_check_action.setCheckable(True)
        self._update_check_action.setChecked(
            bool(self._workspace_state.get_setting(_UPDATE_SETTING_KEY, False))
        )
        self._update_check_action.toggled.connect(
            lambda checked: self._workspace_state.set_setting(_UPDATE_SETTING_KEY, checked)
        )
        settings_menu.addAction(self._update_check_action)

        # -------------------------------------------------------------
        # About menu
        # -------------------------------------------------------------

        about_menu = menu_bar.addMenu("&About")

        version_action = QAction("Version", self)
        version_action.triggered.connect(self._show_version_dialog)
        about_menu.addAction(version_action)

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about_dialog)
        about_menu.addAction(about_action)

        update_action = QAction("Check for Updates...", self)
        update_action.triggered.connect(lambda: self._check_for_updates(manual=True))
        about_menu.addAction(update_action)

        plugins_action = QAction("Loaded Plugins", self)
        plugins_action.triggered.connect(self._show_plugins_dialog)
        about_menu.addAction(plugins_action)

    def _apply_theme(self, theme_id: str, *, persist: bool = True) -> None:
        """Apply a theme by id (or ``SYSTEM_THEME_ID`` to follow the OS).

        Only re-styles the Qt chrome (window, panes, tabs, buttons, the
        tree/hierarchy/filtered text views) — the Graph tab's embedded D3
        view has its own separate dark background baked into the HTML it
        renders and isn't affected by this setting.
        """

        self._theme_id = theme_id
        resolved = resolve_system_theme() if theme_id == SYSTEM_THEME_ID else get_theme(theme_id)

        self.setStyleSheet(build_stylesheet(resolved))

        action = self._theme_actions.get(theme_id)
        if action is not None:
            action.setChecked(True)

        for index in range(self._doc_tabs.count()):
            document = self._doc_tabs.widget(index)
            if isinstance(document, DocumentTab):
                document.apply_theme(resolved.colors)

        if persist:
            self._workspace_state.set_setting(_THEME_SETTING_KEY, theme_id)

    def _current_theme_colors(self) -> dict[str, str]:
        resolved = (
            resolve_system_theme()
            if self._theme_id == SYSTEM_THEME_ID
            else get_theme(self._theme_id)
        )
        return resolved.colors

    def _show_command_palette(self) -> None:
        actions = [action for action in self.findChildren(QAction) if action.text().strip()]
        palette = CommandPalette(actions, self)
        palette.exec()

    def _cycle_document_tab_next(self) -> None:
        self._cycle_document_tab(1)

    def _cycle_document_tab_prev(self) -> None:
        self._cycle_document_tab(-1)

    def _cycle_document_tab(self, direction: int) -> None:
        count = self._doc_tabs.count()
        if count == 0:
            return

        next_index = (self._doc_tabs.currentIndex() + direction) % count
        self._doc_tabs.setCurrentIndex(next_index)

    def _show_version_dialog(self) -> None:
        """Show the application version."""

        QMessageBox.information(self, "Version", f"{APP_NAME} version {APP_VERSION}")

    def _show_about_dialog(self) -> None:
        """Show application information."""

        QMessageBox.information(
            self,
            "About",
            (
                f"{APP_NAME} version {APP_VERSION}\n\n"
                "A JSON payload viewer and editor with tree, hierarchy, "
                "filtered, and graph views.\n\n"
                f"Mode: {'Portable' if is_portable() else 'Installed'}\n"
                f"Data folder: {data_dir()}"
            ),
        )

    # =================================================================
    # Document management
    # =================================================================

    def new_document(self) -> DocumentTab:
        """Open a new, empty document tab and make it current."""

        document = DocumentTab(
            json_service=self._json_service_override,
            large_json_service=self._large_json_service,
            session_service=self._session_service,
        )

        document.title_changed.connect(
            lambda title, doc=document: self._on_document_title_changed(doc, title)
        )
        document.status_changed.connect(self.statusBar().showMessage)
        document.apply_theme(self._current_theme_colors())

        index = self._doc_tabs.addTab(document, document.display_name())
        self._doc_tabs.setCurrentIndex(index)
        self._update_stack_visibility()

        return document

    def _current_document(self) -> DocumentTab | None:
        widget = self._doc_tabs.currentWidget()
        return widget if isinstance(widget, DocumentTab) else None

    def _current_or_new_document(self, *, reuse_if_empty: bool = True) -> DocumentTab:
        document = self._current_document()

        if document is not None and reuse_if_empty and not document.has_content():
            return document

        if document is not None and not reuse_if_empty:
            return document

        return self.new_document()

    def _on_document_title_changed(self, document: DocumentTab, title: str) -> None:
        index = self._doc_tabs.indexOf(document)
        if index >= 0:
            self._doc_tabs.setTabText(index, title)

    def _close_tab(self, index: int) -> None:
        widget = self._doc_tabs.widget(index)
        self._doc_tabs.removeTab(index)

        if widget is not None:
            widget.deleteLater()

        self._update_stack_visibility()

    def _close_current_tab(self) -> None:
        index = self._doc_tabs.currentIndex()
        if index >= 0:
            self._close_tab(index)

    def _on_current_tab_changed(self, index: int) -> None:
        document = self._doc_tabs.widget(index)
        if isinstance(document, DocumentTab):
            self.statusBar().showMessage(document.display_name())

    def _update_stack_visibility(self) -> None:
        if self._doc_tabs.count() == 0:
            self._welcome.set_recent_files(self._workspace_state.get_recent_files())
            self._stack.setCurrentWidget(self._welcome)
        else:
            self._stack.setCurrentWidget(self._doc_tabs)

    # =================================================================
    # JSON loading
    # =================================================================

    def _load_json(self) -> None:
        document = self._current_document()
        if document is None:
            document = self.new_document()
        document.load_from_editor()

    def _open_file_dialog(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(self, "Open JSON File", "", _JSON_FILE_FILTER)
        if file_name:
            self._open_path(Path(file_name))

    def _open_path(self, path: Path) -> None:
        document = self._current_or_new_document()
        document.open_file(path)
        self._workspace_state.add_recent_file(str(path))
        self._refresh_recent_menu()

    def _open_recent_file(self, path_str: str) -> None:
        path = Path(path_str)

        if not path.exists():
            QMessageBox.warning(self, "File Not Found", f"This file no longer exists:\n\n{path}")
            return

        self._open_path(path)

    def _refresh_recent_menu(self) -> None:
        self._recent_menu.clear()
        recent_files = self._workspace_state.get_recent_files()

        if not recent_files:
            empty_action = QAction("(No recent files)", self)
            empty_action.setEnabled(False)
            self._recent_menu.addAction(empty_action)
            return

        for path_str in recent_files:
            action = QAction(path_str, self)
            action.triggered.connect(lambda _checked=False, p=path_str: self._open_recent_file(p))
            self._recent_menu.addAction(action)

        self._recent_menu.addSeparator()
        clear_action = QAction("Clear Recently Opened", self)
        clear_action.triggered.connect(self._clear_recent_files)
        self._recent_menu.addAction(clear_action)

    def _clear_recent_files(self) -> None:
        self._workspace_state.clear_recent_files()
        self._refresh_recent_menu()
        self._welcome.set_recent_files([])

    # =================================================================
    # Saved Sessions
    # =================================================================

    def _open_session(self) -> None:
        document = self._current_or_new_document()
        document.open_session_dialog()

    def _save_session(self) -> None:
        document = self._current_document()
        if document is not None:
            document.save_session()

    def _save_session_as(self) -> None:
        document = self._current_document()
        if document is not None:
            document.save_session_as()

    def open_paths(self, paths: list[Path]) -> None:
        """Open several files (e.g. passed on the command line)."""

        for path in paths:
            self._open_path(path)

    # =================================================================
    # Batch, plugins, updates
    # =================================================================

    def _show_batch_dialog(self) -> None:
        BatchDialog(self).exec()

    def _show_plugins_dialog(self) -> None:
        registry = get_registry()
        lines = [f"Plugin folder: {data_dir() / 'plugins'}", ""]

        if registry.loaded:
            lines.append("Loaded:")
            lines += [f"  - {name}" for name in registry.loaded]
        else:
            lines.append("No plugins loaded.")

        provided = [
            f"Converters: {', '.join(registry.converters) or '-'}",
            f"Analyzers: {', '.join(registry.analyzers) or '-'}",
            f"Tools: {', '.join(registry.tools) or '-'}",
        ]
        lines += ["", *provided]

        if registry.errors:
            lines += ["", "Errors:"]
            lines += [f"  - {error}" for error in registry.errors]

        QMessageBox.information(self, "Plugins", "\n".join(lines))

    def _check_for_updates(self, *, manual: bool) -> None:
        if self._update_worker is not None and self._update_worker.isRunning():
            return

        self._update_check_is_manual = manual
        if manual:
            self.statusBar().showMessage("Checking for updates...")

        worker = _UpdateWorker(APP_VERSION, self)
        worker.finished_with.connect(self._on_update_result)
        worker.failed.connect(self._on_update_failed)
        self._update_worker = worker
        worker.start()

    def _on_update_result(self, info: UpdateInfo) -> None:
        if info.is_newer:
            answer = QMessageBox.question(
                self,
                "Update Available",
                f"Jsonify {info.latest_version} is available (you have {info.current_version}).\n\n"
                f"{info.notes[:600]}\n\nOpen the download page?",
            )
            if answer == QMessageBox.StandardButton.Yes:
                QDesktopServices.openUrl(QUrl(info.release_url))
        elif self._update_check_is_manual:
            QMessageBox.information(
                self, "Up to Date", f"You are running the latest version ({info.current_version})."
            )
        self.statusBar().clearMessage()

    def _on_update_failed(self, message: str) -> None:
        if self._update_check_is_manual:
            QMessageBox.information(self, "Update Check", message)
        self.statusBar().clearMessage()

    # =================================================================
    # Crash recovery
    # =================================================================

    def _write_recovery_snapshot(self) -> None:
        snapshot: list[dict[str, str | None]] = []

        for index in range(self._doc_tabs.count()):
            document = self._doc_tabs.widget(index)
            if not isinstance(document, DocumentTab):
                continue

            text = document.editor_text()
            if not text.strip():
                continue

            snapshot.append(
                {
                    "file_path": str(document.file_path) if document.file_path else None,
                    "text": text,
                }
            )

        if snapshot:
            self._workspace_state.write_recovery_snapshot(snapshot)
        else:
            self._workspace_state.clear_recovery_snapshot()

    def _offer_crash_recovery(self) -> None:
        snapshot = self._workspace_state.read_recovery_snapshot()
        if not snapshot:
            return

        count = len(snapshot)
        result = QMessageBox.question(
            self,
            "Restore Previous Session",
            (
                f"Jsonify did not close normally. Restore {count} unsaved "
                f"document{'s' if count != 1 else ''} from before it closed?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if result == QMessageBox.StandardButton.Yes:
            for entry in snapshot:
                document = self.new_document()
                document.load_text(str(entry.get("text", "")))
                file_path = entry.get("file_path")
                if file_path:
                    document.file_path = Path(str(file_path))

        self._workspace_state.clear_recovery_snapshot()

    # =================================================================
    # Close
    # =================================================================

    def closeEvent(self, event) -> None:
        """Handle application close."""

        self._workspace_state.clear_recovery_snapshot()
        event.accept()
