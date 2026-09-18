"""Regressão (item 32 da unificação no RPG Audio Studio): fechar o app
enquanto um scan de verdade está rodando numa QThread separada não pode
derrubar o processo nem deixar a thread tentando usar um banco já fechado.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None


def _make_silent_mp3(path: Path, duration: float = 1.0) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-t", str(duration), "-codec:a", "libmp3lame", "-b:a", "64k", str(path),
        ],
        check=True, capture_output=True,
    )


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg não disponível neste ambiente")
def test_shutdown_while_real_scan_thread_is_running_does_not_raise(tmp_path: Path, qt_core_app, monkeypatch):
    from soundtrack_app.services import library_scanner as scanner_module
    from soundtrack_app.ui.main_window import MainWindow

    original_partial_hash = scanner_module.partial_hash

    def _slow_partial_hash(path):
        time.sleep(0.05)
        return original_partial_hash(path)

    monkeypatch.setattr(scanner_module, "partial_hash", _slow_partial_hash)

    library = tmp_path / "Musicas"
    library.mkdir()
    for i in range(15):
        _make_silent_mp3(library / f"faixa{i}.mp3")

    window = MainWindow(db_path=tmp_path / "test.db")

    # Mesma coisa que window._start_scan() faz internamente, só sem abrir o
    # ScanProgressDialog modal (que bloquearia este teste até o scan acabar
    # sozinho — o objetivo aqui é fechar o app ENQUANTO ele ainda roda).
    window._scanner = scanner_module.LibraryScanner(window.db, library, window)
    window._scanner.start()
    assert window._scanner.isRunning()  # de propósito: ainda está no meio do scan

    window.shutdown()  # não pode lançar, mesmo com a thread ainda viva no instante da chamada

    assert window._scanner.wait(3000)  # a thread termina logo em seguida (cancelada)


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg não disponível neste ambiente")
def test_shutdown_while_music_is_playing_does_not_raise(tmp_path: Path, qt_core_app):
    from soundtrack_app.ui.main_window import MainWindow

    library = tmp_path / "Musicas"
    library.mkdir()
    track_path = library / "faixa.mp3"
    _make_silent_mp3(track_path, duration=2.0)

    window = MainWindow(db_path=tmp_path / "test.db")
    from soundtrack_app.services.library_scanner import LibraryScanner

    scanner = LibraryScanner(window.db, library)
    results = []
    scanner.scan_finished.connect(results.append)
    scanner.run()
    window._on_scan_finished(results[0])

    tracks = window.library_panel.model.all_tracks()
    assert len(tracks) == 1
    window.player_service.play_track_now(tracks[0], playlist=tracks)

    window.shutdown()  # não pode lançar mesmo com música "tocando"
