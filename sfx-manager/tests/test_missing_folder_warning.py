"""Regressão da Etapa 6 (item 16): se a pasta configurada da biblioteca de
SFX deixar de existir, o app não pode crashar — só avisar e deixar
escolher de novo."""

from __future__ import annotations

from pathlib import Path

from sfx_app.ui.main_window import MainWindow


def test_restore_last_library_with_missing_folder_does_not_crash_and_warns(tmp_path: Path, qt_core_app):
    window = MainWindow(db_path=tmp_path / "test.db")
    missing_folder = tmp_path / "pasta-que-nao-existe-mais"
    window.settings_repo.set("library_root_path", str(missing_folder))

    window._restore_last_library()

    assert window._current_library_root_id is None
    assert "não foi encontrada" in window.status_bar.currentMessage()
    window.shutdown()


def test_scan_folder_sets_library_and_scans(tmp_path: Path, qt_core_app):
    window = MainWindow(db_path=tmp_path / "test.db")
    library = tmp_path / "SFX"
    library.mkdir()

    window.scan_folder(library)

    assert window.current_library_folder() == str(library)
    window.shutdown()
