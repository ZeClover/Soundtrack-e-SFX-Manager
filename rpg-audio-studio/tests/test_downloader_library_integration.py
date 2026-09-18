"""Testes da integração Downloader → Biblioteca (item 15): depois de um
download bem-sucedido, a pasta baixada deve virar/atualizar a biblioteca
sem nunca copiar arquivos — só aponta o scanner pra lá."""

from __future__ import annotations

from pathlib import Path

import main as studio_main
from modules.downloader.models import DownloadItemResult, DownloadReport, ItemStatus


def _build_window(tmp_path: Path):
    return studio_main.build_studio_window(
        soundtrack_db_path=tmp_path / "soundtrack.db", sfx_db_path=tmp_path / "sfx.db"
    )


def test_download_finished_with_no_successes_does_not_touch_library(qt_core_app, tmp_path: Path):
    window = _build_window(tmp_path)
    window.show_page("downloader")
    downloader = window.get_page("downloader")

    report = DownloadReport(total_items=1, completed=[
        DownloadItemResult(1, "Falhou", ItemStatus.ERROR, error_message="erro")
    ])
    downloader.download_finished.emit(report, tmp_path / "downloads")

    # Música nunca precisou ser criada — nada bem-sucedido pra adicionar.
    assert not window.is_page_created("music")


def test_download_into_configured_library_folder_just_rescans(qt_core_app, tmp_path: Path, monkeypatch):
    window = _build_window(tmp_path)
    library_folder = tmp_path / "MinhaBiblioteca"
    library_folder.mkdir()

    music = window.ensure_page_created("music")
    music.settings_repo.set("library_root_path", str(library_folder))

    rescan_calls = []
    monkeypatch.setattr(music, "rescan_library", lambda: rescan_calls.append(True))
    scan_calls = []
    monkeypatch.setattr(music, "scan_folder", lambda folder: scan_calls.append(folder))

    downloader = window.ensure_page_created("downloader")
    report = DownloadReport(total_items=1, completed=[
        DownloadItemResult(1, "Nova Música", ItemStatus.DONE, file_path=library_folder / "nova.mp3")
    ])
    downloader.download_finished.emit(report, library_folder)

    assert rescan_calls == [True]
    assert scan_calls == []  # não tentou trocar a biblioteca — já era ela


def test_download_outside_library_asks_before_changing_it(qt_core_app, tmp_path: Path, monkeypatch):
    window = _build_window(tmp_path)
    library_folder = tmp_path / "Biblioteca"
    library_folder.mkdir()
    downloads_folder = tmp_path / "OutraPasta"
    downloads_folder.mkdir()

    music = window.ensure_page_created("music")
    music.settings_repo.set("library_root_path", str(library_folder))

    scan_calls = []
    monkeypatch.setattr(music, "scan_folder", lambda folder: scan_calls.append(folder))
    monkeypatch.setattr(
        "main.QMessageBox.question",
        lambda *a, **k: studio_main.QMessageBox.StandardButton.Yes,
    )

    downloader = window.ensure_page_created("downloader")
    report = DownloadReport(total_items=1, completed=[
        DownloadItemResult(1, "Nova Música", ItemStatus.DONE, file_path=downloads_folder / "nova.mp3")
    ])
    downloader.download_finished.emit(report, downloads_folder)

    assert scan_calls == [downloads_folder]


def test_declining_the_prompt_does_not_change_the_library(qt_core_app, tmp_path: Path, monkeypatch):
    window = _build_window(tmp_path)
    library_folder = tmp_path / "Biblioteca"
    library_folder.mkdir()
    downloads_folder = tmp_path / "OutraPasta"
    downloads_folder.mkdir()

    music = window.ensure_page_created("music")
    music.settings_repo.set("library_root_path", str(library_folder))

    scan_calls = []
    monkeypatch.setattr(music, "scan_folder", lambda folder: scan_calls.append(folder))
    monkeypatch.setattr(
        "main.QMessageBox.question",
        lambda *a, **k: studio_main.QMessageBox.StandardButton.No,
    )

    downloader = window.ensure_page_created("downloader")
    report = DownloadReport(total_items=1, completed=[
        DownloadItemResult(1, "Nova Música", ItemStatus.DONE, file_path=downloads_folder / "nova.mp3")
    ])
    downloader.download_finished.emit(report, downloads_folder)

    assert scan_calls == []


def test_downloaded_subfolder_of_library_counts_as_already_in_library(qt_core_app, tmp_path: Path, monkeypatch):
    window = _build_window(tmp_path)
    library_folder = tmp_path / "Biblioteca"
    (library_folder / "Playlist X").mkdir(parents=True)

    music = window.ensure_page_created("music")
    music.settings_repo.set("library_root_path", str(library_folder))

    rescan_calls = []
    monkeypatch.setattr(music, "rescan_library", lambda: rescan_calls.append(True))

    downloader = window.ensure_page_created("downloader")
    report = DownloadReport(total_items=1, completed=[
        DownloadItemResult(1, "Faixa", ItemStatus.DONE, file_path=library_folder / "Playlist X" / "faixa.mp3")
    ])
    downloader.download_finished.emit(report, library_folder / "Playlist X")

    assert rescan_calls == [True]


def test_successful_downloads_are_recorded_for_home_recent_list(qt_core_app, tmp_path: Path, monkeypatch):
    from modules.downloader.services import recent_downloads as recent_downloads_module

    isolated_path = tmp_path / "recent.json"
    monkeypatch.setattr(recent_downloads_module, "recent_downloads_path", lambda: isolated_path)

    window = _build_window(tmp_path)
    downloader = window.ensure_page_created("downloader")
    report = DownloadReport(total_items=2, completed=[
        DownloadItemResult(1, "Track A", ItemStatus.DONE),
        DownloadItemResult(2, "Track B", ItemStatus.ERROR, error_message="x"),
    ])
    downloader.download_finished.emit(report, None)

    assert recent_downloads_module.list_recent_titles(path=isolated_path) == ["Track A"]
