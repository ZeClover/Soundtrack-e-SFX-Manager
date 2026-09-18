from __future__ import annotations

from modules.downloader.services.ffmpeg_check import ffmpeg_available


def test_ffmpeg_available_reflects_shutil_which(monkeypatch):
    monkeypatch.setattr("modules.downloader.services.ffmpeg_check.shutil.which", lambda name: "/usr/bin/ffmpeg")
    assert ffmpeg_available() is True

    monkeypatch.setattr("modules.downloader.services.ffmpeg_check.shutil.which", lambda name: None)
    assert ffmpeg_available() is False
