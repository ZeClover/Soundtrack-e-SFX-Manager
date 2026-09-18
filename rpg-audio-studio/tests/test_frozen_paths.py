"""Testes de paths em modo frozen (item 27): recursos do app precisam
resolver corretamente tanto em desenvolvimento quanto dentro de um
executável empacotado, e nunca se confundir com dados do usuário."""

from __future__ import annotations

import sys
from pathlib import Path

from app.config import app_base_dir, resource_path


def test_app_base_dir_is_dev_root_when_not_frozen():
    base = app_base_dir()
    assert base.name == "rpg-audio-studio"
    assert (base / "main.py").exists()


def test_resource_path_joins_onto_base_dir():
    path = resource_path("assets", "icon.ico")
    assert path == app_base_dir() / "assets" / "icon.ico"


def test_app_base_dir_uses_frozen_base_when_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert app_base_dir() == tmp_path


def test_resource_path_never_points_inside_user_appdata(monkeypatch, tmp_path):
    """Regressão: recursos do app (ffmpeg, ícone) não podem se confundir
    com o diretório de dados do usuário — são conceitos completamente
    independentes."""
    from app.config import database_path

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "meipass"), raising=False)

    resource = resource_path("ffmpeg", "ffmpeg.exe")
    user_data = database_path()
    assert str(resource) != str(user_data)
    assert "meipass" in str(resource)


def test_ensure_bundled_ffmpeg_on_path_prepends_when_present(monkeypatch, tmp_path):
    import os

    import main as studio_main

    bundled_dir = tmp_path / "ffmpeg"
    bundled_dir.mkdir()
    monkeypatch.setattr(studio_main, "bundled_ffmpeg_dir", lambda: bundled_dir)
    monkeypatch.setenv("PATH", "/usr/bin")

    studio_main.ensure_bundled_ffmpeg_on_path()

    assert os.environ["PATH"].startswith(str(bundled_dir) + os.pathsep)
    assert "/usr/bin" in os.environ["PATH"]


def test_ensure_bundled_ffmpeg_on_path_is_a_noop_when_absent(monkeypatch, tmp_path):
    import os

    import main as studio_main

    monkeypatch.setattr(studio_main, "bundled_ffmpeg_dir", lambda: tmp_path / "does-not-exist")
    monkeypatch.setenv("PATH", "/usr/bin")

    studio_main.ensure_bundled_ffmpeg_on_path()

    assert os.environ["PATH"] == "/usr/bin"
