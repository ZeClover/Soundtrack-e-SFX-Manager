"""Exportação com seções (item 32): lista única (agrupada) ou subpastas por seção."""

from __future__ import annotations

from pathlib import Path

from soundtrack_app.models import SoundtrackSection, Track
from soundtrack_app.services.export_service import ExportOptions, ExportService

from export_test_helpers import _item, _make_track


def _section(section_id: int, name: str, position: int) -> SoundtrackSection:
    return SoundtrackSection(id=section_id, soundtrack_id=1, name=name, position=position)


def test_export_flat_mode_keeps_single_folder_but_respects_section_order(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    tema = _make_track(source_dir, "Tema")
    boss = _make_track(source_dir, "Boss")
    solta = _make_track(source_dir, "Solta")

    tema_section = _section(1, "Tema Principal", 1)
    boss_section = _section(2, "Boss", 2)

    # "items" já vem na ordem de exibição (sem seção primeiro): Solta, Tema, Boss.
    items = [
        _item(solta, 1, section_id=None),
        _item(tema, 2, section_id=tema_section.id),
        _item(boss, 3, section_id=boss_section.id),
    ]

    report = ExportService().export_soundtrack(
        "Darkrem", items, ExportOptions(destination_folder=dest_dir, section_mode="flat"),
        sections=[tema_section, boss_section],
    )

    assert report.exported_count == 3
    files = sorted(p.name for p in report.destination.iterdir())
    assert files == ["01 - Solta.mp3", "02 - Tema.mp3", "03 - Boss.mp3"]


def test_export_subfolders_mode_creates_one_folder_per_section(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    tema = _make_track(source_dir, "Tema")
    tema2 = _make_track(source_dir, "Tema2")
    boss = _make_track(source_dir, "Boss")
    solta = _make_track(source_dir, "Solta")

    tema_section = _section(1, "Tema Principal", 1)
    boss_section = _section(2, "Boss", 2)

    items = [
        _item(solta, 1, section_id=None),
        _item(tema, 2, section_id=tema_section.id),
        _item(tema2, 3, section_id=tema_section.id),
        _item(boss, 4, section_id=boss_section.id),
    ]

    report = ExportService().export_soundtrack(
        "Darkrem", items, ExportOptions(destination_folder=dest_dir, section_mode="subfolders"),
        sections=[tema_section, boss_section],
    )

    assert report.exported_count == 4

    root_files = sorted(p.name for p in report.destination.iterdir() if p.is_file())
    assert root_files == ["01 - Solta.mp3"]  # faixa sem seção fica na raiz

    tema_dir = report.destination / "Tema Principal"
    assert sorted(p.name for p in tema_dir.iterdir()) == ["01 - Tema.mp3", "02 - Tema2.mp3"]

    boss_dir = report.destination / "Boss"
    assert sorted(p.name for p in boss_dir.iterdir()) == ["01 - Boss.mp3"]


def test_export_subfolders_mode_without_sections_behaves_like_flat(tmp_path: Path):
    """Se a soundtrack não tem seções, "subpastas" não deve criar pasta nenhuma extra."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    track = _make_track(source_dir, "Solo")

    report = ExportService().export_soundtrack(
        "Teste", [_item(track, 1)],
        ExportOptions(destination_folder=dest_dir, section_mode="subfolders"),
        sections=[],
    )

    assert report.exported_count == 1
    assert (report.destination / "01 - Solo.mp3").exists()
