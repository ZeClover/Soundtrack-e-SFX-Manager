"""Testes do player de SFX: reprodução simultânea opcional (item 38)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from app.models import SfxTrack
from app.services.sfx_player_service import SfxPlayerService

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None


def _make_wav(path: Path, duration: float = 1.0) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", str(duration), str(path)],
        check=True, capture_output=True,
    )


def _track(id_: int, path: Path) -> SfxTrack:
    return SfxTrack(
        id=id_, library_root_id=1, category_id=None, absolute_path=str(path), relative_path=path.name,
        filename=path.name, extension=".wav", title=path.stem, duration_seconds=1, file_size=1,
        partial_hash="h", is_favorite=False, note="", is_missing=False, play_count=0,
        last_played_at=None, date_detected="now", updated_at="now",
    )


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg não disponível neste ambiente")
def test_simultaneous_playback_keeps_both_active(tmp_path: Path, qt_core_app):
    file_a, file_b = tmp_path / "a.wav", tmp_path / "b.wav"
    _make_wav(file_a)
    _make_wav(file_b)

    service = SfxPlayerService()
    service.set_allow_simultaneous(True)

    service.play(_track(1, file_a))
    assert service.active_count == 1
    service.play(_track(2, file_b))
    assert service.active_count == 2

    service.stop_all()
    assert service.active_count == 0


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg não disponível neste ambiente")
def test_single_voice_mode_stops_previous_before_playing_next(tmp_path: Path, qt_core_app):
    file_a, file_b = tmp_path / "a.wav", tmp_path / "b.wav"
    _make_wav(file_a)
    _make_wav(file_b)

    service = SfxPlayerService()
    service.set_allow_simultaneous(False)

    service.play(_track(1, file_a))
    assert service.active_count == 1
    service.play(_track(2, file_b))
    assert service.active_count == 1  # A foi parado antes de B começar


def test_missing_file_emits_error_without_crashing(qt_core_app):
    service = SfxPlayerService()
    errors = []
    service.playback_error.connect(errors.append)

    service.play(_track(1, Path("/nao/existe/nunca.wav")))

    assert service.active_count == 0
    assert len(errors) == 1
    assert "não encontrado" in errors[0]


def test_playback_started_signal_emits_the_track(tmp_path: Path, qt_core_app):
    if not FFMPEG_AVAILABLE:
        pytest.skip("ffmpeg não disponível")
    file_a = tmp_path / "a.wav"
    _make_wav(file_a)

    service = SfxPlayerService()
    started = []
    service.playback_started.connect(started.append)

    track = _track(1, file_a)
    service.play(track)

    assert len(started) == 1
    assert started[0].id == 1
