"""Fábricas compartilhadas entre os testes de exportação
(``test_export_service.py`` e ``test_export_sections.py``).

Este módulo deliberadamente NÃO começa com ``test_`` (então o pytest não
tenta coletá-lo) e é importado pelo nome simples (``import
export_test_helpers``), nunca como ``tests.export_test_helpers`` — o
monorepo tem uma pasta ``tests/`` em cada um dos quatro projetos
(``shared``, ``soundtrack-manager``, ``sfx-manager``, ``rpg-audio-studio``),
e um import absoluto começando com ``tests.`` pode resolver para a pasta
``tests/`` errada quando os testes de mais de um projeto rodam no mesmo
processo Python (por exemplo, `BUILD_WINDOWS.bat` chamando `pytest` várias
vezes a partir do mesmo diretório de trabalho) — o nome "tests" nesse caso
não é exclusivo dessa pasta.
"""

from __future__ import annotations

from pathlib import Path

from soundtrack_app.models import SoundtrackItem, Track


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


def _item(track: Track, position: int, section_id: int | None = None) -> SoundtrackItem:
    return SoundtrackItem(id=position, soundtrack_id=1, section_id=section_id, track_id=track.id, position=position, track=track)
