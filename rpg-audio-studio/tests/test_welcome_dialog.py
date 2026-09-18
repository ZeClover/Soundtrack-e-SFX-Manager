from __future__ import annotations

from app.shell.welcome_dialog import WelcomeDialog


def test_folders_start_empty(qt_core_app):
    dialog = WelcomeDialog()
    assert dialog.music_folder() == ""
    assert dialog.sfx_folder() == ""
    assert dialog.downloads_folder() == ""


def test_choosing_a_folder_fills_the_field(qt_core_app, tmp_path, monkeypatch):
    dialog = WelcomeDialog()
    monkeypatch.setattr(
        "app.shell.welcome_dialog.QFileDialog.getExistingDirectory", lambda *a, **k: str(tmp_path)
    )
    dialog._choose_folder(dialog.music_edit, "Selecionar pasta de músicas")
    assert dialog.music_folder() == str(tmp_path)


def test_cancelling_the_picker_leaves_field_empty(qt_core_app, monkeypatch):
    dialog = WelcomeDialog()
    monkeypatch.setattr("app.shell.welcome_dialog.QFileDialog.getExistingDirectory", lambda *a, **k: "")
    dialog._choose_folder(dialog.sfx_edit, "Selecionar pasta de SFX")
    assert dialog.sfx_folder() == ""
