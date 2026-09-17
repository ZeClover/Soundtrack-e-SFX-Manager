import shutil
import subprocess
from pathlib import Path

import pytest

from app.services.library_scanner import LibraryScanner

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None


def _make_silent_wav(path: Path, duration: float = 0.5) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-t", str(duration), str(path),
        ],
        check=True,
        capture_output=True,
    )


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg não disponível neste ambiente")
def test_scanner_detects_new_files_and_assigns_category_from_folder(db, track_repo, category_repo, tmp_path: Path):
    library = tmp_path / "SFX"
    (library / "Espadas").mkdir(parents=True)
    _make_silent_wav(library / "Espadas" / "slash.wav")
    _make_silent_wav(library / "interface_click.wav")  # direto na raiz: sem categoria

    scanner = LibraryScanner(db, library)
    events = []
    scanner.scan_finished.connect(lambda result: events.append(result))
    scanner.run()

    assert len(events) == 1
    result = events[0]
    assert result.total_files_found == 2
    assert result.new_tracks == 2

    from app.repositories import SfxTrackFilter
    tracks = track_repo.find(SfxTrackFilter())
    assert len(tracks) == 2

    slash = next(t for t in tracks if "slash" in t.filename)
    click = next(t for t in tracks if "interface_click" in t.filename)
    assert slash.category_name == "Espadas"
    assert click.category_id is None

    categories = [c.name for c in category_repo.list_all()]
    assert categories == ["Espadas"]


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg não disponível neste ambiente")
def test_scanner_rescan_is_idempotent_and_detects_missing(db, track_repo, tmp_path: Path):
    library = tmp_path / "SFX"
    library.mkdir()
    file_a = library / "a.wav"
    file_b = library / "b.wav"
    _make_silent_wav(file_a)
    _make_silent_wav(file_b)

    LibraryScanner(db, library).run()
    assert len(track_repo.find(_all_filter())) == 2

    scanner2 = LibraryScanner(db, library)
    results = []
    scanner2.scan_finished.connect(results.append)
    scanner2.run()
    assert results[0].new_tracks == 0
    assert results[0].missing_tracks == 0

    file_b.unlink()
    scanner3 = LibraryScanner(db, library)
    results3 = []
    scanner3.scan_finished.connect(results3.append)
    scanner3.run()
    assert results3[0].missing_tracks == 1

    assert len(track_repo.find(_all_filter())) == 1
    assert len(track_repo.find(_all_filter(missing_only=True))) == 1


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg não disponível neste ambiente")
def test_scanner_continues_after_bad_file(db, track_repo, tmp_path: Path):
    library = tmp_path / "SFX"
    library.mkdir()
    good = library / "good.wav"
    _make_silent_wav(good)
    bad = library / "corrompido.wav"
    bad.write_bytes(b"isto nao e um wav valido")

    scanner = LibraryScanner(db, library)
    results = []
    scanner.scan_finished.connect(results.append)
    scanner.run()

    assert results[0].total_files_found == 2
    assert len(track_repo.find(_all_filter())) == 2


def test_scanner_fails_gracefully_for_missing_root(db, tmp_path: Path):
    scanner = LibraryScanner(db, tmp_path / "nao-existe")
    failures = []
    scanner.scan_failed.connect(failures.append)
    scanner.run()
    assert len(failures) == 1


def _all_filter(missing_only: bool = False):
    from app.repositories import SfxTrackFilter
    return SfxTrackFilter(missing_only=missing_only)
