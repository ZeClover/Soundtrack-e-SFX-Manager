"""Histórico unificado (item 25): músicas, SFX e downloads recentes numa
única página com seções — sem virar um sistema complexo à parte."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGroupBox, QLabel, QScrollArea, QVBoxLayout, QWidget

from modules.history.data import (
    collect_recent_download_titles,
    collect_recent_music_titles,
    collect_recent_sfx_titles,
)


class _RecentListGroup(QGroupBox):
    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self._layout = QVBoxLayout(self)
        self._empty_label = QLabel("Nada por aqui ainda.")
        self._empty_label.setStyleSheet("color: #9aa0ad;")
        self._layout.addWidget(self._empty_label)

    def set_items(self, items: list[str]) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

        if not items:
            empty = QLabel("Nada por aqui ainda.")
            empty.setStyleSheet("color: #9aa0ad;")
            self._layout.addWidget(empty)
            return

        for title in items:
            self._layout.addWidget(QLabel(f"• {title}"))


class HistoryPage(QWidget):
    def __init__(self, parent=None, soundtrack_db_path=None, sfx_db_path=None):
        super().__init__(parent)
        # Só usados pelos testes automatizados (mesmo padrão do resto da
        # suíte) — em produção ficam None e cada módulo usa seu caminho
        # real de sempre.
        self._soundtrack_db_path = soundtrack_db_path
        self._sfx_db_path = sfx_db_path
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("Histórico")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        self._music_group = _RecentListGroup("Músicas ouvidas recentemente")
        self._sfx_group = _RecentListGroup("Efeitos tocados recentemente")
        self._downloads_group = _RecentListGroup("Downloads recentes")
        layout.addWidget(self._music_group)
        layout.addWidget(self._sfx_group)
        layout.addWidget(self._downloads_group)
        layout.addStretch(1)

    def on_page_shown(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        self._music_group.set_items(collect_recent_music_titles(db_path=self._soundtrack_db_path))
        self._sfx_group.set_items(collect_recent_sfx_titles(db_path=self._sfx_db_path))
        self._downloads_group.set_items(collect_recent_download_titles())
