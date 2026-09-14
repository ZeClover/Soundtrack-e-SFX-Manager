"""Modelo de tabela para a lista de músicas da biblioteca.

Usa o padrão model/view do Qt (em vez de um widget por linha) para lidar
com bibliotecas de milhares de arquivos sem perda de performance.
"""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from app.models import Track
from rpg_audio_shared.formatting import format_duration

TrackIdRole = Qt.ItemDataRole.UserRole + 1
TrackObjectRole = Qt.ItemDataRole.UserRole + 2

_COLUMNS = ("★", "Título", "Artista", "Duração", "Tags", "Pasta")


class TrackTableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tracks: list[Track] = []

    def set_tracks(self, tracks: list[Track]) -> None:
        self.beginResetModel()
        self._tracks = tracks
        self.endResetModel()

    def track_at(self, row: int) -> Track | None:
        if 0 <= row < len(self._tracks):
            return self._tracks[row]
        return None

    def all_tracks(self) -> list[Track]:
        return list(self._tracks)

    def row_of_track_id(self, track_id: int) -> int:
        for i, track in enumerate(self._tracks):
            if track.id == track_id:
                return i
        return -1

    def update_track(self, track: Track) -> None:
        row = self.row_of_track_id(track.id)
        if row == -1:
            return
        self._tracks[row] = track
        top_left = self.index(row, 0)
        bottom_right = self.index(row, len(_COLUMNS) - 1)
        self.dataChanged.emit(top_left, bottom_right)

    # ------------------------------------------------------------------
    # QAbstractTableModel
    # ------------------------------------------------------------------

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._tracks)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(_COLUMNS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return _COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        track = self._tracks[index.row()]
        col = index.column()

        if role == TrackIdRole:
            return track.id
        if role == TrackObjectRole:
            return track

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return "★" if track.is_favorite else ""
            if col == 1:
                return track.title
            if col == 2:
                return track.artist or ""
            if col == 3:
                return format_duration(track.duration_seconds)
            if col == 4:
                return ", ".join(track.tags)
            if col == 5:
                return str(track.relative_path).rsplit("/", 1)[0] if "/" in track.relative_path else ""
            return None

        if role == Qt.ItemDataRole.ForegroundRole and track.is_missing:
            from PySide6.QtGui import QColor
            return QColor("#e0555a")

        if role == Qt.ItemDataRole.ToolTipRole:
            tooltip = track.absolute_path
            if track.is_missing:
                tooltip += "\n⚠ Arquivo não encontrado"
            if track.note:
                tooltip += f"\n\n{track.note}"
            return tooltip

        return None
