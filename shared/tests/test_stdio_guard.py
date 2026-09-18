"""Regressão: pythonw.exe deixa sys.stdout/sys.stderr como None, e o
RPG Audio Downloader já quebrou com 'NoneType' object has no attribute
'write' por causa disso (yt-dlp tentando escrever progresso no console)."""

from __future__ import annotations

import sys

from rpg_audio_shared.stdio_guard import ensure_stdio


def test_ensure_stdio_replaces_none_stdout_and_stderr(monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    ensure_stdio()

    assert sys.stdout is not None
    assert sys.stderr is not None
    sys.stdout.write("linha de progresso qualquer\n")
    sys.stderr.write("aviso qualquer\n")
    sys.stdout.flush()
    sys.stderr.flush()
    assert sys.stdout.isatty() is False


def test_ensure_stdio_leaves_real_streams_untouched(monkeypatch, capsys):
    ensure_stdio()
    print("ainda vai para o stdout real")
    captured = capsys.readouterr()
    assert "ainda vai para o stdout real" in captured.out
