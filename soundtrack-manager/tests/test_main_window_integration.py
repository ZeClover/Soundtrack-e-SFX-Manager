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
    from soundtrack_app.ui.main_window import MainWindow

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
    import soundtrack_app.ui.main_window as main_window_module

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
    from soundtrack_app.services.export_service import ExportOptions

    report = main_window.export_service.export_soundtrack(
        soundtrack.name, items_after, ExportOptions(destination_folder=export_dir)
    )
    assert report.exported_count == 2
    exported_files = sorted(p.name for p in report.destination.iterdir())
    assert len(exported_files) == 2

    # Arquivos originais continuam lá, intactos
    assert (library / "Tema Principal.mp3").exists()
    assert (library / "Boss Final.mp3").exists()


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg não disponível neste ambiente")
def test_close_and_reopen_preserves_data(tmp_path: Path, qt_core_app):
    """Item 29: fechar e reabrir o programa preserva biblioteca, favoritos, tags e soundtracks."""
    from soundtrack_app.ui.main_window import MainWindow

    library = tmp_path / "Musicas"
    library.mkdir()
    _make_silent_mp3(library / "Tema Principal.mp3")
    _make_silent_mp3(library / "Boss Final.mp3")

    db_path = tmp_path / "persist_test.db"

    # --- Primeira "sessão": escaneia, favorita, taggeia e cria soundtrack ---
    window1 = MainWindow(db_path=db_path)
    window1.settings_repo.set("library_root_path", str(library))
    _run_scan_synchronously(window1, library)

    tracks = window1.library_panel.model.all_tracks()
    boss = next(t for t in tracks if t.title == "Boss Final")
    window1._on_toggle_favorite(boss)
    window1._on_tags_edited(boss.id, ["boss", "combate"])
    window1._on_note_edited(boss.id, "Usar no confronto final.")

    soundtrack = window1.soundtrack_repo.create("Darkrem — Soundtrack Principal")
    window1._reload_soundtracks(select_id=soundtrack.id)
    for t in tracks:
        window1._on_add_to_soundtrack(t)

    window1.db.close()  # fecha o programa

    # --- Segunda "sessão": reabre apontando para o MESMO banco ---
    window2 = MainWindow(db_path=db_path)
    try:
        # _restore_last_library() já roda no __init__ e recarrega a última pasta
        reopened_tracks = window2.library_panel.model.all_tracks()
        assert len(reopened_tracks) == 2

        reopened_boss = next(t for t in reopened_tracks if t.title == "Boss Final")
        assert reopened_boss.is_favorite is True
        assert reopened_boss.tags == ["boss", "combate"]
        assert reopened_boss.note == "Usar no confronto final."

        soundtracks = window2.soundtrack_repo.list_all()
        assert len(soundtracks) == 1
        assert soundtracks[0].name == "Darkrem — Soundtrack Principal"
        assert soundtracks[0].track_count == 2
    finally:
        window2.db.close()


def test_manage_tags_refreshes_sidebar_autocomplete_and_keeps_selection(main_window, tmp_path: Path):
    """Regressão do gerenciador de tags: depois de renomear/excluir pelo
    diálogo, o filtro lateral e o autocomplete do campo de tags precisam
    refletir a mudança na hora, e a música selecionada continua selecionada."""
    root_id = main_window.library_root_repo.get_or_create(str(tmp_path))
    track_id = main_window.track_repo.upsert_from_scan(
        library_root_id=root_id, absolute_path=str(tmp_path / "boss.mp3"), relative_path="boss.mp3",
        filename="boss.mp3", extension=".mp3", title="Boss Final", artist=None, album=None,
        duration_seconds=10, file_size=100, partial_hash="h", has_embedded_cover=False,
    )
    main_window._current_library_root_id = root_id
    main_window._on_tags_edited(track_id, ["boss", "combate"])
    main_window.refresh_library()
    main_window.library_panel.select_track_id(track_id)

    assert main_window.library_panel.selected_track().id == track_id
    sidebar_names_before = {
        main_window.filters_panel.tags_list.item(i).text()
        for i in range(main_window.filters_panel.tags_list.count())
    }
    assert sidebar_names_before == {"boss", "combate"}

    from soundtrack_app.ui.dialogs.tag_manager_dialog import TagManagerDialog

    dialog = TagManagerDialog(main_window.tag_repo, parent=main_window)
    boss_tag = main_window.tag_repo.get_or_create("boss")
    dialog._tag_repo.rename(boss_tag.id, "chefão")
    dialog.changed = True

    # Mesmo caminho que main_window._on_manage_tags() segue depois de dialog.exec().
    main_window._reload_filter_options()
    main_window.refresh_library()

    sidebar_names_after = {
        main_window.filters_panel.tags_list.item(i).text()
        for i in range(main_window.filters_panel.tags_list.count())
    }
    assert sidebar_names_after == {"chefão", "combate"}  # filtro lateral atualizado

    autocomplete_names = main_window.library_panel._tags_completer.model().stringList()
    assert set(autocomplete_names) == {"chefão", "combate"}  # autocomplete atualizado

    # A música continua selecionada depois do refresh.
    assert main_window.library_panel.selected_track() is not None
    assert main_window.library_panel.selected_track().id == track_id
    assert sorted(main_window.library_panel.selected_track().tags) == ["chefão", "combate"]


def _run_scan_synchronously(main_window, folder: Path) -> None:
    """Executa o LibraryScanner de forma síncrona (sem QThread) apenas para o teste."""
    from soundtrack_app.services.library_scanner import LibraryScanner

    scanner = LibraryScanner(main_window.db, folder)
    results = []
    scanner.scan_finished.connect(results.append)
    scanner.run()  # chama diretamente em vez de start(), evitando thread real no teste
    assert results, "scan deveria ter terminado com sucesso"
    main_window._on_scan_finished(results[0])
