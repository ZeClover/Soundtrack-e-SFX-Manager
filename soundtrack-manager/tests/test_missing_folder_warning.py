"""Regressão da Etapa 6 (item 16): se a pasta configurada da biblioteca
deixar de existir, o app não pode crashar — só avisar e deixar escolher
de novo."""

from __future__ import annotations

from pathlib import Path

from soundtrack_app.ui.main_window import MainWindow


def test_restore_last_library_with_missing_folder_does_not_crash_and_warns(tmp_path: Path, qt_core_app):
    window = MainWindow(db_path=tmp_path / "test.db")
    missing_folder = tmp_path / "pasta-que-nao-existe-mais"
    window.settings_repo.set("library_root_path", str(missing_folder))

    # Chama de novo manualmente (o __init__ já rodou com a pasta ainda
    # inexistente por padrão, então força o cenário de forma explícita).
    window._restore_last_library()

    assert window._current_library_root_id is None
    assert "não foi encontrada" in window.status_bar.currentMessage()
    window.shutdown()


def test_restore_last_library_with_no_saved_path_does_nothing(tmp_path: Path, qt_core_app):
    window = MainWindow(db_path=tmp_path / "test.db")
    window._restore_last_library()
    assert window._current_library_root_id is None
    assert window.status_bar.currentMessage() == ""
    window.shutdown()
