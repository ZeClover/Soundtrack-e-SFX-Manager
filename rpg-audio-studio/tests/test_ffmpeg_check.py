from __future__ import annotations

from modules.downloader.services.ffmpeg_check import ffmpeg_available


def test_ffmpeg_available_reflects_system_path_when_no_bundled_copy(monkeypatch, tmp_path):
    # Sem cópia empacotada neste ambiente de teste (bundled_ffmpeg_dir()
    # aponta pra dentro da árvore de código-fonte, que não tem pasta
    # ffmpeg/) -- cai no PATH do sistema via rpg_audio_shared.ffmpeg_locator.
    monkeypatch.setattr(
        "rpg_audio_shared.ffmpeg_locator.shutil.which", lambda name: "/usr/bin/ffmpeg"
    )
    assert ffmpeg_available() is True

    monkeypatch.setattr("rpg_audio_shared.ffmpeg_locator.shutil.which", lambda name: None)
    assert ffmpeg_available() is False


def test_ffmpeg_available_prefers_bundled_copy_over_path(monkeypatch, tmp_path):
    import sys

    monkeypatch.setattr(sys, "platform", "win32")
    bundled_dir = tmp_path / "ffmpeg"
    bundled_dir.mkdir()
    (bundled_dir / "ffmpeg.exe").write_text("fake")

    monkeypatch.setattr("modules.downloader.services.ffmpeg_check.bundled_ffmpeg_dir", lambda: bundled_dir)
    # mesmo sem nada no PATH, a cópia empacotada já basta
    monkeypatch.setattr("rpg_audio_shared.ffmpeg_locator.shutil.which", lambda name: None)

    assert ffmpeg_available() is True
