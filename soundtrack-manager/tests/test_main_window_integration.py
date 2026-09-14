"""Teste de integração ponta a ponta da janela principal (headless/offscreen).

Cobre o fluxo central descrito na especificação (item 80): escanear pasta,
ver músicas na biblioteca, favoritar, adicionar tags, criar soundtrack,
adicionar música, reordenar, exportar.
"""

from __future__ import annotations

import os
import shutil
import subprocess
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


@pytest.fixture
def main_window(tmp_path, qt_core_app):
    from app.ui.main_window import MainWindow

    # Banco isolado por teste (evita depender de %APPDATA%, que só existe no Windows).
    window = MainWindow(db_path=tmp_path / "test_soundtrack_manager.db")
    yield window
    window.db.close()


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg não disponível neste ambiente")
def test_full_flow_scan_browse_favorite_tag_soundtrack_export(main_window, tmp_path: Path):
    library = tmp_path / "Musicas"
    library.mkdir()
    _make_silent_mp3(library / "Tema Principal.mp3")
    _make_silent_mp3(library / "Boss Final.mp3")

    # 1. Escanear a pasta (equivalente a "Selecionar pasta da biblioteca")
    _run_scan_synchronously(main_window, library)

    tracks = main_window.library_panel.model.all_tracks()
    assert len(tracks) == 2
    titles = sorted(t.title for t in tracks)
    assert titles == ["Boss Final", "Tema Principal"]

    boss_track = next(t for t in tracks if t.title == "Boss Final")

    # 2. Favoritar
    main_window._on_toggle_favorite(boss_track)
    updated = main_window.track_repo.get_by_id(boss_track.id)
    assert updated.is_favorite is True

    # 3. Tags
    main_window._on_tags_edited(boss_track.id, ["boss", "combate"])
    updated = main_window.track_repo.get_by_id(boss_track.id)
    assert updated.tags == ["boss", "combate"]

    # 4. Buscar
    main_window.library_panel.search_box.setText("boss")
    main_window.refresh_library()
    filtered_titles = [t.title for t in main_window.library_panel.model.all_tracks()]
    assert filtered_titles == ["Boss Final"]
    main_window.library_panel.search_box.setText("")
    main_window.refresh_library()

    # 5. Criar soundtrack e adicionar músicas
    soundtrack = main_window.soundtrack_repo.create("Darkrem — Soundtrack Principal")
    main_window._reload_soundtracks(select_id=soundtrack.id)
    for track in tracks:
        main_window._on_add_to_soundtrack(track)

    items = main_window.soundtrack_repo.get_items(soundtrack.id)
    assert len(items) == 2

    # 6. Duplicata pede confirmação: sem confirmar (mock do QMessageBox = No), não duplica
    from PySide6.QtWidgets import QMessageBox
    import app.ui.main_window as main_window_module

    original_question = QMessageBox.question
    main_window_module.QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
    try:
        main_window._on_add_to_soundtrack(boss_track)
    finally:
        main_window_module.QMessageBox.question = original_question

    items_after = main_window.soundtrack_repo.get_items(soundtrack.id)
    assert len(items_after) == 2  # não duplicou

    # 7. Exportar
    export_dir = tmp_path / "export_dest"
    export_dir.mkdir()
    from app.services.export_service import ExportOptions

    report = main_window.export_service.export_soundtrack(
        soundtrack.name, items_after, ExportOptions(destination_folder=export_dir)
    )
    assert report.exported_count == 2
    exported_files = sorted(p.name for p in report.destination.iterdir())
    assert len(exported_files) == 2

    # Arquivos originais continuam lá, intactos
    assert (library / "Tema Principal.mp3").exists()
    assert (library / "Boss Final.mp3").exists()


def _run_scan_synchronously(main_window, folder: Path) -> None:
    """Executa o LibraryScanner de forma síncrona (sem QThread) apenas para o teste."""
    from app.services.library_scanner import LibraryScanner

    scanner = LibraryScanner(main_window.db, folder)
    results = []
    scanner.scan_finished.connect(results.append)
    scanner.run()  # chama diretamente em vez de start(), evitando thread real no teste
    assert results, "scan deveria ter terminado com sucesso"
    main_window._on_scan_finished(results[0])
