import shutil
import subprocess
from pathlib import Path

import pytest

from app.models import SfxPackItem, SfxTrack
from app.services.export_service import ExportOptions, ExportService

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None


def _make_track(tmp_path: Path, name: str, suffix: str = ".wav", content: bytes = b"fake") -> SfxTrack:
    path = tmp_path / f"{name}{suffix}"
    path.write_bytes(content)
    return SfxTrack(
        id=1, library_root_id=1, category_id=None, absolute_path=str(path), relative_path=path.name,
        filename=path.name, extension=suffix, title=name, duration_seconds=1, file_size=len(content),
        partial_hash="h", is_favorite=False, note="", is_missing=False, play_count=0,
        last_played_at=None, date_detected="now", updated_at="now",
    )


def _item(track: SfxTrack, position: int) -> SfxPackItem:
    return SfxPackItem(id=position, pack_id=1, track_id=track.id, position=position, track=track)


def test_export_copies_files_by_name(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    sword = _make_track(source_dir, "Sword Heavy")
    growl = _make_track(source_dir, "Monster Growl")

    report = ExportService().export_pack(
        "Darkrem Dungeon", [_item(sword, 1), _item(growl, 2)], ExportOptions(destination_folder=dest_dir)
    )

    assert report.exported_count == 2
    files = sorted(p.name for p in report.destination.iterdir())
    assert files == ["Monster Growl.wav", "Sword Heavy.wav"]
    assert (dest_dir / "Darkrem Dungeon SFX").exists()


def test_export_never_touches_original_files(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    track = _make_track(source_dir, "Efeito", content=b"conteudo-original")
    original_bytes = Path(track.absolute_path).read_bytes()

    ExportService().export_pack("Teste", [_item(track, 1)], ExportOptions(destination_folder=dest_dir))

    assert Path(track.absolute_path).read_bytes() == original_bytes


def test_export_handles_missing_source_file(tmp_path: Path):
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    track = _make_track(tmp_path, "Fantasma")
    Path(track.absolute_path).unlink()

    report = ExportService().export_pack("X", [_item(track, 1)], ExportOptions(destination_folder=dest_dir))

    assert report.exported_count == 0
    assert report.has_errors


def test_export_conflict_rename(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    track = _make_track(source_dir, "Efeito")

    options = ExportOptions(destination_folder=dest_dir, conflict_policy="rename")
    service = ExportService()
    service.export_pack("Teste", [_item(track, 1)], options)
    report2 = service.export_pack("Teste", [_item(track, 1)], options)

    names = sorted(p.name for p in report2.destination.iterdir())
    assert names == ["Efeito (2).wav", "Efeito.wav"]


def test_export_conflict_skip(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    track = _make_track(source_dir, "Efeito")

    options = ExportOptions(destination_folder=dest_dir, conflict_policy="skip")
    service = ExportService()
    service.export_pack("Teste", [_item(track, 1)], options)
    report2 = service.export_pack("Teste", [_item(track, 1)], options)

    assert report2.exported_count == 0
    assert report2.skipped_count == 1


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg não disponível neste ambiente")
def test_export_converts_wav_to_mp3(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    wav_path = source_dir / "efeito.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "1", str(wav_path)],
        check=True, capture_output=True,
    )
    track = SfxTrack(
        id=1, library_root_id=1, category_id=None, absolute_path=str(wav_path), relative_path="efeito.wav",
        filename="efeito.wav", extension=".wav", title="Efeito", duration_seconds=1,
        file_size=wav_path.stat().st_size, partial_hash="h", is_favorite=False, note="",
        is_missing=False, play_count=0, last_played_at=None, date_detected="now", updated_at="now",
    )

    report = ExportService().export_pack(
        "Conv", [_item(track, 1)], ExportOptions(destination_folder=dest_dir, export_format="mp3")
    )

    assert report.exported_count == 1
    assert (dest_dir / "Conv SFX" / "Efeito.mp3").exists()


def test_export_does_not_reconvert_already_correct_format(tmp_path: Path):
    """Item 46: manter formato quando já bate com o formato-alvo (sem recomprimir)."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    track = _make_track(source_dir, "JaEhWav", content=b"conteudo-wav-original")

    report = ExportService().export_pack(
        "Conv", [_item(track, 1)], ExportOptions(destination_folder=dest_dir, export_format="wav")
    )

    target = dest_dir / "Conv SFX" / "JaEhWav.wav"
    assert target.read_bytes() == b"conteudo-wav-original"
    assert report.exported_count == 1
