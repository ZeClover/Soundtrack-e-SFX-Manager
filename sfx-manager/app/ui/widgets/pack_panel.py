"""Painel direito: pack de SFX atual (itens 45-46). Sem seções — mais simples que soundtracks."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.models import SfxPack, SfxPackItem
from rpg_audio_shared.formatting import format_duration

_ITEM_ID_ROLE = Qt.ItemDataRole.UserRole + 1
_TRACK_ID_ROLE = Qt.ItemDataRole.UserRole + 2


class PackPanel(QWidget):
    pack_selected = Signal(int)
    new_pack_requested = Signal()
    remove_item_requested = Signal(int)  # item_id
    move_item_requested = Signal(int, int)  # item_id, direction
    reorder_requested = Signal(list)  # lista ordenada de item_id
    play_item_requested = Signal(object)  # SfxTrack
    export_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setMinimumWidth(250)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self.pack_combo = QComboBox()
        self.pack_combo.currentIndexChanged.connect(self._on_combo_changed)
        header.addWidget(self.pack_combo, stretch=1)
        self.new_button = QPushButton("＋ Novo")
        self.new_button.clicked.connect(self.new_pack_requested)
        header.addWidget(self.new_button)
        layout.addLayout(header)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("color: #9aa0ad;")
        layout.addWidget(self.summary_label)

        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_widget.model().rowsMoved.connect(self._on_rows_moved)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.list_widget, stretch=1)

        actions_row = QHBoxLayout()
        self.remove_button = QPushButton("Remover")
        self.remove_button.clicked.connect(self._on_remove_clicked)
        actions_row.addWidget(self.remove_button)
        self.up_button = QPushButton("▲")
        self.up_button.setFixedWidth(36)
        self.up_button.clicked.connect(lambda: self._move_selected(-1))
        actions_row.addWidget(self.up_button)
        self.down_button = QPushButton("▼")
        self.down_button.setFixedWidth(36)
        self.down_button.clicked.connect(lambda: self._move_selected(1))
        actions_row.addWidget(self.down_button)
        layout.addLayout(actions_row)

        self.export_button = QPushButton("EXPORTAR PACK")
        self.export_button.setObjectName("PrimaryButton")
        self.export_button.clicked.connect(self.export_requested)
        layout.addWidget(self.export_button)

        self._loading = False
        self._items: list[SfxPackItem] = []

    def set_packs(self, packs: list[SfxPack], selected_id: int | None) -> None:
        self._loading = True
        self.pack_combo.clear()
        for pack in packs:
            self.pack_combo.addItem(f"{pack.name}  ({pack.track_count})", pack.id)
        if selected_id is not None:
            index = self.pack_combo.findData(selected_id)
            if index >= 0:
                self.pack_combo.setCurrentIndex(index)
        self._loading = False

    def set_items(self, items: list[SfxPackItem]) -> None:
        self._items = items
        self.list_widget.clear()
        total_seconds = 0.0
        for position, item in enumerate(items, start=1):
            track = item.track
            total_seconds += track.duration_seconds if track else 0
            title = track.title if track else "(arquivo removido)"
            text = f"{position:02d}. {title}"
            if track:
                text += f"   {format_duration(track.duration_seconds)}"
            list_item = QListWidgetItem(text)
            list_item.setData(_ITEM_ID_ROLE, item.id)
            list_item.setData(_TRACK_ID_ROLE, item.track_id)
            self.list_widget.addItem(list_item)

        count = len(items)
        self.summary_label.setText(f"{count} efeito(s) — {format_duration(total_seconds)}")
        self.export_button.setEnabled(count > 0)

    def current_pack_id(self) -> int | None:
        return self.pack_combo.currentData()

    def _on_combo_changed(self, _index: int) -> None:
        if self._loading:
            return
        pack_id = self.pack_combo.currentData()
        if pack_id is not None:
            self.pack_selected.emit(pack_id)

    def _selected_item_ids(self) -> list[int]:
        return [item.data(_ITEM_ID_ROLE) for item in self.list_widget.selectedItems()]

    def _on_remove_clicked(self) -> None:
        for item_id in self._selected_item_ids():
            self.remove_item_requested.emit(item_id)

    def _move_selected(self, direction: int) -> None:
        ids = self._selected_item_ids()
        if len(ids) == 1:
            self.move_item_requested.emit(ids[0], direction)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        track_id = item.data(_TRACK_ID_ROLE)
        track = next((i.track for i in self._items if i.track_id == track_id), None)
        if track:
            self.play_item_requested.emit(track)

    def _on_rows_moved(self, *_args) -> None:
        ordered_ids = [
            self.list_widget.item(i).data(_ITEM_ID_ROLE) for i in range(self.list_widget.count())
        ]
        self.reorder_requested.emit(ordered_ids)

    def _show_context_menu(self, pos) -> None:
        item = self.list_widget.itemAt(pos)
        if item is None:
            return
        menu = QMenu(self)
        play_action = menu.addAction("▶ Tocar")
        remove_action = menu.addAction("Remover do pack")
        chosen = menu.exec(self.list_widget.viewport().mapToGlobal(pos))
        track_id = item.data(_TRACK_ID_ROLE)
        if chosen == play_action:
            track = next((i.track for i in self._items if i.track_id == track_id), None)
            if track:
                self.play_item_requested.emit(track)
        elif chosen == remove_action:
            self.remove_item_requested.emit(item.data(_ITEM_ID_ROLE))
