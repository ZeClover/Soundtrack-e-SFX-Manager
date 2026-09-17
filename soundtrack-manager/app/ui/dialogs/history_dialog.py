"""Diálogo de histórico de reprodução (item 68 — últimas músicas ouvidas)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from app.models import Track
from rpg_audio_shared.formatting import format_duration

_TRACK_ID_ROLE = Qt.ItemDataRole.UserRole + 1


class HistoryDialog(QDialog):
    play_requested = Signal(object)  # Track
    select_in_library_requested = Signal(object)  # Track

    def __init__(self, tracks: list[Track], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Histórico de reprodução")
        self.setMinimumSize(420, 480)
        self._tracks_by_id = {t.id: t for t in tracks}

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Últimas {len(tracks)} música(s) ouvidas:"))

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_double_clicked)
        for track in tracks:
            artist = f" — {track.artist}" if track.artist else ""
            text = f"{track.title}{artist}   ({format_duration(track.duration_seconds)})"
            item = QListWidgetItem(text)
            item.setData(_TRACK_ID_ROLE, track.id)
            if track.is_missing:
                item.setToolTip("Arquivo não encontrado")
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget, stretch=1)

        actions_row = QHBoxLayout()
        play_button = QPushButton("▶ Tocar")
        play_button.setObjectName("PrimaryButton")
        play_button.clicked.connect(self._on_play_clicked)
        actions_row.addWidget(play_button)
        select_button = QPushButton("Selecionar na biblioteca")
        select_button.clicked.connect(self._on_select_clicked)
        actions_row.addWidget(select_button)
        layout.addLayout(actions_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.accept)
        layout.addWidget(buttons)

    def _selected_track(self) -> Track | None:
        items = self.list_widget.selectedItems()
        if not items:
            return None
        return self._tracks_by_id.get(items[0].data(_TRACK_ID_ROLE))

    def _on_double_clicked(self, item: QListWidgetItem) -> None:
        track = self._tracks_by_id.get(item.data(_TRACK_ID_ROLE))
        if track:
            self.play_requested.emit(track)

    def _on_play_clicked(self) -> None:
        track = self._selected_track()
        if track:
            self.play_requested.emit(track)

    def _on_select_clicked(self) -> None:
        track = self._selected_track()
        if track:
            self.select_in_library_requested.emit(track)
            self.accept()
