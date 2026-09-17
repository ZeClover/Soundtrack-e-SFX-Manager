"""Modo Triagem (item 67): tela focada em decidir rapidamente sobre muitas músicas.

Opera sobre a lista de faixas que for passada a ele (tipicamente a
biblioteca com os filtros atuais aplicados — ex.: "Não avaliadas"), tocando
automaticamente e avançando/voltando com o teclado, sem exigir cliques.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from app.models import Track
from app.services.player_service import PlayerService


class TriageDialog(QDialog):
    add_to_soundtrack_requested = Signal(object)  # Track
    favorite_toggle_requested = Signal(object)  # Track

    def __init__(self, tracks: list[Track], player_service: PlayerService, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Modo Triagem")
        self.setMinimumSize(480, 320)
        self._player = player_service
        self._tracks = list(tracks)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        now_playing_label = QLabel("TOCANDO AGORA")
        now_playing_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        now_playing_label.setStyleSheet("color: #9aa0ad; font-weight: 600; letter-spacing: 2px;")
        layout.addWidget(now_playing_label)

        self.title_label = QLabel("—")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-size: 22px; font-weight: 700;")
        layout.addWidget(self.title_label)

        self.artist_label = QLabel("")
        self.artist_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.artist_label.setStyleSheet("color: #9aa0ad; font-size: 14px;")
        layout.addWidget(self.artist_label)

        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setStyleSheet("color: #5a6070; font-size: 12px;")
        layout.addWidget(self.progress_label)

        layout.addStretch(1)

        buttons_row = QHBoxLayout()
        self.skip_button = QPushButton("✕ NÃO")
        self.skip_button.clicked.connect(self._on_skip)
        buttons_row.addWidget(self.skip_button)

        self.favorite_button = QPushButton("☆ FAVORITO")
        self.favorite_button.clicked.connect(self._on_favorite)
        buttons_row.addWidget(self.favorite_button)

        self.add_button = QPushButton("＋ ADICIONAR")
        self.add_button.setObjectName("PrimaryButton")
        self.add_button.clicked.connect(self._on_add)
        buttons_row.addWidget(self.add_button)
        layout.addLayout(buttons_row)

        layout.addStretch(1)

        nav_row = QHBoxLayout()
        self.previous_button = QPushButton("← Anterior")
        self.previous_button.clicked.connect(self._player.previous_track)
        nav_row.addWidget(self.previous_button)
        nav_row.addStretch(1)
        hint = QLabel("Espaço = pausar   •   ← →  navegar   •   A adicionar   •   F favoritar")
        hint.setStyleSheet("color: #5a6070; font-size: 11px;")
        nav_row.addWidget(hint)
        nav_row.addStretch(1)
        self.next_button = QPushButton("Próxima →")
        self.next_button.clicked.connect(self._player.next_track)
        nav_row.addWidget(self.next_button)
        layout.addLayout(nav_row)

        close_button = QPushButton("Fechar modo triagem")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self._player.track_changed.connect(self._on_track_changed)
        self._install_shortcuts()

        self._player.set_playlist(self._tracks, start_index=0, autoplay=bool(self._tracks))
        if not self._tracks:
            self.title_label.setText("Nenhuma música para revisar aqui.")

    def _install_shortcuts(self) -> None:
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, activated=self._player.toggle_play_pause)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, activated=self._player.next_track)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, activated=self._player.previous_track)
        QShortcut(QKeySequence(Qt.Key.Key_A), self, activated=self._on_add)
        QShortcut(QKeySequence(Qt.Key.Key_F), self, activated=self._on_favorite)

    def _current_track(self) -> Track | None:
        return self._player.current_track()

    def _on_track_changed(self, track: Track | None) -> None:
        if track is None:
            self.title_label.setText("—")
            self.artist_label.setText("")
            self.progress_label.setText("")
            return
        self.title_label.setText(track.title)
        self.artist_label.setText(track.artist or "")
        self.favorite_button.setText("★ FAVORITO" if track.is_favorite else "☆ FAVORITO")

        if track.id in {t.id for t in self._tracks}:
            position = next(i for i, t in enumerate(self._tracks) if t.id == track.id) + 1
            self.progress_label.setText(f"{position} / {len(self._tracks)}")

    def _on_skip(self) -> None:
        self._player.next_track()

    def _on_add(self) -> None:
        track = self._current_track()
        if track:
            self.add_to_soundtrack_requested.emit(track)

    def _on_favorite(self) -> None:
        track = self._current_track()
        if track is None:
            return
        track.is_favorite = not track.is_favorite
        self.favorite_button.setText("★ FAVORITO" if track.is_favorite else "☆ FAVORITO")
        self.favorite_toggle_requested.emit(track)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._player.track_changed.disconnect(self._on_track_changed)
        self._player.stop()
        super().closeEvent(event)
