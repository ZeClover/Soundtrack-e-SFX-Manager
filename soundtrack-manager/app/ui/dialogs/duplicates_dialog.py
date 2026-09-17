"""Diálogo do detector de duplicados (item 47).

Só identifica e mostra — nunca apaga nada automaticamente. O usuário decide,
faixa por faixa, se quer remover da biblioteca (o arquivo original nunca é
tocado, só o registro no banco).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from app.services.duplicate_service import DuplicateGroup
from rpg_audio_shared.formatting import format_duration, format_file_size

_TRACK_ID_ROLE = Qt.ItemDataRole.UserRole + 1


class DuplicatesDialog(QDialog):
    remove_from_library_requested = Signal(int)  # track_id

    def __init__(self, groups: list[DuplicateGroup], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Localizar duplicados")
        self.setMinimumSize(560, 480)

        layout = QVBoxLayout(self)

        confirmed = [g for g in groups if g.kind == "confirmed"]
        possible = [g for g in groups if g.kind == "possible"]

        summary = QLabel(
            f"{len(confirmed)} grupo(s) confirmado(s) (arquivos idênticos)  •  "
            f"{len(possible)} grupo(s) possível(is) (nome, tamanho ou duração parecidos)"
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        note = QLabel("Nada é apagado automaticamente. Remover só tira da biblioteca — o arquivo continua no disco.")
        note.setStyleSheet("color: #9aa0ad;")
        note.setWordWrap(True)
        layout.addWidget(note)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Faixa", "Pasta", "Duração", "Tamanho"])
        self.tree.setColumnWidth(0, 220)
        layout.addWidget(self.tree, stretch=1)

        if confirmed:
            self._add_section("DUPLICADO CONFIRMADO", confirmed, "#e0555a")
        if possible:
            self._add_section("POSSÍVEL DUPLICADO", possible, "#d9a441")
        if not groups:
            layout.addWidget(QLabel("Nenhum duplicado encontrado. 🎉"))

        actions_row = QHBoxLayout()
        remove_button = QPushButton("Remover da biblioteca")
        remove_button.clicked.connect(self._on_remove_selected)
        actions_row.addWidget(remove_button)
        actions_row.addStretch(1)
        layout.addLayout(actions_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.accept)
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.accept)
        layout.addWidget(buttons)

    def _add_section(self, label: str, groups: list[DuplicateGroup], color: str) -> None:
        header = QTreeWidgetItem([label])
        header.setFlags(Qt.ItemFlag.ItemIsEnabled)
        font = header.font(0)
        font.setBold(True)
        header.setFont(0, font)
        header.setForeground(0, QColor(color))
        self.tree.addTopLevelItem(header)
        header.setExpanded(True)

        for index, group in enumerate(groups, start=1):
            group_item = QTreeWidgetItem([f"Grupo {index} ({len(group.tracks)} arquivos)"])
            group_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            header.addChild(group_item)
            group_item.setExpanded(True)
            for track in group.tracks:
                child = QTreeWidgetItem([
                    track.title,
                    track.relative_path.rsplit("/", 1)[0] if "/" in track.relative_path else "",
                    format_duration(track.duration_seconds),
                    format_file_size(track.file_size),
                ])
                child.setData(0, _TRACK_ID_ROLE, track.id)
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Unchecked)
                group_item.addChild(child)

    def _on_remove_selected(self) -> None:
        track_ids = []

        def walk(item: QTreeWidgetItem) -> None:
            for i in range(item.childCount()):
                child = item.child(i)
                if child.checkState(0) == Qt.CheckState.Checked:
                    track_id = child.data(0, _TRACK_ID_ROLE)
                    if track_id is not None:
                        track_ids.append(track_id)
                walk(child)

        for i in range(self.tree.topLevelItemCount()):
            walk(self.tree.topLevelItem(i))

        for track_id in track_ids:
            self.remove_from_library_requested.emit(track_id)

        for track_id in track_ids:
            self._remove_item_by_track_id(track_id)

    def _remove_item_by_track_id(self, track_id: int) -> None:
        def walk(item: QTreeWidgetItem) -> bool:
            for i in range(item.childCount()):
                child = item.child(i)
                if child.data(0, _TRACK_ID_ROLE) == track_id:
                    item.removeChild(child)
                    return True
                if walk(child):
                    return True
            return False

        for i in range(self.tree.topLevelItemCount()):
            walk(self.tree.topLevelItem(i))
