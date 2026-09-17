"""Player de efeitos sonoros: clique = toca na hora (item 38/43).

Diferente do player do Soundtrack Manager (uma faixa por vez, com
playlist), aqui cada clique dispara sua própria reprodução independente.
Quando "sons simultâneos" está ligado, vários efeitos podem tocar ao mesmo
tempo (ex.: chuva + trovão + passos); quando desligado, iniciar um efeito
novo para qualquer um que ainda esteja tocando.

Cada reprodução usa seu próprio QMediaPlayer/QAudioOutput (criados sob
demanda e descartados ao terminar) — não há uma "faixa atual" única como
no Soundtrack Manager.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from app.models import SfxTrack

logger = logging.getLogger(__name__)


class SfxPlayerService(QObject):
    playback_started = Signal(object)  # SfxTrack
    playback_error = Signal(str)
    active_count_changed = Signal(int)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._allow_simultaneous = True
        self._volume = 0.8
        self._active: list[QMediaPlayer] = []

    def set_allow_simultaneous(self, allow: bool) -> None:
        self._allow_simultaneous = allow

    def set_volume(self, value_0_100: int) -> None:
        self._volume = max(0, min(100, value_0_100)) / 100
        for player in self._active:
            output = player.audioOutput()
            if output is not None:
                output.setVolume(self._volume)

    @property
    def active_count(self) -> int:
        return len(self._active)

    def play(self, track: SfxTrack) -> None:
        path = Path(track.absolute_path)
        if not path.exists():
            self.playback_error.emit(f"Arquivo não encontrado: {track.title}")
            return

        if not self._allow_simultaneous:
            self.stop_all()

        player = QMediaPlayer(self)
        output = QAudioOutput(self)
        output.setVolume(self._volume)
        player.setAudioOutput(output)
        player.mediaStatusChanged.connect(lambda status, p=player: self._on_status_changed(p, status))
        player.errorOccurred.connect(lambda err, msg, p=player: self._on_error(p, msg))

        self._active.append(player)
        self.active_count_changed.emit(len(self._active))

        player.setSource(QUrl.fromLocalFile(str(path)))
        player.play()
        self.playback_started.emit(track)

    def stop_all(self) -> None:
        for player in list(self._active):
            player.stop()
        # stop() não dispara EndOfMedia — removemos explicitamente aqui.
        for player in list(self._active):
            self._remove(player)

    # ------------------------------------------------------------------

    def _on_status_changed(self, player: QMediaPlayer, status: QMediaPlayer.MediaStatus) -> None:
        if status in (QMediaPlayer.MediaStatus.EndOfMedia, QMediaPlayer.MediaStatus.InvalidMedia):
            self._remove(player)

    def _on_error(self, player: QMediaPlayer, message: str) -> None:
        if message:
            logger.warning("Erro de reprodução de SFX: %s", message)
            self.playback_error.emit(message)
        self._remove(player)

    def _remove(self, player: QMediaPlayer) -> None:
        if player in self._active:
            self._active.remove(player)
            self.active_count_changed.emit(len(self._active))
        player.stop()
        player.deleteLater()
