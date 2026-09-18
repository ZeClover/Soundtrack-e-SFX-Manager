"""Player de áudio integrado, construído sobre QMediaPlayer/QAudioOutput.

Toda comunicação com a UI acontece via signals — a UI nunca deve chamar
:class:`QMediaPlayer` diretamente, apenas este serviço.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from soundtrack_app.models import Track
from soundtrack_app.services.playlist_cursor import PlaylistCursor

logger = logging.getLogger(__name__)


class PlayerService(QObject):
    track_changed = Signal(object)  # Track | None
    position_changed = Signal(int)  # milissegundos
    duration_changed = Signal(int)  # milissegundos
    playing_changed = Signal(bool)
    volume_changed = Signal(int)  # 0-100
    muted_changed = Signal(bool)
    loop_changed = Signal(bool)
    track_finished_naturally = Signal(object)  # Track — para registrar histórico/play_count
    playback_error = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._cursor = PlaylistCursor()
        self._loop_current = False
        self._suppress_finish_signal = False

        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(0.8)

        # Conectado via lambda (e não signal-a-signal direto): QMediaPlayer emite
        # posição/duração como qint64, incompatível na assinatura com Signal(int).
        self._player.positionChanged.connect(lambda pos: self.position_changed.emit(int(pos)))
        self._player.durationChanged.connect(lambda dur: self.duration_changed.emit(int(dur)))
        self._player.playbackStateChanged.connect(self._on_playback_state_changed)
        self._player.mediaStatusChanged.connect(self._on_media_status_changed)
        self._player.errorOccurred.connect(self._on_error)

    # ------------------------------------------------------------------
    # Playlist / seleção de faixa
    # ------------------------------------------------------------------

    def set_playlist(self, tracks: list[Track], start_index: int = 0, autoplay: bool = True) -> None:
        track = self._cursor.set_items(tracks, start_index)
        if track is not None:
            self._load_and_play(track, autoplay=autoplay)
        else:
            self._player.stop()
            self.track_changed.emit(None)

    def current_track(self) -> Track | None:
        return self._cursor.current()

    def play_track_now(self, track: Track, playlist: list[Track] | None = None) -> None:
        if playlist is not None:
            self.set_playlist(playlist, start_index=_index_of(playlist, track.id), autoplay=True)
        else:
            self._load_and_play(track, autoplay=True)

    def toggle_play_pause(self) -> None:
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        elif self.current_track() is not None:
            self._player.play()
        elif self._cursor.current() is None and self._cursor.items:
            self.set_playlist(self._cursor.items, 0, autoplay=True)

    def stop(self) -> None:
        self._player.stop()

    def next_track(self) -> None:
        track = self._cursor.next()
        if track is not None:
            self._load_and_play(track, autoplay=True)

    def previous_track(self) -> None:
        track = self._cursor.previous()
        if track is not None:
            self._load_and_play(track, autoplay=True)

    # ------------------------------------------------------------------
    # Controles
    # ------------------------------------------------------------------

    def seek(self, position_ms: int) -> None:
        self._player.setPosition(position_ms)

    def set_volume(self, value_0_100: int) -> None:
        value_0_100 = max(0, min(100, value_0_100))
        self._audio_output.setVolume(value_0_100 / 100)
        self.volume_changed.emit(value_0_100)

    def set_muted(self, muted: bool) -> None:
        self._audio_output.setMuted(muted)
        self.muted_changed.emit(muted)

    def set_loop_current(self, loop: bool) -> None:
        self._loop_current = loop
        self.loop_changed.emit(loop)

    @property
    def is_playing(self) -> bool:
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _load_and_play(self, track: Track, *, autoplay: bool) -> None:
        path = Path(track.absolute_path)
        if not path.exists():
            self.playback_error.emit(f"Arquivo não encontrado: {track.title}")
            self.track_changed.emit(track)
            return

        self._player.setSource(QUrl.fromLocalFile(str(path)))
        self.track_changed.emit(track)
        if autoplay:
            self._player.play()

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        self.playing_changed.emit(state == QMediaPlayer.PlaybackState.PlayingState)

    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        if status != QMediaPlayer.MediaStatus.EndOfMedia:
            return

        finished_track = self._cursor.current()
        if finished_track is not None:
            self.track_finished_naturally.emit(finished_track)

        if self._loop_current and finished_track is not None:
            self._load_and_play(finished_track, autoplay=True)
            return

        # Item 17: ao terminar, toca a próxima da lista atual automaticamente.
        next_track = self._cursor.next()
        if next_track is not None:
            self._load_and_play(next_track, autoplay=True)

    def _on_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        if error == QMediaPlayer.Error.NoError:
            return
        logger.warning("Erro de reprodução: %s", error_string)
        self.playback_error.emit(error_string or "Não foi possível reproduzir este arquivo.")


def _index_of(tracks: list[Track], track_id: int) -> int:
    for i, t in enumerate(tracks):
        if t.id == track_id:
            return i
    return 0
