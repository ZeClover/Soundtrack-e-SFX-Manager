"""Home do RPG Audio Studio: estatísticas rápidas + atalhos para os módulos.

Não conhece os módulos diretamente — só emite ``action_requested`` com um
código de ação; quem decide o que fazer com cada ação é a camada de
montagem (``main.py``), que é a única parte do Studio que conhece todos os
módulos ao mesmo tempo (item 16: sem acoplar regras de negócio entre
módulos).
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_NAME
from modules.home.stats import StudioStats, collect_stats


class _StatTile(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("Panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)

        self.value_label = QLabel("—")
        self.value_label.setStyleSheet("font-size: 26px; font-weight: 700;")
        layout.addWidget(self.value_label)

        caption = QLabel(title)
        caption.setStyleSheet("color: #9aa0ad;")
        layout.addWidget(caption)

    def set_value(self, value: int) -> None:
        self.value_label.setText(f"{value:,}".replace(",", "."))

    def set_unavailable(self) -> None:
        self.value_label.setText("—")


class HomePage(QWidget):
    action_requested = Signal(str)

    def __init__(self, parent=None, soundtrack_db_path=None, sfx_db_path=None):
        super().__init__(parent)
        # Só usados pelos testes automatizados, pra apontar pra bancos
        # isolados em tmp_path (mesmo padrão do resto da suíte) — em
        # produção ficam None e cada módulo usa seu caminho real de sempre.
        self._soundtrack_db_path = soundtrack_db_path
        self._sfx_db_path = sfx_db_path
        self._recent_downloads_provider: Callable[[], list[str]] | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(20)

        title = QLabel(APP_NAME)
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        layout.addWidget(title)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self._music_tile = _StatTile("Músicas na biblioteca")
        self._soundtrack_tile = _StatTile("Soundtracks")
        self._sfx_tile = _StatTile("Efeitos (SFX)")
        self._pack_tile = _StatTile("Packs de SFX")
        for tile in (self._music_tile, self._soundtrack_tile, self._sfx_tile, self._pack_tile):
            stats_row.addWidget(tile)
        layout.addLayout(stats_row)

        actions_label = QLabel("Ações rápidas")
        actions_label.setStyleSheet("font-size: 15px; font-weight: 600; margin-top: 8px;")
        layout.addWidget(actions_label)

        actions_grid = QGridLayout()
        actions_grid.setSpacing(10)
        actions = [
            ("Adicionar músicas", "add_music"),
            ("Abrir triagem", "triage"),
            ("Nova soundtrack", "new_soundtrack"),
            ("Abrir SFX", "open_sfx"),
            ("Nova pack de SFX", "new_pack"),
            ("Baixar playlist", "download_playlist"),
        ]
        for index, (label, code) in enumerate(actions):
            button = QPushButton(label)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.clicked.connect(lambda _checked=False, c=code: self.action_requested.emit(c))
            actions_grid.addWidget(button, index // 3, index % 3)
        layout.addLayout(actions_grid)

        recent_label = QLabel("Downloads recentes")
        recent_label.setStyleSheet("font-size: 15px; font-weight: 600; margin-top: 8px;")
        layout.addWidget(recent_label)

        self._recent_downloads_container = QVBoxLayout()
        self._recent_downloads_container.setSpacing(4)
        layout.addLayout(self._recent_downloads_container)
        self._recent_downloads_empty_label = QLabel("Nenhum download ainda.")
        self._recent_downloads_empty_label.setStyleSheet("color: #9aa0ad;")
        self._recent_downloads_container.addWidget(self._recent_downloads_empty_label)

        layout.addStretch(1)

    # ------------------------------------------------------------------

    def set_recent_downloads_provider(self, provider: Callable[[], list[str]]) -> None:
        self._recent_downloads_provider = provider

    def on_page_shown(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        stats = collect_stats(self._soundtrack_db_path, self._sfx_db_path)
        self._apply_stats(stats)
        self._refresh_recent_downloads()

    def _apply_stats(self, stats: StudioStats) -> None:
        if stats.music_available:
            self._music_tile.set_value(stats.music_count)
            self._soundtrack_tile.set_value(stats.soundtrack_count)
        else:
            self._music_tile.set_unavailable()
            self._soundtrack_tile.set_unavailable()

        if stats.sfx_available:
            self._sfx_tile.set_value(stats.sfx_count)
            self._pack_tile.set_value(stats.pack_count)
        else:
            self._sfx_tile.set_unavailable()
            self._pack_tile.set_unavailable()

    def _refresh_recent_downloads(self) -> None:
        while self._recent_downloads_container.count():
            item = self._recent_downloads_container.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

        items: list[str] = []
        if self._recent_downloads_provider is not None:
            try:
                items = self._recent_downloads_provider()
            except Exception:  # nunca deixa a Home quebrar por causa disso
                items = []

        if not items:
            empty = QLabel("Nenhum download ainda.")
            empty.setStyleSheet("color: #9aa0ad;")
            self._recent_downloads_container.addWidget(empty)
            return

        for entry in items[:5]:
            self._recent_downloads_container.addWidget(QLabel(f"• {entry}"))
