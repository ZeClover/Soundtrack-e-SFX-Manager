"""Janela principal do RPG SFX Manager: monta os painéis e a lógica de aplicação."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from sfx_app.config import database_path
from sfx_app.database import Database
from sfx_app.models import SfxTrack
from sfx_app.repositories import (
    CategoryRepository,
    HotkeyRepository,
    LibraryRootRepository,
    PackRepository,
    SettingsRepository,
    SfxTrackFilter,
    SfxTrackRepository,
    TagRepository,
)
from sfx_app.services.duplicate_service import DuplicateService
from sfx_app.services.export_service import ExportOptions, ExportService
from sfx_app.services.library_scanner import LibraryScanner, ScanResult
from sfx_app.services.sfx_player_service import SfxPlayerService
from sfx_app.ui.dialogs.category_manager_dialog import CategoryManagerDialog
from sfx_app.ui.dialogs.duplicates_dialog import DuplicatesDialog
from sfx_app.ui.dialogs.export_dialog import ExportDialog
from sfx_app.ui.dialogs.export_report_dialog import ExportReportDialog
from sfx_app.ui.dialogs.hotkey_dialog import HotkeyDialog
from sfx_app.ui.dialogs.scan_progress_dialog import ScanProgressDialog
from sfx_app.ui.widgets.pack_panel import PackPanel
from sfx_app.ui.widgets.sfx_filters_panel import SfxFiltersPanel
from sfx_app.ui.widgets.sfx_library_panel import SfxLibraryPanel

logger = logging.getLogger(__name__)

_SETTINGS_KEY_LIBRARY_PATH = "library_root_path"


class MainWindow(QWidget):
    """Widget do módulo SFX: usável como janela central standalone (veja
    ``main.py``) ou embutido como página do RPG Audio Studio."""

    def __init__(self, db_path: Path | None = None):
        super().__init__()
        self._is_active = True

        self.db = Database(db_path or database_path())
        self.track_repo = SfxTrackRepository(self.db)
        self.tag_repo = TagRepository(self.db)
        self.category_repo = CategoryRepository(self.db)
        self.pack_repo = PackRepository(self.db)
        self.hotkey_repo = HotkeyRepository(self.db)
        self.library_root_repo = LibraryRootRepository(self.db)
        self.settings_repo = SettingsRepository(self.db)

        self.player_service = SfxPlayerService(self)
        self.export_service = ExportService()

        self._current_library_root_id: int | None = None
        self._current_pack_id: int | None = None
        # Preenchido pelo Studio (item 14 da Etapa 6) pra pré-selecionar o
        # comportamento de duplicados salvo em Configurações; no app
        # standalone fica None e o diálogo usa seu próprio padrão de sempre.
        self._default_conflict_policy_provider: Callable[[], str] | None = None
        self._scanner: LibraryScanner | None = None
        self._scan_dialog: ScanProgressDialog | None = None
        self._hotkey_shortcuts: dict[str, QShortcut] = {}

        self._build_ui()
        self._connect_signals()
        self._restore_last_library()
        self._reload_packs()
        self._rebuild_hotkey_shortcuts()

    # ------------------------------------------------------------------
    # Construção da UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QToolBar("Principal")
        toolbar.setMovable(False)
        layout.addWidget(toolbar)

        select_action = toolbar.addAction("Selecionar pasta da biblioteca...")
        select_action.triggered.connect(self._on_select_library_folder)

        rescan_action = toolbar.addAction("⟳ Atualizar biblioteca")
        rescan_action.triggered.connect(self._on_rescan_library)
        self._rescan_action = rescan_action
        self._rescan_action.setEnabled(False)

        duplicates_action = toolbar.addAction("Localizar duplicados")
        duplicates_action.triggered.connect(self._on_find_duplicates)

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.filters_panel = SfxFiltersPanel()
        self.library_panel = SfxLibraryPanel()
        self.pack_panel = PackPanel()
        splitter.addWidget(self.filters_panel)
        splitter.addWidget(self.library_panel)
        splitter.addWidget(self.pack_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([200, 760, 320])
        central_layout.addWidget(splitter, stretch=1)

        bottom_bar = QWidget()
        bottom_bar.setObjectName("Panel")
        bottom_layout = QVBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(14, 8, 14, 8)
        bottom_row = QHBoxLayout()
        self.active_count_label = QLabel("Nenhum efeito tocando")
        bottom_row.addWidget(self.active_count_label, stretch=1)
        self.stop_all_button = QPushButton("🔇 Parar tudo")
        self.stop_all_button.clicked.connect(self.player_service.stop_all)
        bottom_row.addWidget(self.stop_all_button)
        bottom_layout.addLayout(bottom_row)
        central_layout.addWidget(bottom_bar)

        layout.addWidget(central, stretch=1)

        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)

    def _connect_signals(self) -> None:
        self.filters_panel.filters_changed.connect(self.refresh_library)
        self.filters_panel.manage_categories_button.clicked.connect(self._on_manage_categories)

        self.library_panel.search_changed.connect(lambda _: self.refresh_library())
        self.library_panel.play_requested.connect(self._on_play)
        self.library_panel.favorite_toggle_requested.connect(self._on_toggle_favorite)
        self.library_panel.tags_edited.connect(self._on_tags_edited)
        self.library_panel.category_change_requested.connect(self._on_category_change_requested)
        self.library_panel.hotkey_assign_requested.connect(self._on_hotkey_assign_requested)
        self.library_panel.add_to_pack_requested.connect(self._on_add_to_pack)
        self.library_panel.simultaneous_toggled.connect(self.player_service.set_allow_simultaneous)
        self.library_panel.locate_file_requested.connect(self._on_locate_file)
        self.library_panel.remove_from_library_requested.connect(self._on_remove_from_library_with_confirm)

        self.pack_panel.pack_selected.connect(self._on_pack_selected)
        self.pack_panel.new_pack_requested.connect(self._on_new_pack)
        self.pack_panel.remove_item_requested.connect(self._on_remove_item)
        self.pack_panel.move_item_requested.connect(self._on_move_item)
        self.pack_panel.reorder_requested.connect(self._on_reorder_items)
        self.pack_panel.play_item_requested.connect(self._on_play)
        self.pack_panel.export_requested.connect(self._on_export)

        self.player_service.active_count_changed.connect(self._on_active_count_changed)
        self.player_service.playback_error.connect(self._on_playback_error)

    def set_module_active(self, active: bool) -> None:
        """Chamado pelo shell do Studio ao trocar de página (item 32: evita
        hotkeys do módulo dispararem quando ele não está em primeiro
        plano)."""
        self._is_active = active

    def _typing_in_text_field(self) -> bool:
        return isinstance(QApplication.focusWidget(), QLineEdit)

    # ------------------------------------------------------------------
    # Hotkeys (item 44)
    # ------------------------------------------------------------------

    def _rebuild_hotkey_shortcuts(self) -> None:
        for shortcut in self._hotkey_shortcuts.values():
            shortcut.setParent(None)
            shortcut.deleteLater()
        self._hotkey_shortcuts.clear()

        for key in self.hotkey_repo.get_map():
            shortcut = QShortcut(QKeySequence(key), self)
            # Restrito a este widget (e filhos): dentro do Studio, outras
            # páginas não devem disparar hotkeys de efeitos do módulo SFX.
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(lambda k=key: self._on_hotkey_triggered(k))
            self._hotkey_shortcuts[key] = shortcut

    def _on_hotkey_triggered(self, key: str) -> None:
        if not self._is_active or self._typing_in_text_field():
            return
        track_id = self.hotkey_repo.get_map().get(key)
        if track_id is None:
            return
        track = self.track_repo.get_by_id(track_id)
        if track:
            self._on_play(track)

    # ------------------------------------------------------------------
    # Biblioteca / escaneamento
    # ------------------------------------------------------------------

    def _restore_last_library(self) -> None:
        saved_path = self.settings_repo.get(_SETTINGS_KEY_LIBRARY_PATH)
        if not saved_path:
            return
        if Path(saved_path).is_dir():
            self._current_library_root_id = self.library_root_repo.get_or_create(saved_path)
            self._rescan_action.setEnabled(True)
            self.refresh_library()
        else:
            # Item 16 da Etapa 6: pasta configurada sumiu — nunca crasha,
            # só avisa e deixa a ação "Selecionar pasta" disponível.
            self.status_bar.showMessage(
                f"A pasta da biblioteca de SFX não foi encontrada: {saved_path}. "
                "Selecione a pasta novamente na barra de ferramentas.",
                12000,
            )

    def _on_select_library_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Selecionar pasta da biblioteca de SFX")
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

        filt = SfxTrackFilter(
            search_text=self.library_panel.search_box.text(),
            library_root_id=self._current_library_root_id,
            category_id=self.filters_panel.selected_category_id,
            tag_ids=tuple(self.filters_panel.checked_tag_ids()),
            favorites_only=self.filters_panel.favorites_only,
            missing_only=self.filters_panel.missing_only,
            exclude_missing=not self.filters_panel.missing_only,
        )
        tracks = self.track_repo.find(filt)
        self.library_panel.set_tracks(tracks)
        self._reload_filter_options()

        stats = self.track_repo.stats(self._current_library_root_id)
        self.status_bar.showMessage(f"{stats['total']} efeito(s)  •  {stats['favorites']} favorito(s)")

    def _reload_filter_options(self) -> None:
        tags = self.tag_repo.list_all()
        categories = self.category_repo.list_all()
        self.filters_panel.set_tags(tags)
        self.filters_panel.set_categories(categories)
        self.library_panel.set_available_tags([t.name for t in tags])

    # ------------------------------------------------------------------
    # Ações da biblioteca
    # ------------------------------------------------------------------

    def _on_play(self, track: SfxTrack) -> None:
        self.player_service.play(track)
        self.track_repo.register_play(track.id)

    def _on_active_count_changed(self, count: int) -> None:
        self.active_count_label.setText(
            "Nenhum efeito tocando" if count == 0 else f"{count} efeito(s) tocando"
        )
        self.stop_all_button.setEnabled(count > 0)

    def _on_playback_error(self, message: str) -> None:
        self.status_bar.showMessage(f"⚠ Não foi possível reproduzir: {message}", 6000)

    def _on_toggle_favorite(self, track: SfxTrack) -> None:
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

    def _on_category_change_requested(self, track: SfxTrack) -> None:
        categories = self.category_repo.list_all()
        names = ["(sem categoria)"] + [c.name for c in categories]
        current = track.category_name or "(sem categoria)"
        name, ok = QInputDialog.getItem(
            self, "Mudar categoria", f"Categoria de “{track.title}”:", names,
            names.index(current) if current in names else 0, editable=True,
        )
        if not ok or not name.strip():
            return
        category_id = None if name == "(sem categoria)" else self.category_repo.get_or_create(name.strip()).id
        self.track_repo.set_category(track.id, category_id)
        updated = self.track_repo.get_by_id(track.id)
        if updated:
            self.library_panel.update_track_in_place(updated)
        self._reload_filter_options()

    def _on_hotkey_assign_requested(self, track: SfxTrack) -> None:
        hotkey_map = self.hotkey_repo.get_map()
        tracks_by_id = self.track_repo.get_many_by_ids(list(hotkey_map.values()))
        taken = {key: tracks_by_id[tid].title for key, tid in hotkey_map.items() if tid in tracks_by_id}

        dialog = HotkeyDialog(track.title, track.hotkey, taken, parent=self)
        if dialog.exec() != HotkeyDialog.DialogCode.Accepted:
            return

        key = dialog.selected_key()
        if key is None:
            self.hotkey_repo.clear(track.id)
        else:
            self.hotkey_repo.assign(track.id, key)

        updated = self.track_repo.get_by_id(track.id)
        if updated:
            self.library_panel.update_track_in_place(updated)
        self._rebuild_hotkey_shortcuts()

    def _on_locate_file(self, track: SfxTrack) -> None:
        initial_dir = str(Path(track.absolute_path).parent) if Path(track.absolute_path).parent.exists() else ""
        new_path, _ = QFileDialog.getOpenFileName(
            self, f"Localizar arquivo para “{track.title}”", initial_dir,
            "Arquivos de áudio (*.mp3 *.wav *.flac *.ogg *.m4a *.opus);;Todos os arquivos (*)",
        )
        if not new_path:
            return
        new_path_obj = Path(new_path)
        library_root = self.library_root_repo.get_path(track.library_root_id)
        try:
            relative = str(new_path_obj.relative_to(library_root)) if library_root else new_path_obj.name
        except ValueError:
            relative = new_path_obj.name
        self.track_repo.relocate(track.id, str(new_path_obj), relative)
        self.refresh_library()

    def _on_remove_from_library_with_confirm(self, track: SfxTrack) -> None:
        answer = QMessageBox.question(
            self, "Remover da biblioteca",
            f"Remover “{track.title}” da biblioteca?\n\n"
            "Isso não apaga nenhum arquivo, só o registro no programa "
            "(tags, favorito, hotkey e uso em packs também somem).",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.track_repo.delete(track.id)
        self.refresh_library()
        self._rebuild_hotkey_shortcuts()

    def _on_manage_categories(self) -> None:
        dialog = CategoryManagerDialog(self.category_repo, parent=self)
        dialog.exec()
        if dialog.changed:
            self._reload_filter_options()
            self.refresh_library()

    def _on_find_duplicates(self) -> None:
        if self._current_library_root_id is None:
            QMessageBox.information(self, "Nenhuma biblioteca", "Selecione uma pasta de biblioteca primeiro.")
            return
        tracks = self.track_repo.find(SfxTrackFilter(library_root_id=self._current_library_root_id))
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            groups = DuplicateService().find_duplicates(tracks)
        finally:
            QApplication.restoreOverrideCursor()

        dialog = DuplicatesDialog(groups, parent=self)
        dialog.remove_from_library_requested.connect(self._on_remove_track_from_library)
        dialog.exec()
        self.refresh_library()
        self._rebuild_hotkey_shortcuts()

    def _on_remove_track_from_library(self, track_id: int) -> None:
        self.track_repo.delete(track_id)

    # ------------------------------------------------------------------
    # Packs
    # ------------------------------------------------------------------

    def _reload_packs(self, select_id: int | None = None) -> None:
        packs = self.pack_repo.list_all()
        target = select_id or self._current_pack_id or (packs[0].id if packs else None)
        self.pack_panel.set_packs(packs, target)
        if target is not None:
            self._on_pack_selected(target)
        else:
            self.pack_panel.set_items([])

    def _on_new_pack(self) -> None:
        name, ok = QInputDialog.getText(self, "Novo Pack", "Nome do pack:")
        if not ok or not name.strip():
            return
        pack = self.pack_repo.create(name.strip())
        self._reload_packs(select_id=pack.id)

    def _on_pack_selected(self, pack_id: int) -> None:
        self._current_pack_id = pack_id
        items = self.pack_repo.get_items(pack_id)
        self.pack_panel.set_items(items)

    def _on_add_to_pack(self, track: SfxTrack) -> None:
        if self._current_pack_id is None:
            QMessageBox.information(
                self, "Nenhum pack selecionado",
                "Crie um pack primeiro (botão “＋ Novo”) antes de adicionar efeitos.",
            )
            return

        if self.pack_repo.has_track(self._current_pack_id, track.id):
            answer = QMessageBox.question(
                self, "Efeito já adicionado",
                f"“{track.title}” já está neste pack.\n\nAdicionar novamente?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        self.pack_repo.add_track(self._current_pack_id, track.id)
        self._on_pack_selected(self._current_pack_id)
        self._reload_packs(select_id=self._current_pack_id)

    def _on_remove_item(self, item_id: int) -> None:
        if self._current_pack_id is None:
            return
        self.pack_repo.remove_item(item_id, self._current_pack_id)
        self._on_pack_selected(self._current_pack_id)
        self._reload_packs(select_id=self._current_pack_id)

    def _on_move_item(self, item_id: int, direction: int) -> None:
        if self._current_pack_id is None:
            return
        self.pack_repo.move_item(self._current_pack_id, item_id, direction)
        self._on_pack_selected(self._current_pack_id)

    def _on_reorder_items(self, ordered_item_ids: list[int]) -> None:
        if self._current_pack_id is None:
            return
        self.pack_repo.reorder(self._current_pack_id, ordered_item_ids)
        self._on_pack_selected(self._current_pack_id)

    def _on_export(self) -> None:
        if self._current_pack_id is None:
            return
        pack = self.pack_repo.get(self._current_pack_id)
        items = self.pack_repo.get_items(self._current_pack_id)
        if not items or pack is None:
            QMessageBox.information(self, "Pack vazio", "Adicione efeitos antes de exportar.")
            return

        initial_conflict_policy = (
            self._default_conflict_policy_provider() if self._default_conflict_policy_provider else None
        )
        dialog = ExportDialog(
            pack.name, len(items), initial_conflict_policy=initial_conflict_policy, parent=self,
        )
        if dialog.exec() != ExportDialog.DialogCode.Accepted:
            return

        options: ExportOptions = dialog.export_options()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            report = self.export_service.export_pack(pack.name, items, options)
        finally:
            QApplication.restoreOverrideCursor()

        ExportReportDialog(report, parent=self).exec()

    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Encerramento explícito (chamado pelo wrapper standalone ao fechar
        a janela, ou pelo shell do Studio ao sair da aplicação).

        Cancela e espera um scan em andamento antes de fechar o banco —
        sem isso, a QThread do scanner podia continuar tentando consultar
        uma conexão sqlite já fechada (item 32: fechar o app durante um
        scan precisa ser seguro)."""
        if self._scanner is not None and self._scanner.isRunning():
            self._scanner.cancel()
            self._scanner.wait(3000)
        self.player_service.stop_all()
        self.db.close()

    # ------------------------------------------------------------------
    # API pública usada pela Home do RPG Audio Studio (ações rápidas)
    # ------------------------------------------------------------------

    def create_new_pack(self) -> None:
        self._on_new_pack()

    def select_library_folder(self) -> None:
        self._on_select_library_folder()

    def current_library_folder(self) -> str | None:
        return self.settings_repo.get(_SETTINGS_KEY_LIBRARY_PATH)

    def scan_folder(self, folder: Path) -> None:
        """Escaneia ``folder`` e passa a usá-la como pasta da biblioteca de
        SFX — usado pela primeira execução do Studio (item 15 da Etapa 6)
        pra não precisar reabrir um seletor de pasta que o usuário já usou."""
        self.settings_repo.set(_SETTINGS_KEY_LIBRARY_PATH, str(folder))
        self._start_scan(Path(folder))

    def set_default_conflict_policy_provider(self, provider: Callable[[], str]) -> None:
        """Usado pelo Studio (item 14 da Etapa 6) pra pré-selecionar o
        combo "se o arquivo já existir" do diálogo de exportação com a
        preferência salva em Configurações."""
        self._default_conflict_policy_provider = provider
