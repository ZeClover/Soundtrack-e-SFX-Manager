"""Painel central: busca + biblioteca de SFX em modo cards ou lista (itens 38, 39, 43).

Clicar num card/linha toca o efeito imediatamente — sem tela nova, sem
confirmação (item 43). Menu de contexto dá acesso a favoritar, editar
tags/categoria, atribuir tecla e adicionar a um pack.
"""

from __future__ import annotations

from PySide6.QtCore import QItemSelectionModel, QStringListModel, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QCompleter,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListView,
    QMenu,
    QPushButton,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.models import SfxTrack
from app.ui.widgets.sfx_card_delegate import CARD_SIZE, SfxCardDelegate
from app.ui.widgets.sfx_models import SfxCardModel, SfxTableModel, TrackObjectRole

_SEARCH_DEBOUNCE_MS = 200


class SfxLibraryPanel(QWidget):
    search_changed = Signal(str)
    play_requested = Signal(object)  # SfxTrack
    favorite_toggle_requested = Signal(object)  # SfxTrack
    tags_edited = Signal(int, list)  # track_id, tag_names
    category_change_requested = Signal(object)  # SfxTrack
    hotkey_assign_requested = Signal(object)  # SfxTrack
    add_to_pack_requested = Signal(object)  # SfxTrack
    simultaneous_toggled = Signal(bool)
    locate_file_requested = Signal(object)  # SfxTrack
    remove_from_library_requested = Signal(object)  # SfxTrack

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Panel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Buscar por nome, categoria ou tag...")
        self.search_box.setClearButtonEnabled(True)
        top_row.addWidget(self.search_box, stretch=1)

        self._tags_completer = QCompleter([], self)
        self._tags_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        self.view_toggle_button = QPushButton("☰ Lista")
        self.view_toggle_button.setToolTip("Alternar entre cards e lista")
        self.view_toggle_button.clicked.connect(self._toggle_view_mode)
        top_row.addWidget(self.view_toggle_button)

        self.simultaneous_checkbox = QCheckBox("Sons simultâneos")
        self.simultaneous_checkbox.setChecked(True)
        self.simultaneous_checkbox.setToolTip("Permitir tocar vários efeitos ao mesmo tempo")
        self.simultaneous_checkbox.toggled.connect(self.simultaneous_toggled)
        top_row.addWidget(self.simultaneous_checkbox)

        layout.addLayout(top_row)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(_SEARCH_DEBOUNCE_MS)
        self._debounce.timeout.connect(lambda: self.search_changed.emit(self.search_box.text()))
        self.search_box.textChanged.connect(lambda _: self._debounce.start())

        self.card_model = SfxCardModel(self)
        self.table_model = SfxTableModel(self)

        self.card_view = QListView()
        self.card_view.setModel(self.card_model)
        self.card_view.setViewMode(QListView.ViewMode.IconMode)
        self.card_view.setResizeMode(QListView.ResizeMode.Adjust)
        self.card_view.setMovement(QListView.Movement.Static)
        self.card_view.setUniformItemSizes(True)
        self.card_view.setGridSize(CARD_SIZE)
        self.card_view.setItemDelegate(SfxCardDelegate(self))
        self.card_view.setSpacing(4)
        self.card_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.card_view.doubleClicked.connect(self._on_card_activated)
        self.card_view.clicked.connect(self._on_card_clicked)
        self.card_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.card_view.customContextMenuRequested.connect(self._show_card_context_menu)

        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_view.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_view.doubleClicked.connect(self._on_table_activated)
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._show_table_context_menu)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.card_view)
        self.stack.addWidget(self.table_view)
        layout.addWidget(self.stack, stretch=1)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #9aa0ad;")
        layout.addWidget(self.status_label)

        self._card_mode = True

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def set_tracks(self, tracks: list[SfxTrack]) -> None:
        self.card_model.set_tracks(tracks)
        self.table_model.set_tracks(tracks)
        self.status_label.setText(f"{len(tracks)} efeito(s)")

    def set_available_tags(self, names: list[str]) -> None:
        self._tags_completer.setModel(QStringListModel(names, self._tags_completer))

    def all_tracks(self) -> list[SfxTrack]:
        return self.card_model.all_tracks()

    def update_track_in_place(self, track: SfxTrack) -> None:
        self.card_model.update_track(track)
        self.table_model.update_track(track)

    def selected_tracks(self) -> list[SfxTrack]:
        if self._card_mode:
            indexes = self.card_view.selectionModel().selectedIndexes()
            return [self.card_model.data(i, TrackObjectRole) for i in indexes if i.isValid()]
        rows = {i.row() for i in self.table_view.selectionModel().selectedRows()}
        return [self.table_model.track_at(r) for r in sorted(rows) if self.table_model.track_at(r)]

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _toggle_view_mode(self) -> None:
        self._card_mode = not self._card_mode
        self.stack.setCurrentIndex(0 if self._card_mode else 1)
        self.view_toggle_button.setText("☰ Lista" if self._card_mode else "▦ Cards")

    def _on_card_clicked(self, index) -> None:
        track = self.card_model.data(index, TrackObjectRole)
        if track:
            self.play_requested.emit(track)

    def _on_card_activated(self, index) -> None:
        track = self.card_model.data(index, TrackObjectRole)
        if track:
            self.play_requested.emit(track)

    def _on_table_activated(self, index) -> None:
        track = self.table_model.data(index, TrackObjectRole)
        if track:
            self.play_requested.emit(track)

    def _show_card_context_menu(self, pos) -> None:
        index = self.card_view.indexAt(pos)
        if not index.isValid():
            return
        track = self.card_model.data(index, TrackObjectRole)
        self._show_context_menu(track, self.card_view.viewport().mapToGlobal(pos))

    def _show_table_context_menu(self, pos) -> None:
        index = self.table_view.indexAt(pos)
        if not index.isValid():
            return
        track = self.table_model.data(index, TrackObjectRole)
        self._show_context_menu(track, self.table_view.viewport().mapToGlobal(pos))

    def _show_context_menu(self, track: SfxTrack, global_pos) -> None:
        menu = QMenu(self)

        if track.is_missing:
            locate_action = menu.addAction("Localizar arquivo...")
            remove_action = menu.addAction("Remover da biblioteca")
            chosen = menu.exec(global_pos)
            if chosen == locate_action:
                self.locate_file_requested.emit(track)
            elif chosen == remove_action:
                self.remove_from_library_requested.emit(track)
            return

        play_action = menu.addAction("▶ Tocar")
        fav_action = menu.addAction("★ Alternar favorito")
        tags_action = menu.addAction("Editar tags...")
        category_action = menu.addAction("Mudar categoria...")
        hotkey_action = menu.addAction("Atribuir tecla...")
        add_pack_action = menu.addAction("＋ Adicionar ao pack")
        chosen = menu.exec(global_pos)
        if chosen == play_action:
            self.play_requested.emit(track)
        elif chosen == fav_action:
            self.favorite_toggle_requested.emit(track)
        elif chosen == tags_action:
            self._prompt_tags(track)
        elif chosen == category_action:
            self.category_change_requested.emit(track)
        elif chosen == hotkey_action:
            self.hotkey_assign_requested.emit(track)
        elif chosen == add_pack_action:
            for t in self.selected_tracks() or [track]:
                self.add_to_pack_requested.emit(t)

    def _prompt_tags(self, track: SfxTrack) -> None:
        from PySide6.QtWidgets import QInputDialog

        current = ", ".join(track.tags)
        text, ok = QInputDialog.getText(
            self, "Editar tags", "Tags (separadas por vírgula):", text=current
        )
        if not ok:
            return
        names = [t.strip() for t in text.split(",") if t.strip()]
        self.tags_edited.emit(track.id, names)
