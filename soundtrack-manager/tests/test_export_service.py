import shutil
import subprocess
from pathlib import Path

import pytest

from app.models import SoundtrackItem, Track
from app.services.export_service import ExportOptions, ExportService

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None


def _make_track(tmp_path: Path, name: str, suffix: str = ".mp3", content: bytes = b"fake") -> Track:
    path = tmp_path / f"{name}{suffix}"
    path.write_bytes(content)
    return Track(
        id=1, library_root_id=1, absolute_path=str(path), relative_path=path.name,
        filename=path.name, extension=suffix, title=name, artist=None, album=None,
        duration_seconds=10, file_size=len(content), partial_hash="h", has_embedded_cover=False,
        is_favorite=False, note="", is_missing=False, play_count=0, last_played_at=None,
        date_detected="now", updated_at="now",
    )


def _item(track: Track, position: int) -> SoundtrackItem:
    return SoundtrackItem(id=position, soundtrack_id=1, section_id=None, track_id=track.id, position=position, track=track)


def test_export_copies_files_with_numbering(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    t1 = _make_track(source_dir, "Tema Principal")
    t2 = _make_track(source_dir, "Boss Final")
    items = [_item(t1, 1), _item(t2, 2)]

    report = ExportService().export_soundtrack(
        "Darkrem", items, ExportOptions(destination_folder=dest_dir, numbering=True)
    )

    assert report.exported_count == 2
    assert not report.has_errors
    exported = sorted(p.name for p in report.destination.iterdir())
    assert exported == ["01 - Tema Principal.mp3", "02 - Boss Final.mp3"]
    assert (dest_dir / "Darkrem - Soundtrack").exists()
    # Arquivos originais continuam intactos
    assert t1.absolute_path and Path(t1.absolute_path).exists()


def test_export_never_touches_original_files(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    track = _make_track(source_dir, "Musica", content=b"original-bytes")
    original_bytes = Path(track.absolute_path).read_bytes()

    ExportService().export_soundtrack("Teste", [_item(track, 1)], ExportOptions(destination_folder=dest_dir))

    assert Path(track.absolute_path).read_bytes() == original_bytes


def test_export_handles_missing_source_file(tmp_path: Path):
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    track = _make_track(tmp_path, "Fantasma")
    Path(track.absolute_path).unlink()

    report = ExportService().export_soundtrack("X", [_item(track, 1)], ExportOptions(destination_folder=dest_dir))

    assert report.exported_count == 0
    assert report.has_errors
    assert "Fantasma" in report.errors[0]


def test_export_conflict_rename_creates_alternative_name(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    track = _make_track(source_dir, "Musica")

    options = ExportOptions(destination_folder=dest_dir, numbering=False, conflict_policy="rename")
    service = ExportService()
    service.export_soundtrack("Teste", [_item(track, 1)], options)
    report2 = service.export_soundtrack("Teste", [_item(track, 1)], options)

    names = sorted(p.name for p in report2.destination.iterdir())
    assert names == ["Musica (2).mp3", "Musica.mp3"]


def test_export_conflict_skip(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    track = _make_track(source_dir, "Musica")

    options = ExportOptions(destination_folder=dest_dir, numbering=False, conflict_policy="skip")
    service = ExportService()
    service.export_soundtrack("Teste", [_item(track, 1)], options)
    report2 = service.export_soundtrack("Teste", [_item(track, 1)], options)

    assert report2.exported_count == 0
    assert report2.skipped_count == 1


def test_export_conflict_overwrite(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    track = _make_track(source_dir, "Musica", content=b"v1")

    options = ExportOptions(destination_folder=dest_dir, numbering=False, conflict_policy="overwrite")
    service = ExportService()
    service.export_soundtrack("Teste", [_item(track, 1)], options)

    track.file_size = 2
    Path(track.absolute_path).write_bytes(b"v2-bytes")
    service.export_soundtrack("Teste", [_item(track, 1)], options)

    target = dest_dir / "Teste - Soundtrack" / "Musica.mp3"
    assert target.read_bytes() == b"v2-bytes"


def test_export_gives_friendly_error_when_ffmpeg_missing(tmp_path: Path, monkeypatch):
    """Item 58: erro amigável (não traceback cru) quando o FFmpeg não está instalado."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    track = _make_track(source_dir, "SemFFmpeg", suffix=".wav")

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("ffmpeg nao encontrado no PATH")

    monkeypatch.setattr("app.services.export_service.subprocess.run", fake_run)

    report = ExportService().export_soundtrack(
        "Teste", [_item(track, 1)],
        ExportOptions(destination_folder=dest_dir, numbering=False, convert_to_mp3=True),
    )

    assert report.exported_count == 0
    assert report.has_errors
    assert "FFmpeg não foi encontrado" in report.errors[0]
    assert "Traceback" not in report.errors[0]


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg não disponível neste ambiente")
def test_export_converts_to_mp3_when_requested(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    wav_path = source_dir / "efeito.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "1", str(wav_path)],
        check=True, capture_output=True,
    )
    track = Track(
        id=1, library_root_id=1, absolute_path=str(wav_path), relative_path=wav_path.name,
        filename=wav_path.name, extension=".wav", title="Efeito", artist=None, album=None,
        duration_seconds=1, file_size=wav_path.stat().st_size, partial_hash="h", has_embedded_cover=False,
        is_favorite=False, note="", is_missing=False, play_count=0, last_played_at=None,
        date_detected="now", updated_at="now",
    )

    report = ExportService().export_soundtrack(
        "Conv", [_item(track, 1)],
        ExportOptions(destination_folder=dest_dir, numbering=False, convert_to_mp3=True),
    )

    assert report.exported_count == 1
    assert (dest_dir / "Conv - Soundtrack" / "Efeito.mp3").exists()


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg não disponível neste ambiente")
def test_export_does_not_reencode_existing_mp3(tmp_path: Path):
    """Item 33: não recomprimir MP3 já existente ao 'converter para MP3'."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    track = _make_track(source_dir, "JaEhMp3", content=b"conteudo-mp3-original")

    report = ExportService().export_soundtrack(
        "Conv", [_item(track, 1)],
        ExportOptions(destination_folder=dest_dir, numbering=False, convert_to_mp3=True),
    )

    target = dest_dir / "Conv - Soundtrack" / "JaEhMp3.mp3"
    assert target.read_bytes() == b"conteudo-mp3-original"
    assert report.exported_count == 1
