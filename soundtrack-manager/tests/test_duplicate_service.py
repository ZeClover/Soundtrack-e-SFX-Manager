"""Testes do detector de duplicados (item 47)."""

from __future__ import annotations

from pathlib import Path

from soundtrack_app.models import Track
from soundtrack_app.services.duplicate_service import DuplicateService


def _track(
    tmp_path: Path, id_: int, title: str, content: bytes, duration: float = 100, partial_hash: str = "h",
) -> Track:
    path = tmp_path / f"{id_}.mp3"
    path.write_bytes(content)
    return Track(
        id=id_, library_root_id=1, absolute_path=str(path), relative_path=path.name,
        filename=path.name, extension=".mp3", title=title, artist=None, album=None,
        duration_seconds=duration, file_size=len(content), partial_hash=partial_hash,
        has_embedded_cover=False, is_favorite=False, note="", is_missing=False, play_count=0,
        last_played_at=None, date_detected="now", updated_at="now",
    )


def test_confirmed_duplicate_when_content_is_byte_identical(tmp_path: Path):
    content = b"exatamente os mesmos bytes" * 100
    a = _track(tmp_path, 1, "Tema A", content, partial_hash="same")
    b = _track(tmp_path, 2, "Tema B (copia)", content, partial_hash="same")
    unrelated = _track(tmp_path, 3, "Outra Musica", b"conteudo bem diferente" * 50, partial_hash="other")

    groups = DuplicateService().find_duplicates([a, b, unrelated])

    confirmed = [g for g in groups if g.kind == "confirmed"]
    assert len(confirmed) == 1
    assert {t.id for t in confirmed[0].tracks} == {1, 2}
    # A faixa sem duplicata não aparece em nenhum grupo
    all_grouped_ids = {t.id for g in groups for t in g.tracks}
    assert 3 not in all_grouped_ids


def test_same_partial_hash_but_different_content_is_not_confirmed(tmp_path: Path):
    """Colisão de hash parcial (raro) não deve virar falso positivo confirmado."""
    a = _track(tmp_path, 1, "A", b"conteudo-1" * 100, partial_hash="colidiu")
    b = _track(tmp_path, 2, "B", b"conteudo-2-bem-diferente" * 100, partial_hash="colidiu")

    groups = DuplicateService().find_duplicates([a, b])

    assert all(g.kind != "confirmed" for g in groups)


def test_possible_duplicate_by_normalized_title(tmp_path: Path):
    a = _track(tmp_path, 1, "Battle Theme", b"aaa", partial_hash="h1")
    b = _track(tmp_path, 2, "  battle theme  ", b"bbb", partial_hash="h2")

    groups = DuplicateService().find_duplicates([a, b])

    possible = [g for g in groups if g.kind == "possible"]
    assert len(possible) == 1
    assert {t.id for t in possible[0].tracks} == {1, 2}


def test_possible_duplicate_by_size_and_duration(tmp_path: Path):
    a = _track(tmp_path, 1, "Nome Um", b"x" * 500, duration=120, partial_hash="h1")
    b = _track(tmp_path, 2, "Nome Completamente Diferente", b"y" * 500, duration=120, partial_hash="h2")

    groups = DuplicateService().find_duplicates([a, b])

    possible = [g for g in groups if g.kind == "possible"]
    assert len(possible) == 1
    assert {t.id for t in possible[0].tracks} == {1, 2}


def test_unique_tracks_produce_no_groups(tmp_path: Path):
    a = _track(tmp_path, 1, "Solo A", b"a" * 10, duration=10, partial_hash="ha")
    b = _track(tmp_path, 2, "Solo B", b"b" * 20, duration=20, partial_hash="hb")

    groups = DuplicateService().find_duplicates([a, b])

    assert groups == []


def test_missing_file_is_skipped_for_confirmed_but_can_still_be_possible(tmp_path: Path):
    content = b"conteudo" * 50
    present = _track(tmp_path, 1, "Musica X", content, partial_hash="same")
    missing = _track(tmp_path, 2, "Musica X", content, partial_hash="same")
    missing.is_missing = True
    Path(missing.absolute_path).unlink()

    groups = DuplicateService().find_duplicates([present, missing])

    # Sem poder ler o arquivo ausente, não há confirmação por hash completo...
    assert all(g.kind != "confirmed" for g in groups)
    # ...mas o título idêntico ainda os agrupa como "possível".
    possible = [g for g in groups if g.kind == "possible"]
    assert len(possible) == 1
    assert {t.id for t in possible[0].tracks} == {1, 2}
