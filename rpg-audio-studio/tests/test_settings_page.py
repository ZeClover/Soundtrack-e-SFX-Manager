from __future__ import annotations

from pathlib import Path

from app.settings.database import Database
from app.settings.settings_page import SettingsPage
from app.settings.settings_repository import (
    KEY_CREATE_PLAYLIST_SUBFOLDER,
    KEY_DEFAULT_DOWNLOADS_FOLDER,
    KEY_DOWNLOADS_FOLDER_IS_LIBRARY,
    KEY_EXPORT_CONFLICT_POLICY,
    KEY_MP3_QUALITY,
    KEY_NUMBER_TRACKS,
    KEY_PREFERRED_FORMAT,
    StudioSettingsRepository,
)


def _make_page(tmp_path: Path) -> tuple[SettingsPage, StudioSettingsRepository, Database]:
    db = Database(tmp_path / "settings.db")
    repo = StudioSettingsRepository(db)
    page = SettingsPage(repo)
    return page, repo, db


def test_choosing_default_downloads_folder_persists_it(qt_core_app, tmp_path: Path, monkeypatch):
    page, repo, db = _make_page(tmp_path)
    try:
        folder = tmp_path / "Downloads"
        monkeypatch.setattr(
            "app.settings.settings_page.QFileDialog.getExistingDirectory", lambda *a, **k: str(folder)
        )
        page._on_choose_default_downloads_folder()
        assert repo.get(KEY_DEFAULT_DOWNLOADS_FOLDER) == str(folder)
        assert page.default_downloads_edit.text() == str(folder)
    finally:
        db.close()


def test_format_and_quality_changes_persist(qt_core_app, tmp_path: Path):
    page, repo, db = _make_page(tmp_path)
    try:
        index = page.format_combo.findData("best")
        page.format_combo.setCurrentIndex(index)
        assert repo.get(KEY_PREFERRED_FORMAT) == "best"

        index = page.quality_combo.findData("economic")
        page.quality_combo.setCurrentIndex(index)
        assert repo.get(KEY_MP3_QUALITY) == "economic"
    finally:
        db.close()


def test_checkboxes_persist_state(qt_core_app, tmp_path: Path):
    page, repo, db = _make_page(tmp_path)
    try:
        page.number_tracks_checkbox.setChecked(False)
        assert repo.get(KEY_NUMBER_TRACKS) is False

        page.create_subfolder_checkbox.setChecked(False)
        assert repo.get(KEY_CREATE_PLAYLIST_SUBFOLDER) is False
    finally:
        db.close()


def test_conflict_policy_persists(qt_core_app, tmp_path: Path):
    page, repo, db = _make_page(tmp_path)
    try:
        index = page.conflict_policy_combo.findData("overwrite")
        page.conflict_policy_combo.setCurrentIndex(index)
        assert repo.get(KEY_EXPORT_CONFLICT_POLICY) == "overwrite"
    finally:
        db.close()


def test_settings_reloaded_on_construction(qt_core_app, tmp_path: Path):
    db = Database(tmp_path / "settings.db")
    try:
        repo = StudioSettingsRepository(db)
        repo.set(KEY_PREFERRED_FORMAT, "best")
        repo.set(KEY_NUMBER_TRACKS, False)

        page = SettingsPage(repo)
        assert page.format_combo.currentData() == "best"
        assert page.number_tracks_checkbox.isChecked() is False
    finally:
        db.close()


def test_use_library_as_downloads_checkbox_fills_folder_from_hook(qt_core_app, tmp_path: Path):
    page, repo, db = _make_page(tmp_path)
    try:
        page.set_music_folder_hooks(lambda: str(tmp_path / "MinhaBiblioteca"), lambda: None)
        page.use_library_as_downloads_checkbox.setChecked(True)

        assert repo.get(KEY_DOWNLOADS_FOLDER_IS_LIBRARY) is True
        assert page.default_downloads_edit.text() == str(tmp_path / "MinhaBiblioteca")
        assert page.effective_downloads_folder() == str(tmp_path / "MinhaBiblioteca")
    finally:
        db.close()


def test_change_music_folder_button_calls_hook(qt_core_app, tmp_path: Path):
    page, repo, db = _make_page(tmp_path)
    try:
        calls = []
        page.set_music_folder_hooks(lambda: "/some/folder", lambda: calls.append(True))
        page._on_change_music_folder_clicked()
        assert calls == [True]
        assert page.music_folder_label.text() == "/some/folder"
    finally:
        db.close()


def test_refresh_shows_placeholder_when_no_folder_configured(qt_core_app, tmp_path: Path):
    page, repo, db = _make_page(tmp_path)
    try:
        page.set_sfx_folder_hooks(lambda: None, lambda: None)
        page.refresh()
        assert page.sfx_folder_label.text() == "Nenhuma pasta selecionada"
    finally:
        db.close()


def test_backup_button_creates_zip_at_chosen_path(qt_core_app, tmp_path: Path, monkeypatch):
    import sqlite3

    from app.backup.backup_service import BackupSource

    source_db = tmp_path / "source.db"
    conn = sqlite3.connect(str(source_db))
    conn.execute("CREATE TABLE t (x INTEGER)")
    conn.commit()
    conn.close()

    monkeypatch.setattr(
        "app.backup.backup_service.default_sources",
        lambda: [BackupSource("Teste", source_db, "source.db")],
    )

    page, repo, db = _make_page(tmp_path)
    try:
        zip_path = tmp_path / "out.zip"
        monkeypatch.setattr(
            "app.settings.settings_page.QFileDialog.getSaveFileName", lambda *a, **k: (str(zip_path), "")
        )
        infos = []
        monkeypatch.setattr(
            "app.settings.settings_page.QMessageBox.information", lambda *a, **k: infos.append(a)
        )
        page._on_backup_clicked()
        assert zip_path.exists()
        assert infos  # mostrou confirmação
    finally:
        db.close()


def test_restore_button_asks_confirmation_and_calls_before_restore_hook(qt_core_app, tmp_path: Path, monkeypatch):
    import sqlite3

    from PySide6.QtWidgets import QMessageBox as RealQMessageBox

    from app.backup.backup_service import BackupSource, create_backup

    restored_db = tmp_path / "restored.db"
    zip_path = tmp_path / "backup.zip"

    source_db = tmp_path / "source.db"
    conn = sqlite3.connect(str(source_db))
    conn.execute("CREATE TABLE t (x INTEGER)")
    conn.commit()
    conn.close()

    create_backup(zip_path, sources=[BackupSource("Teste", source_db, "restored.db")])

    monkeypatch.setattr(
        "app.backup.backup_service.default_sources", lambda: [BackupSource("Teste", restored_db, "restored.db")]
    )

    page, repo, db = _make_page(tmp_path)
    try:
        monkeypatch.setattr(
            "app.settings.settings_page.QFileDialog.getOpenFileName", lambda *a, **k: (str(zip_path), "")
        )
        monkeypatch.setattr(
            "app.settings.settings_page.QMessageBox.question",
            lambda *a, **k: RealQMessageBox.StandardButton.Yes,
        )
        monkeypatch.setattr("app.settings.settings_page.QMessageBox.information", lambda *a, **k: None)

        before_restore_calls = []
        page.set_before_restore_hook(lambda: before_restore_calls.append(True))

        # Evita fechar a QApplication de verdade (afetaria os outros testes).
        monkeypatch.setattr("app.settings.settings_page.QApplication.instance", lambda: None)

        page._on_restore_clicked()

        assert before_restore_calls == [True]
        assert restored_db.exists()
    finally:
        db.close()


def test_declining_restore_confirmation_does_not_touch_files(qt_core_app, tmp_path: Path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox as RealQMessageBox

    zip_path = tmp_path / "backup.zip"
    zip_path.write_bytes(b"not a real zip, should never be opened")

    page, repo, db = _make_page(tmp_path)
    try:
        monkeypatch.setattr(
            "app.settings.settings_page.QFileDialog.getOpenFileName", lambda *a, **k: (str(zip_path), "")
        )
        monkeypatch.setattr(
            "app.settings.settings_page.QMessageBox.question",
            lambda *a, **k: RealQMessageBox.StandardButton.No,
        )
        calls = []
        page.set_before_restore_hook(lambda: calls.append(True))

        page._on_restore_clicked()

        assert calls == []  # nunca chegou a tentar restaurar
    finally:
        db.close()
