import shutil
import subprocess
from pathlib import Path

import pytest

from soundtrack_app.services.library_scanner import LibraryScanner

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None


def _make_silent_mp3(path: Path, duration: float = 1.0) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-t", str(duration), "-codec:a", "libmp3lame", "-b:a", "64k", str(path),
        ],
        check=True,
        capture_output=True,
    )


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg não disponível neste ambiente")
def test_scanner_detects_new_files(db, track_repo, tmp_path: Path):
    library = tmp_path / "Musicas"
    (library / "Combate").mkdir(parents=True)
    _make_silent_mp3(library / "tema.mp3")
    _make_silent_mp3(library / "Combate" / "boss.mp3")

    scanner = LibraryScanner(db, library)
    events = []
    scanner.scan_finished.connect(lambda result: events.append(result))
    scanner.run()

    assert len(events) == 1
    result = events[0]
    assert result.total_files_found == 2
    assert result.new_tracks == 2
    assert result.missing_tracks == 0

    tracks = track_repo.find(_all_filter())
    assert len(tracks) == 2
    relative_paths = sorted(t.relative_path for t in tracks)
    assert relative_paths == ["Combate/boss.mp3", "tema.mp3"]


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg não disponível neste ambiente")
def test_scanner_rescan_is_idempotent_and_detects_missing(db, track_repo, tmp_path: Path):
    library = tmp_path / "Musicas"
    library.mkdir()
    file_a = library / "a.mp3"
    file_b = library / "b.mp3"
    _make_silent_mp3(file_a)
    _make_silent_mp3(file_b)

    LibraryScanner(db, library).run()
    assert len(track_repo.find(_all_filter())) == 2

    # Segundo scan sem mudanças: nenhuma nova faixa
    scanner2 = LibraryScanner(db, library)
    results = []
    scanner2.scan_finished.connect(results.append)
    scanner2.run()
    assert results[0].new_tracks == 0
    assert results[0].missing_tracks == 0

    # Remove um arquivo e escaneia de novo: deve marcar como ausente, sem apagar do banco
    file_b.unlink()
    scanner3 = LibraryScanner(db, library)
    results3 = []
    scanner3.scan_finished.connect(results3.append)
    scanner3.run()
    assert results3[0].missing_tracks == 1

    active = track_repo.find(_all_filter())
    assert len(active) == 1
    missing = track_repo.find(_all_filter(missing_only=True))
    assert len(missing) == 1


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg não disponível neste ambiente")
def test_scanner_continues_after_bad_file(db, track_repo, tmp_path: Path):
    library = tmp_path / "Musicas"
    library.mkdir()
    good = library / "good.mp3"
    _make_silent_mp3(good)
    bad = library / "corrompido.mp3"
    bad.write_bytes(b"isto nao e um mp3 valido")

    scanner = LibraryScanner(db, library)
    results = []
    scanner.scan_finished.connect(results.append)
    scanner.run()

    # Arquivo corrompido ainda é indexado (fallback de metadados), sem interromper o scan
    assert results[0].total_files_found == 2
    assert len(track_repo.find(_all_filter())) == 2


def test_scanner_fails_gracefully_for_missing_root(db, tmp_path: Path):
    scanner = LibraryScanner(db, tmp_path / "nao-existe")
    failures = []
    scanner.scan_failed.connect(failures.append)
    scanner.run()
    assert len(failures) == 1


def _all_filter(missing_only: bool = False):
    from soundtrack_app.repositories import TrackFilter
    return TrackFilter(missing_only=missing_only)
