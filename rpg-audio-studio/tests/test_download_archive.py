from __future__ import annotations

from pathlib import Path

from modules.downloader.services.download_archive import DownloadArchive


def test_archive_contains_is_false_for_missing_file(tmp_path: Path):
    archive = DownloadArchive(tmp_path / "does_not_exist.txt")
    assert archive.contains("abc123") is False


def test_archive_add_then_contains(tmp_path: Path):
    path = tmp_path / "archive.txt"
    archive = DownloadArchive(path)

    assert archive.contains("abc123") is False
    archive.add("abc123")
    assert archive.contains("abc123") is True
    assert archive.contains("other") is False


def test_archive_add_creates_parent_directories(tmp_path: Path):
    path = tmp_path / "nested" / "dir" / "archive.txt"
    archive = DownloadArchive(path)
    archive.add("xyz")
    assert path.exists()
    assert archive.contains("xyz") is True


def test_archive_add_empty_id_is_a_noop(tmp_path: Path):
    path = tmp_path / "archive.txt"
    archive = DownloadArchive(path)
    archive.add("")
    assert not path.exists()
