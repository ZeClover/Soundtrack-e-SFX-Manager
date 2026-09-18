"""Barra de player integrada na parte inferior da janela (item 17)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget

from soundtrack_app.models import Track
from soundtrack_app.services.player_service import PlayerService
from rpg_audio_shared.formatting import format_duration


class PlayerBar(QWidget):
    def __init__(self, player_service: PlayerService, parent=None):
        super().__init__(parent)
        self.setObjectName("Panel")
        self._player = player_service
        self._seeking = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 8, 14, 8)
        outer.setSpacing(4)

        self.now_playing_label = QLabel("Nenhuma música selecionada")
        self.now_playing_label.setStyleSheet("font-weight: 600;")
        outer.addWidget(self.now_playing_label)

        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.previous_button = QPushButton("⏮")
        self.previous_button.clicked.connect(self._player.previous_track)
        controls.addWidget(self.previous_button)

        self.play_pause_button = QPushButton("▶")
        self.play_pause_button.setFixedWidth(42)
        self.play_pause_button.clicked.connect(self._player.toggle_play_pause)
        controls.addWidget(self.play_pause_button)

        self.stop_button = QPushButton("⏹")
        self.stop_button.clicked.connect(self._player.stop)
        controls.addWidget(self.stop_button)

        self.next_button = QPushButton("⏭")
        self.next_button.clicked.connect(self._player.next_track)
        controls.addWidget(self.next_button)

        self.loop_button = QPushButton("🔁")
        self.loop_button.setCheckable(True)
        self.loop_button.setToolTip("Repetir faixa atual")
        self.loop_button.toggled.connect(self._player.set_loop_current)
        controls.addWidget(self.loop_button)

        self.position_label = QLabel("0:00")
        controls.addWidget(self.position_label)

        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderPressed.connect(lambda: setattr(self, "_seeking", True))
        self.seek_slider.sliderReleased.connect(self._on_seek_released)
        controls.addWidget(self.seek_slider, stretch=1)

        self.duration_label = QLabel("0:00")
        controls.addWidget(self.duration_label)

        self.mute_button = QPushButton("🔊")
        self.mute_button.setCheckable(True)
        self.mute_button.setFixedWidth(36)
        self.mute_button.toggled.connect(self._on_mute_toggled)
        controls.addWidget(self.mute_button)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(110)
        self.volume_slider.valueChanged.connect(self._player.set_volume)
        controls.addWidget(self.volume_slider)

        outer.addLayout(controls)

        self._player.track_changed.connect(self._on_track_changed)
        self._player.position_changed.connect(self._on_position_changed)
        self._player.duration_changed.connect(self._on_duration_changed)
        self._player.playing_changed.connect(self._on_playing_changed)
        self._player.playback_error.connect(self._on_playback_error)

    # ------------------------------------------------------------------

    def _on_track_changed(self, track: Track | None) -> None:
        if track is None:
            self.now_playing_label.setText("Nenhuma música selecionada")
        else:
            artist = f" — {track.artist}" if track.artist else ""
            self.now_playing_label.setText(f"{track.title}{artist}")

    def _on_position_changed(self, position_ms: int) -> None:
        if not self._seeking:
            self.seek_slider.setValue(position_ms)
        self.position_label.setText(format_duration(position_ms / 1000))

    def _on_duration_changed(self, duration_ms: int) -> None:
        self.seek_slider.setRange(0, max(duration_ms, 0))
        self.duration_label.setText(format_duration(duration_ms / 1000))

    def _on_playing_changed(self, playing: bool) -> None:
        self.play_pause_button.setText("⏸" if playing else "▶")

    def _on_seek_released(self) -> None:
        self._seeking = False
        self._player.seek(self.seek_slider.value())

    def _on_mute_toggled(self, muted: bool) -> None:
        self._player.set_muted(muted)
        self.mute_button.setText("🔇" if muted else "🔊")

    def _on_playback_error(self, message: str) -> None:
        self.now_playing_label.setText("⚠ Não foi possível reproduzir este arquivo.")
        self.now_playing_label.setToolTip(message)
