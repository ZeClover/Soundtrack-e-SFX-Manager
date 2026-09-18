from __future__ import annotations

from pathlib import Path

from modules.downloader.services.recent_downloads import list_recent_titles, record_downloads


def test_record_and_list_recent_titles(tmp_path: Path):
    path = tmp_path / "recent.json"
    record_downloads(["Track A", "Track B"], path=path)
    assert list_recent_titles(path=path) == ["Track A", "Track B"]


def test_newer_downloads_appear_first(tmp_path: Path):
    path = tmp_path / "recent.json"
    record_downloads(["Old"], path=path)
    record_downloads(["New"], path=path)
    assert list_recent_titles(path=path) == ["New", "Old"]


def test_list_respects_limit(tmp_path: Path):
    path = tmp_path / "recent.json"
    record_downloads([f"Track {i}" for i in range(10)], path=path)
    assert len(list_recent_titles(path=path, limit=3)) == 3


def test_record_empty_list_is_noop(tmp_path: Path):
    path = tmp_path / "recent.json"
    record_downloads([], path=path)
    assert not path.exists()


def test_list_recent_titles_with_missing_file_returns_empty(tmp_path: Path):
    assert list_recent_titles(path=tmp_path / "does-not-exist.json") == []


def test_list_recent_titles_survives_corrupted_file(tmp_path: Path):
    path = tmp_path / "recent.json"
    path.write_text("{not valid json", encoding="utf-8")
    assert list_recent_titles(path=path) == []
