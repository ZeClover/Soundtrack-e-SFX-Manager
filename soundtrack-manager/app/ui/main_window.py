"""Janela principal do RPG Soundtrack Manager: monta os painéis e a lógica de aplicação."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_NAME, database_path
from app.database import Database
from app.models import Track
from app.repositories import (
    CampaignRepository,
    LibraryRootRepository,
    SettingsRepository,
    SoundtrackRepository,
    TagRepository,
    TrackFilter,
    TrackRepository,
)
from app.services.export_service import ExportOptions, ExportService
from app.services.library_scanner import LibraryScanner, ScanResult
from app.services.player_service import PlayerService
from app.ui.dialogs.export_dialog import ExportDialog
from app.ui.dialogs.export_report_dialog import ExportReportDialog
from app.ui.dialogs.scan_progress_dialog import ScanProgressDialog
from app.ui.widgets.filters_panel import FiltersPanel
from app.ui.widgets.library_panel import LibraryPanel
from app.ui.widgets.player_bar import PlayerBar
from app.ui.widgets.soundtrack_panel import SoundtrackPanel

logger = logging.getLogger(__name__)

_SETTINGS_KEY_LIBRARY_PATH = "library_root_path"


class MainWindow(QMainWindow):
    def __init__(self, db_path: Path | None = None):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 800)

        self.db = Database(db_path or database_path())
        self.track_repo = TrackRepository(self.db)
        self.tag_repo = TagRepository(self.db)
        self.campaign_repo = CampaignRepository(self.db)
        self.soundtrack_repo = SoundtrackRepository(self.db)
        self.library_root_repo = LibraryRootRepository(self.db)
        self.settings_repo = SettingsRepository(self.db)

        self.player_service = PlayerService(self)
        self.export_service = ExportService()

        self._current_library_root_id: int | None = None
        self._current_soundtrack_id: int | None = None
        self._scanner: LibraryScanner | None = None
        self._scan_dialog: ScanProgressDialog | None = None

        self._build_ui()
        self._connect_signals()
        self._install_shortcuts()
        self._restore_last_library()
        self._reload_soundtracks()

    # ------------------------------------------------------------------
    # Construção da UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        toolbar = QToolBar("Principal")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        select_action = toolbar.addAction("Selecionar pasta da biblioteca...")
        select_action.triggered.connect(self._on_select_library_folder)

        rescan_action = toolbar.addAction("⟳ Atualizar biblioteca")
        rescan_action.triggered.connect(self._on_rescan_library)
        self._rescan_action = rescan_action
        self._rescan_action.setEnabled(False)

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.filters_panel = FiltersPanel()
        self.library_panel = LibraryPanel()
        self.soundtrack_panel = SoundtrackPanel()
        splitter.addWidget(self.filters_panel)
        splitter.addWidget(self.library_panel)
        splitter.addWidget(self.soundtrack_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([200, 760, 320])
        central_layout.addWidget(splitter, stretch=1)

        self.player_bar = PlayerBar(self.player_service)
        central_layout.addWidget(self.player_bar)

        self.setCentralWidget(central)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _connect_signals(self) -> None:
        self.filters_panel.filters_changed.connect(self.refresh_library)
        self.library_panel.search_changed.connect(lambda _: self.refresh_library())
        self.library_panel.play_requested.connect(self._on_play_from_library)
        self.library_panel.add_to_soundtrack_requested.connect(self._on_add_to_soundtrack)
        self.library_panel.favorite_toggle_requested.connect(self._on_toggle_favorite)
        self.library_panel.tags_edited.connect(self._on_tags_edited)
        self.library_panel.note_edited.connect(self._on_note_edited)

        self.soundtrack_panel.soundtrack_selected.connect(self._on_soundtrack_selected)
        self.soundtrack_panel.new_soundtrack_requested.connect(self._on_new_soundtrack)
        self.soundtrack_panel.remove_item_requested.connect(self._on_remove_item)
        self.soundtrack_panel.move_item_requested.connect(self._on_move_item)
        self.soundtrack_panel.reorder_requested.connect(self._on_reorder_items)
        self.soundtrack_panel.play_item_requested.connect(self._on_play_from_soundtrack)
        self.soundtrack_panel.export_requested.connect(self._on_export)

        self.player_service.track_finished_naturally.connect(self._on_track_finished)

    def _install_shortcuts(self) -> None:
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, activated=self._shortcut_play_pause)
        QShortcut(QKeySequence(Qt.Key.Key_Return), self, activated=self._shortcut_add_to_soundtrack)
        QShortcut(QKeySequence(Qt.Key.Key_Enter), self, activated=self._shortcut_add_to_soundtrack)
        QShortcut(QKeySequence(Qt.Key.Key_F), self, activated=self._shortcut_toggle_favorite)
        QShortcut(QKeySequence(Qt.Key.Key_Down), self, activated=lambda: self._shortcut_navigate(1))
        QShortcut(QKeySequence(Qt.Key.Key_Up), self, activated=lambda: self._shortcut_navigate(-1))

    def _typing_in_text_field(self) -> bool:
        widget = QApplication.focusWidget()
        return isinstance(widget, (QLineEdit, QPlainTextEdit))

    def _shortcut_play_pause(self) -> None:
        if self._typing_in_text_field():
            return
        self.player_service.toggle_play_pause()

    def _shortcut_add_to_soundtrack(self) -> None:
        if self._typing_in_text_field():
            return
        track = self.library_panel.selected_track()
        if track:
            self._on_add_to_soundtrack(track)

    def _shortcut_toggle_favorite(self) -> None:
        if self._typing_in_text_field():
            return
        track = self.library_panel.selected_track()
        if track:
            self._on_toggle_favorite(track)

    def _shortcut_navigate(self, delta: int) -> None:
        if self._typing_in_text_field():
            return
        self.library_panel.move_selection(delta)

    # ------------------------------------------------------------------
    # Biblioteca / escaneamento
    # ------------------------------------------------------------------

    def _restore_last_library(self) -> None:
        saved_path = self.settings_repo.get(_SETTINGS_KEY_LIBRARY_PATH)
        if saved_path and Path(saved_path).is_dir():
            self._current_library_root_id = self.library_root_repo.get_or_create(saved_path)
            self._rescan_action.setEnabled(True)
            self.refresh_library()

    def _on_select_library_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Selecionar pasta da biblioteca de músicas")
        if not folder:
            return
        self.settings_repo.set(_SETTINGS_KEY_LIBRARY_PATH, folder)
        self._start_scan(Path(folder))

    def _on_rescan_library(self) -> None:
        saved_path = self.settings_repo.get(_SETTINGS_KEY_LIBRARY_PATH)
        if saved_path:
            self._start_scan(Path(saved_path))

    def _start_scan(self, folder: Path) -> None:
        self._scanner = LibraryScanner(self.db, folder, self)
        self._scan_dialog = ScanProgressDialog(self)
        self._scanner.progress.connect(self._scan_dialog.set_progress)
        self._scanner.scan_finished.connect(self._on_scan_finished)
        self._scanner.scan_failed.connect(self._on_scan_failed)
        self._scan_dialog.cancel_requested.connect(self._scanner.cancel)
        self._scanner.start()
        self._scan_dialog.exec()

    def _on_scan_finished(self, result: ScanResult) -> None:
        if self._scan_dialog:
            self._scan_dialog.accept()
            self._scan_dialog = None
        self._current_library_root_id = result.library_root_id
        self._rescan_action.setEnabled(True)
        self.refresh_library()

        message = (
            f"Escaneamento concluído: {result.total_files_found} arquivo(s) encontrados, "
            f"{result.new_tracks} novo(s), {result.missing_tracks} ausente(s)."
        )
        if result.errors:
            message += f" {len(result.errors)} erro(s) — ver log."
            for error in result.errors:
                logger.warning("Erro de escaneamento: %s", error)
        self.status_bar.showMessage(message, 8000)

    def _on_scan_failed(self, message: str) -> None:
        if self._scan_dialog:
            self._scan_dialog.reject()
            self._scan_dialog = None
        QMessageBox.warning(self, "Erro ao escanear biblioteca", message)

    def refresh_library(self) -> None:
        if self._current_library_root_id is None:
            self.library_panel.set_tracks([])
            self._reload_filter_options()
            return

        filt = TrackFilter(
            search_text=self.library_panel.search_box.text(),
            library_root_id=self._current_library_root_id,
            campaign_id=self.filters_panel.campaign_id,
            tag_ids=tuple(self.filters_panel.checked_tag_ids()),
            favorites_only=self.filters_panel.favorites_only,
            missing_only=self.filters_panel.missing_only,
            exclude_missing=not self.filters_panel.missing_only,
        )
        tracks = self.track_repo.find(filt)
        self.library_panel.set_tracks(tracks)
        self._reload_filter_options()

        stats = self.track_repo.stats(self._current_library_root_id)
        self.status_bar.showMessage(
            f"{stats['total']} música(s)  •  {stats['favorites']} favorita(s)  •  "
            f"{stats['used_in_soundtracks']} usada(s) em soundtracks"
        )

    def _reload_filter_options(self) -> None:
        self.filters_panel.set_tags(self.tag_repo.list_all())
        self.filters_panel.set_campaigns(self.campaign_repo.list_all())

    # ------------------------------------------------------------------
    # Ações da biblioteca
    # ------------------------------------------------------------------

    def _on_play_from_library(self, track: Track) -> None:
        playlist = self.library_panel.model.all_tracks()
        self.player_service.play_track_now(track, playlist=playlist)

    def _on_toggle_favorite(self, track: Track) -> None:
        self.track_repo.set_favorite(track.id, not track.is_favorite)
        updated = self.track_repo.get_by_id(track.id)
        if updated:
            self.library_panel.update_track_in_place(updated)

    def _on_tags_edited(self, track_id: int, tag_names: list[str]) -> None:
        self.tag_repo.set_tags_for_track(track_id, tag_names)
        updated = self.track_repo.get_by_id(track_id)
        if updated:
            self.library_panel.update_track_in_place(updated)
        self._reload_filter_options()

    def _on_note_edited(self, track_id: int, note: str) -> None:
        self.track_repo.set_note(track_id, note)
        updated = self.track_repo.get_by_id(track_id)
        if updated:
            self.library_panel.update_track_in_place(updated)

    def _on_track_finished(self, track: Track) -> None:
        self.track_repo.register_play(track.id)
        updated = self.track_repo.get_by_id(track.id)
        if updated:
            self.library_panel.update_track_in_place(updated)

    # ------------------------------------------------------------------
    # Soundtrack
    # ------------------------------------------------------------------

    def _reload_soundtracks(self, select_id: int | None = None) -> None:
        soundtracks = self.soundtrack_repo.list_all()
        target = select_id or self._current_soundtrack_id or (soundtracks[0].id if soundtracks else None)
        self.soundtrack_panel.set_soundtracks(soundtracks, target)
        if target is not None:
            self._on_soundtrack_selected(target)
        else:
            self.soundtrack_panel.set_items([])

    def _on_new_soundtrack(self) -> None:
        name, ok = QInputDialog.getText(self, "Nova Soundtrack", "Nome da soundtrack:")
        if not ok or not name.strip():
            return
        soundtrack = self.soundtrack_repo.create(name.strip())
        self._reload_soundtracks(select_id=soundtrack.id)

    def _on_soundtrack_selected(self, soundtrack_id: int) -> None:
        self._current_soundtrack_id = soundtrack_id
        items = self.soundtrack_repo.get_items(soundtrack_id)
        self.soundtrack_panel.set_items(items)

    def _on_add_to_soundtrack(self, track: Track) -> None:
        if self._current_soundtrack_id is None:
            QMessageBox.information(
                self, "Nenhuma soundtrack selecionada",
                "Crie uma soundtrack primeiro (botão “＋ Nova”) antes de adicionar músicas.",
            )
            return

        if self.soundtrack_repo.has_track(self._current_soundtrack_id, track.id):
            answer = QMessageBox.question(
                self, "Música já adicionada",
                f"“{track.title}” já está nesta soundtrack.\n\nAdicionar novamente?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        self.soundtrack_repo.add_track(self._current_soundtrack_id, track.id)
        self._on_soundtrack_selected(self._current_soundtrack_id)
        self._reload_soundtracks(select_id=self._current_soundtrack_id)

    def _on_remove_item(self, item_id: int) -> None:
        if self._current_soundtrack_id is None:
            return
        self.soundtrack_repo.remove_item(item_id, self._current_soundtrack_id)
        self._on_soundtrack_selected(self._current_soundtrack_id)
        self._reload_soundtracks(select_id=self._current_soundtrack_id)

    def _on_move_item(self, item_id: int, direction: int) -> None:
        if self._current_soundtrack_id is None:
            return
        self.soundtrack_repo.move_item(self._current_soundtrack_id, item_id, direction)
        self._on_soundtrack_selected(self._current_soundtrack_id)

    def _on_reorder_items(self, ordered_item_ids: list[int]) -> None:
        if self._current_soundtrack_id is None:
            return
        self.soundtrack_repo.reorder(self._current_soundtrack_id, ordered_item_ids)
        self._on_soundtrack_selected(self._current_soundtrack_id)

    def _on_play_from_soundtrack(self, track_id: int) -> None:
        if self._current_soundtrack_id is None:
            return
        items = self.soundtrack_repo.get_items(self._current_soundtrack_id)
        tracks = [item.track for item in items if item.track]
        target = next((t for t in tracks if t.id == track_id), None)
        if target:
            self.player_service.play_track_now(target, playlist=tracks)

    def _on_export(self) -> None:
        if self._current_soundtrack_id is None:
            return
        soundtrack = self.soundtrack_repo.get(self._current_soundtrack_id)
        items = self.soundtrack_repo.get_items(self._current_soundtrack_id)
        if not items or soundtrack is None:
            QMessageBox.information(self, "Soundtrack vazia", "Adicione músicas antes de exportar.")
            return

        dialog = ExportDialog(soundtrack.name, len(items), parent=self)
        if dialog.exec() != ExportDialog.DialogCode.Accepted:
            return

        options: ExportOptions = dialog.export_options()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            report = self.export_service.export_soundtrack(soundtrack.name, items, options)
        finally:
            QApplication.restoreOverrideCursor()

        ExportReportDialog(report, parent=self).exec()

    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:  # noqa: N802
        self.player_service.stop()
        self.db.close()
        super().closeEvent(event)
