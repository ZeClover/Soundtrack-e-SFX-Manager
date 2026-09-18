"""Regressão da Etapa 6 (item 15): a primeira execução só aparece uma vez,
nunca obriga a preencher nada, e aplica as pastas escolhidas sem reabrir
seletores de pasta."""

from __future__ import annotations

from pathlib import Path

import main as studio_main
from app.settings.settings_repository import KEY_DEFAULT_DOWNLOADS_FOLDER, KEY_FIRST_RUN_COMPLETED


def _build_window(tmp_path: Path):
    return studio_main.build_studio_window(
        soundtrack_db_path=tmp_path / "soundtrack.db",
        sfx_db_path=tmp_path / "sfx.db",
        studio_settings_db_path=tmp_path / "studio.db",
    )


class _FakeWelcomeDialog:
    DialogCode = type("DialogCode", (), {"Accepted": 1, "Rejected": 0})

    def __init__(self, result, music="", sfx="", downloads=""):
        self._result = result
        self._music = music
        self._sfx = sfx
        self._downloads = downloads

    def exec(self):
        return self._result

    def music_folder(self):
        return self._music

    def sfx_folder(self):
        return self._sfx

    def downloads_folder(self):
        return self._downloads


def _fake_dialog_factory(result, music="", sfx="", downloads=""):
    """``main.py`` referencia ``WelcomeDialog.DialogCode.Accepted`` pela
    classe (idioma comum do Qt) — então o substituto usado no monkeypatch
    também precisa expor ``DialogCode``, não só se comportar como
    construtor."""

    def factory(*args, **kwargs):
        return _FakeWelcomeDialog(result, music, sfx, downloads)

    factory.DialogCode = _FakeWelcomeDialog.DialogCode
    return factory


def test_does_not_show_again_once_completed(qt_core_app, tmp_path: Path, monkeypatch):
    window = _build_window(tmp_path)
    window.studio_settings_repo.set(KEY_FIRST_RUN_COMPLETED, True)

    calls = []
    monkeypatch.setattr(
        "app.shell.welcome_dialog.WelcomeDialog",
        lambda *a, **k: calls.append(True) or _FakeWelcomeDialog(1),
    )
    studio_main.maybe_show_welcome_dialog(window, window.studio_settings_repo)
    assert calls == []


def test_skip_marks_completed_without_touching_any_folder(qt_core_app, tmp_path: Path, monkeypatch):
    window = _build_window(tmp_path)
    monkeypatch.setattr(
        "app.shell.welcome_dialog.WelcomeDialog",
        _fake_dialog_factory(0),  # Pular por enquanto (Rejected)
    )

    studio_main.maybe_show_welcome_dialog(window, window.studio_settings_repo)

    assert window.studio_settings_repo.get(KEY_FIRST_RUN_COMPLETED) is True
    assert not window.is_page_created("music")
    assert not window.is_page_created("sfx")
    assert window.studio_settings_repo.get(KEY_DEFAULT_DOWNLOADS_FOLDER) is None


def test_accept_with_folders_applies_them(qt_core_app, tmp_path: Path, monkeypatch):
    window = _build_window(tmp_path)
    music_folder = tmp_path / "Musicas"
    music_folder.mkdir()
    sfx_folder = tmp_path / "SFX"
    sfx_folder.mkdir()
    downloads_folder = tmp_path / "Downloads"

    monkeypatch.setattr(
        "app.shell.welcome_dialog.WelcomeDialog",
        _fake_dialog_factory(1, music=str(music_folder), sfx=str(sfx_folder), downloads=str(downloads_folder)),
    )

    studio_main.maybe_show_welcome_dialog(window, window.studio_settings_repo)

    assert window.studio_settings_repo.get(KEY_FIRST_RUN_COMPLETED) is True
    music = window.get_page("music")
    sfx = window.get_page("sfx")
    assert music is not None and music.current_library_folder() == str(music_folder)
    assert sfx is not None and sfx.current_library_folder() == str(sfx_folder)
    assert window.studio_settings_repo.get(KEY_DEFAULT_DOWNLOADS_FOLDER) == str(downloads_folder)


def test_accept_with_no_folders_filled_touches_nothing(qt_core_app, tmp_path: Path, monkeypatch):
    window = _build_window(tmp_path)
    monkeypatch.setattr("app.shell.welcome_dialog.WelcomeDialog", _fake_dialog_factory(1))

    studio_main.maybe_show_welcome_dialog(window, window.studio_settings_repo)

    assert window.studio_settings_repo.get(KEY_FIRST_RUN_COMPLETED) is True
    assert not window.is_page_created("music")
    assert not window.is_page_created("sfx")
