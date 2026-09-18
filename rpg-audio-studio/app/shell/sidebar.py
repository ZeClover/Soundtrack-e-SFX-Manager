"""Barra de navegação lateral do RPG Audio Studio."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from app.config import APP_NAME


@dataclass(frozen=True)
class NavEntry:
    key: str
    label: str
    icon: str


# Música e Soundtracks vivem na mesma tela (o módulo Soundtrack já mostra
# biblioteca + soundtrack lado a lado); o mesmo vale para SFX + Packs. Menos
# itens na navegação, mas nenhuma tela existente precisou ser desmontada
# para caber aqui.
DEFAULT_NAV_ENTRIES: tuple[NavEntry, ...] = (
    NavEntry("home", "Home", "🏠"),
    NavEntry("music", "Música e Soundtracks", "🎵"),
    NavEntry("sfx", "SFX e Packs", "🔊"),
    NavEntry("downloader", "Downloader", "⬇"),
    NavEntry("history", "Histórico", "🕘"),
    NavEntry("settings", "Configurações", "⚙"),
)


class Sidebar(QWidget):
    navigate_requested = Signal(str)

    def __init__(self, entries: tuple[NavEntry, ...] = DEFAULT_NAV_ENTRIES, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(220)
        self._entries = list(entries)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel(APP_NAME.upper())
        title.setObjectName("SidebarTitle")
        title.setContentsMargins(18, 20, 18, 16)
        layout.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("SidebarList")
        self.list_widget.setFrameShape(QListWidget.Shape.NoFrame)
        for entry in self._entries:
            item = QListWidgetItem(f"{entry.icon}   {entry.label}")
            item.setData(Qt.ItemDataRole.UserRole, entry.key)
            self.list_widget.addItem(item)
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self.list_widget, stretch=1)

    def _on_row_changed(self, row: int) -> None:
        if row < 0:
            return
        self.navigate_requested.emit(self._entries[row].key)

    def set_current(self, key: str) -> None:
        for row, entry in enumerate(self._entries):
            if entry.key == key:
                self.list_widget.blockSignals(True)
                self.list_widget.setCurrentRow(row)
                self.list_widget.blockSignals(False)
                return

    def keys(self) -> list[str]:
        return [entry.key for entry in self._entries]
