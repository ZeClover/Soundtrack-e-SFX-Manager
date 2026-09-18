"""Regressão (item 32 da unificação no RPG Audio Studio): fechar o app
enquanto um scan de verdade está rodando numa QThread separada, ou com um
efeito tocando, não pode derrubar o processo nem deixar a thread tentando
usar um banco já fechado."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None


def _make_silent_wav(path: Path, duration: float = 1.0) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-t", str(duration), str(path),
        ],
        check=True, capture_output=True,
    )


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg não disponível neste ambiente")
def test_shutdown_while_real_scan_thread_is_running_does_not_raise(tmp_path: Path, qt_core_app, monkeypatch):
    from sfx_app.services import library_scanner as scanner_module
    from sfx_app.ui.main_window import MainWindow

    original_partial_hash = scanner_module.partial_hash

    def _slow_partial_hash(path):
        time.sleep(0.05)
        return original_partial_hash(path)

    monkeypatch.setattr(scanner_module, "partial_hash", _slow_partial_hash)

    library = tmp_path / "SFX"
    (library / "Impactos").mkdir(parents=True)
    for i in range(15):
        _make_silent_wav(library / "Impactos" / f"efeito{i}.wav")

    window = MainWindow(db_path=tmp_path / "test.db")

    window._scanner = scanner_module.LibraryScanner(window.db, library, window)
    window._scanner.start()
    assert window._scanner.isRunning()

    window.shutdown()  # não pode lançar, mesmo com a thread ainda viva no instante da chamada

    assert window._scanner.wait(3000)


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg não disponível neste ambiente")
def test_shutdown_while_sfx_is_playing_does_not_raise(tmp_path: Path, qt_core_app):
    from sfx_app.services.library_scanner import LibraryScanner
    from sfx_app.ui.main_window import MainWindow

    library = tmp_path / "SFX"
    (library / "Impactos").mkdir(parents=True)
    _make_silent_wav(library / "Impactos" / "efeito.wav", duration=2.0)

    window = MainWindow(db_path=tmp_path / "test.db")

    scanner = LibraryScanner(window.db, library)
    results = []
    scanner.scan_finished.connect(results.append)
    scanner.run()
    window._on_scan_finished(results[0])

    tracks = window.library_panel.all_tracks()
    assert len(tracks) == 1
    window.player_service.play(tracks[0])

    window.shutdown()  # não pode lançar mesmo com efeito "tocando"


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg não disponível neste ambiente")
def test_shutdown_while_multiple_sfx_are_playing_simultaneously_does_not_raise(tmp_path: Path, qt_core_app):
    """Etapa 6 (item 64): "sons simultâneos" ligado é o caso mais exigente
    de fechar o app — vários QMediaPlayer/QAudioOutput ativos ao mesmo
    tempo, todos precisando parar sem lançar."""
    from sfx_app.services.library_scanner import LibraryScanner
    from sfx_app.ui.main_window import MainWindow

    library = tmp_path / "SFX"
    (library / "Impactos").mkdir(parents=True)
    for name in ("chuva", "trovao", "passos"):
        _make_silent_wav(library / "Impactos" / f"{name}.wav", duration=2.0)

    window = MainWindow(db_path=tmp_path / "test.db")

    scanner = LibraryScanner(window.db, library)
    results = []
    scanner.scan_finished.connect(results.append)
    scanner.run()
    window._on_scan_finished(results[0])

    tracks = window.library_panel.all_tracks()
    assert len(tracks) == 3

    window.player_service.set_allow_simultaneous(True)
    for track in tracks:
        window.player_service.play(track)
    assert window.player_service.active_count == 3

    window.shutdown()  # não pode lançar mesmo com 3 efeitos tocando ao mesmo tempo
