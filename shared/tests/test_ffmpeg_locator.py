from __future__ import annotations

import sys
from pathlib import Path

from rpg_audio_shared.ffmpeg_locator import ffmpeg_available, find_ffmpeg_binary


def _make_fake_exe(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("fake binary")


def test_finds_bundled_binary_before_checking_path(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    bundled_dir = tmp_path / "ffmpeg"
    _make_fake_exe(bundled_dir / "ffmpeg.exe")

    # mesmo que o PATH tenha um ffmpeg, o empacotado deve ganhar
    monkeypatch.setattr("rpg_audio_shared.ffmpeg_locator.shutil.which", lambda name: "/usr/bin/ffmpeg")

    found = find_ffmpeg_binary("ffmpeg", bundled_dir=bundled_dir)
    assert found == bundled_dir / "ffmpeg.exe"


def test_falls_back_to_path_when_no_bundled_copy(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    empty_dir = tmp_path / "no-ffmpeg-here"
    empty_dir.mkdir()
    monkeypatch.setattr("rpg_audio_shared.ffmpeg_locator.shutil.which", lambda name: "/usr/bin/ffmpeg")

    found = find_ffmpeg_binary("ffmpeg", bundled_dir=empty_dir)
    assert found == Path("/usr/bin/ffmpeg")


def test_returns_none_when_neither_bundled_nor_path_available(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("rpg_audio_shared.ffmpeg_locator.shutil.which", lambda name: None)
    found = find_ffmpeg_binary("ffmpeg", bundled_dir=tmp_path / "does-not-exist")
    assert found is None


def test_ffmpeg_available_reflects_bundled_binary(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    bundled_dir = tmp_path / "ffmpeg"
    _make_fake_exe(bundled_dir / "ffmpeg.exe")
    monkeypatch.setattr("rpg_audio_shared.ffmpeg_locator.shutil.which", lambda name: None)

    assert ffmpeg_available(bundled_dir=bundled_dir) is True


def test_ffmpeg_available_false_when_nothing_found(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("rpg_audio_shared.ffmpeg_locator.shutil.which", lambda name: None)
    assert ffmpeg_available(bundled_dir=tmp_path / "empty") is False


def test_bundled_lookup_uses_plain_name_on_non_windows(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    bundled_dir = tmp_path / "ffmpeg"
    _make_fake_exe(bundled_dir / "ffmpeg")

    found = find_ffmpeg_binary("ffmpeg", bundled_dir=bundled_dir)
    assert found == bundled_dir / "ffmpeg"
