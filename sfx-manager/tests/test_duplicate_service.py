"""Testes do detector de duplicados para SFX (item 47)."""

from __future__ import annotations

from pathlib import Path

from app.models import SfxTrack
from app.services.duplicate_service import DuplicateService


def _track(tmp_path: Path, id_: int, title: str, content: bytes, duration: float = 1, partial_hash: str = "h") -> SfxTrack:
    path = tmp_path / f"{id_}.wav"
    path.write_bytes(content)
    return SfxTrack(
        id=id_, library_root_id=1, category_id=None, absolute_path=str(path), relative_path=path.name,
        filename=path.name, extension=".wav", title=title, duration_seconds=duration, file_size=len(content),
        partial_hash=partial_hash, is_favorite=False, note="", is_missing=False, play_count=0,
        last_played_at=None, date_detected="now", updated_at="now",
    )


def test_confirmed_duplicate_when_content_is_byte_identical(tmp_path: Path):
    content = b"efeito-identico" * 50
    a = _track(tmp_path, 1, "Sword A", content, partial_hash="same")
    b = _track(tmp_path, 2, "Sword B (copia)", content, partial_hash="same")

    groups = DuplicateService().find_duplicates([a, b])
    confirmed = [g for g in groups if g.kind == "confirmed"]
    assert len(confirmed) == 1
    assert {t.id for t in confirmed[0].tracks} == {1, 2}


def test_possible_duplicate_by_title(tmp_path: Path):
    a = _track(tmp_path, 1, "Door Creak", b"aaa", partial_hash="h1")
    b = _track(tmp_path, 2, "  door creak  ", b"bbb", partial_hash="h2")

    groups = DuplicateService().find_duplicates([a, b])
    possible = [g for g in groups if g.kind == "possible"]
    assert len(possible) == 1


def test_unique_tracks_produce_no_groups(tmp_path: Path):
    a = _track(tmp_path, 1, "A", b"a" * 10, duration=1, partial_hash="ha")
    b = _track(tmp_path, 2, "B", b"b" * 20, duration=2, partial_hash="hb")
    assert DuplicateService().find_duplicates([a, b]) == []
