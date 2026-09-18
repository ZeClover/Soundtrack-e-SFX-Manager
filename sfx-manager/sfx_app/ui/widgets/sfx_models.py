"""Modelos de dados para as duas visualizações da biblioteca de SFX.

Modo cards (item 39) usa :class:`SfxCardModel` num ``QListView`` em modo
ícone; modo lista usa :class:`SfxTableModel` num ``QTableView``. Ambos são
baseados em model/view do Qt (não um widget por item), para continuar
responsivo com bibliotecas de milhares de efeitos (item 50).
"""

from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QAbstractTableModel, QModelIndex, Qt

from sfx_app.models import SfxTrack
from rpg_audio_shared.formatting import format_duration

TrackIdRole = Qt.ItemDataRole.UserRole + 1
TrackObjectRole = Qt.ItemDataRole.UserRole + 2

_LIST_COLUMNS = ("★", "Título", "Categoria", "Duração", "Tags", "Tecla")


class _SfxModelMixin:
    """Armazenamento e navegação comuns aos dois modelos (evita duplicar)."""

    def _init_tracks(self) -> None:
        self._tracks: list[SfxTrack] = []

    def set_tracks(self, tracks: list[SfxTrack]) -> None:
        self.beginResetModel()
        self._tracks = tracks
        self.endResetModel()

    def track_at(self, row: int) -> SfxTrack | None:
        if 0 <= row < len(self._tracks):
            return self._tracks[row]
        return None

    def all_tracks(self) -> list[SfxTrack]:
        return list(self._tracks)

    def row_of_track_id(self, track_id: int) -> int:
        for i, track in enumerate(self._tracks):
            if track.id == track_id:
                return i
        return -1

    def update_track(self, track: SfxTrack) -> None:
        row = self.row_of_track_id(track.id)
        if row == -1:
            return
        self._tracks[row] = track
        top_left = self.index(row, 0)
        # QAbstractListModel.columnCount() sempre retorna 1; QAbstractTableModel
        # retorna a quantidade real de colunas — funciona igual para os dois.
        bottom_right = self.index(row, self.columnCount() - 1)
        self.dataChanged.emit(top_left, bottom_right)


class SfxCardModel(_SfxModelMixin, QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_tracks()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._tracks)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        # QAbstractListModel.columnCount() herdado exige o argumento parent
        # explicitamente em PySide6 (sem default aplicado à implementação
        # C++ base) — declarar aqui evita um TypeError ao chamar
        # self.columnCount() sem argumentos (usado em update_track()).
        return 0 if parent.isValid() else 1

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        track = self._tracks[index.row()]
        if role == TrackIdRole:
            return track.id
        if role == TrackObjectRole:
            return track
        if role == Qt.ItemDataRole.DisplayRole:
            return track.title
        if role == Qt.ItemDataRole.ToolTipRole:
            tip = f"{track.title}  ({format_duration(track.duration_seconds)})"
            if track.category_name:
                tip += f"\n{track.category_name}"
            if track.hotkey:
                tip += f"\nTecla: {track.hotkey}"
            if track.is_missing:
                tip += "\n⚠ Arquivo não encontrado"
            return tip
        return None


class SfxTableModel(_SfxModelMixin, QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_tracks()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._tracks)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(_LIST_COLUMNS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return _LIST_COLUMNS[section]
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
                return track.category_name or ""
            if col == 3:
                return format_duration(track.duration_seconds)
            if col == 4:
                return ", ".join(track.tags)
            if col == 5:
                return track.hotkey or ""
            return None

        if role == Qt.ItemDataRole.ForegroundRole and track.is_missing:
            from PySide6.QtGui import QColor
            return QColor("#e0555a")

        return None
