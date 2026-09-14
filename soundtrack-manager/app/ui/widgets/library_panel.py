"""Painel central: busca instantânea + lista da biblioteca + detalhes rápidos."""

from __future__ import annotations

from PySide6.QtCore import QItemSelectionModel, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.models import Track
from app.ui.widgets.track_table_model import TrackIdRole, TrackObjectRole, TrackTableModel

_SEARCH_DEBOUNCE_MS = 200


class LibraryPanel(QWidget):
    search_changed = Signal(str)
    selection_changed = Signal(object)  # Track | None
    play_requested = Signal(object)  # Track
    add_to_soundtrack_requested = Signal(object)  # Track (ou lista via seleção múltipla, ver get_selected_tracks)
    favorite_toggle_requested = Signal(object)  # Track
    tags_edited = Signal(int, list)  # track_id, tag_names
    note_edited = Signal(int, str)  # track_id, note

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Panel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        search_row = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Buscar por título, artista, tag, pasta, observação...")
        self.search_box.setClearButtonEnabled(True)
        search_row.addWidget(self.search_box)
        layout.addLayout(search_row)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(_SEARCH_DEBOUNCE_MS)
        self._debounce.timeout.connect(lambda: self.search_changed.emit(self.search_box.text()))
        self.search_box.textChanged.connect(lambda _: self._debounce.start())

        self.model = TrackTableModel(self)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 70)
        self.table.setColumnWidth(4, 160)
        self.table.setColumnWidth(5, 140)
        self.table.doubleClicked.connect(self._on_double_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.table, stretch=1)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #9aa0ad;")
        layout.addWidget(self.status_label)

        layout.addWidget(self._build_details_box())

        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self._current_track: Track | None = None

    # ------------------------------------------------------------------

    def _build_details_box(self) -> QWidget:
        box = QWidget()
        box.setObjectName("Panel")
        v = QVBoxLayout(box)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(6)

        header_row = QHBoxLayout()
        self.detail_title = QLabel("Selecione uma música")
        self.detail_title.setStyleSheet("font-weight: 600;")
        header_row.addWidget(self.detail_title, stretch=1)

        self.favorite_button = QPushButton("☆ Favoritar")
        self.favorite_button.clicked.connect(self._on_favorite_clicked)
        header_row.addWidget(self.favorite_button)

        self.add_button = QPushButton("＋ Adicionar à Soundtrack")
        self.add_button.setObjectName("PrimaryButton")
        self.add_button.clicked.connect(self._on_add_clicked)
        header_row.addWidget(self.add_button)
        v.addLayout(header_row)

        tags_row = QHBoxLayout()
        tags_row.addWidget(QLabel("Tags:"))
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("boss, combate, épico (separadas por vírgula)")
        self.tags_edit.editingFinished.connect(self._on_tags_edited)
        tags_row.addWidget(self.tags_edit)
        v.addLayout(tags_row)

        note_row = QHBoxLayout()
        note_row.addWidget(QLabel("Observação:"))
        self.note_edit = QPlainTextEdit()
        self.note_edit.setMaximumHeight(50)
        self.note_edit.setPlaceholderText("Ex.: usar quando os jogadores encontrarem o laboratório...")
        note_row.addWidget(self.note_edit)
        v.addLayout(note_row)
        self.note_edit.focusOutEvent = self._wrap_note_focus_out(self.note_edit.focusOutEvent)

        self._set_details_enabled(False)
        return box

    def _wrap_note_focus_out(self, original):
        def handler(event):
            original(event)
            self._on_note_edited()
        return handler

    def _set_details_enabled(self, enabled: bool) -> None:
        self.favorite_button.setEnabled(enabled)
        self.add_button.setEnabled(enabled)
        self.tags_edit.setEnabled(enabled)
        self.note_edit.setEnabled(enabled)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def set_tracks(self, tracks: list[Track]) -> None:
        selected_id = self._current_track.id if self._current_track else None
        self.model.set_tracks(tracks)
        self.status_label.setText(f"{len(tracks)} música(s)")
        if selected_id is not None:
            self.select_track_id(selected_id)

    def select_track_id(self, track_id: int) -> None:
        row = self.model.row_of_track_id(track_id)
        if row == -1:
            return
        index = self.model.index(row, 0)
        self.table.selectionModel().select(
            index,
            QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows,
        )
        self.table.scrollTo(index)

    def selected_track(self) -> Track | None:
        return self._current_track

    def selected_tracks(self) -> list[Track]:
        rows = {i.row() for i in self.table.selectionModel().selectedRows()}
        return [self.model.track_at(r) for r in sorted(rows) if self.model.track_at(r)]

    def update_track_in_place(self, track: Track) -> None:
        self.model.update_track(track)
        if self._current_track and self._current_track.id == track.id:
            self._current_track = track
            self._refresh_details(track)

    def move_selection(self, delta: int) -> None:
        rows = self.table.selectionModel().selectedRows()
        current_row = rows[0].row() if rows else -1
        new_row = max(0, min(current_row + delta, self.model.rowCount() - 1))
        if new_row == current_row and current_row != -1:
            return
        index = self.model.index(new_row, 0)
        self.table.selectionModel().select(
            index, QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows
        )
        self.table.setCurrentIndex(index)
        self.table.scrollTo(index)

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _on_selection_changed(self, *_args) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self._current_track = None
            self.detail_title.setText("Selecione uma música")
            self._set_details_enabled(False)
            self.selection_changed.emit(None)
            return
        track = self.model.data(rows[0], TrackObjectRole)
        self._current_track = track
        self._refresh_details(track)
        self.selection_changed.emit(track)

    def _refresh_details(self, track: Track) -> None:
        self._set_details_enabled(True)
        self.detail_title.setText(track.title + (" ⚠" if track.is_missing else ""))
        self.favorite_button.setText("★ Favorito" if track.is_favorite else "☆ Favoritar")
        self.tags_edit.blockSignals(True)
        self.tags_edit.setText(", ".join(track.tags))
        self.tags_edit.blockSignals(False)
        self.note_edit.blockSignals(True)
        self.note_edit.setPlainText(track.note)
        self.note_edit.blockSignals(False)

    def _on_double_clicked(self, index) -> None:
        track = self.model.data(index, TrackObjectRole)
        if track:
            self.play_requested.emit(track)

    def _on_favorite_clicked(self) -> None:
        if self._current_track:
            self.favorite_toggle_requested.emit(self._current_track)

    def _on_add_clicked(self) -> None:
        for track in self.selected_tracks() or ([self._current_track] if self._current_track else []):
            self.add_to_soundtrack_requested.emit(track)

    def _on_tags_edited(self) -> None:
        if not self._current_track:
            return
        names = [t.strip() for t in self.tags_edit.text().split(",") if t.strip()]
        self.tags_edited.emit(self._current_track.id, names)

    def _on_note_edited(self) -> None:
        if not self._current_track:
            return
        self.note_edited.emit(self._current_track.id, self.note_edit.toPlainText())

    def _show_context_menu(self, pos) -> None:
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        track = self.model.data(index, TrackObjectRole)
        menu = QMenu(self)
        play_action = menu.addAction("▶ Tocar")
        fav_action = menu.addAction("★ Alternar favorito")
        add_action = menu.addAction("＋ Adicionar à Soundtrack")
        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen == play_action:
            self.play_requested.emit(track)
        elif chosen == fav_action:
            self.favorite_toggle_requested.emit(track)
        elif chosen == add_action:
            for t in self.selected_tracks() or [track]:
                self.add_to_soundtrack_requested.emit(t)
