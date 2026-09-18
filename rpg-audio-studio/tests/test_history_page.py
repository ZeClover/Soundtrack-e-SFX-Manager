from __future__ import annotations

from modules.history.data import (
    collect_recent_download_titles,
    collect_recent_music_titles,
    collect_recent_sfx_titles,
)
from modules.history.history_page import HistoryPage


def test_collectors_never_raise_without_any_database(qt_core_app):
    assert collect_recent_music_titles() == []
    assert collect_recent_sfx_titles() == []
    assert collect_recent_download_titles() == []


def test_history_page_refresh_does_not_raise(qt_core_app):
    page = HistoryPage()
    page.refresh()  # sem bancos reais disponíveis (isolados pelo conftest)


def test_collect_recent_downloads_reflects_recorded_titles(qt_core_app, tmp_path, monkeypatch):
    from modules.downloader.services import recent_downloads as recent_downloads_module

    isolated_path = tmp_path / "recent.json"
    monkeypatch.setattr(recent_downloads_module, "recent_downloads_path", lambda: isolated_path)
    recent_downloads_module.record_downloads(["Track X"])

    assert collect_recent_download_titles() == ["Track X"]


def test_collect_recent_music_reflects_real_play_history_in_injected_db(qt_core_app, tmp_path):
    from soundtrack_app.database import Database
    from soundtrack_app.repositories import HistoryRepository, LibraryRootRepository, TrackRepository

    db_path = tmp_path / "soundtrack.db"
    db = Database(db_path)
    root_id = LibraryRootRepository(db).get_or_create("/library")
    track_id = TrackRepository(db).upsert_from_scan(
        library_root_id=root_id, absolute_path="/library/a.mp3", relative_path="a.mp3",
        filename="a.mp3", extension=".mp3", title="Faixa Ouvida", artist="", album="",
        duration_seconds=1.0, file_size=1, partial_hash="h", has_embedded_cover=False,
    )
    TrackRepository(db).register_play(track_id)
    db.close()

    assert collect_recent_music_titles(db_path=db_path) == ["Faixa Ouvida"]


def test_history_page_refresh_shows_real_data_from_injected_db(qt_core_app, tmp_path):
    from soundtrack_app.database import Database
    from soundtrack_app.repositories import LibraryRootRepository, TrackRepository

    db_path = tmp_path / "soundtrack.db"
    db = Database(db_path)
    root_id = LibraryRootRepository(db).get_or_create("/library")
    track_id = TrackRepository(db).upsert_from_scan(
        library_root_id=root_id, absolute_path="/library/a.mp3", relative_path="a.mp3",
        filename="a.mp3", extension=".mp3", title="Faixa da Home", artist="", album="",
        duration_seconds=1.0, file_size=1, partial_hash="h", has_embedded_cover=False,
    )
    TrackRepository(db).register_play(track_id)
    db.close()

    page = HistoryPage(soundtrack_db_path=db_path, sfx_db_path=tmp_path / "sfx-nao-existe.db")
    page.refresh()
    assert "• Faixa da Home" in [
        page._music_group._layout.itemAt(i).widget().text() for i in range(page._music_group._layout.count())
    ]
