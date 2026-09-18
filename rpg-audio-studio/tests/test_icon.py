"""Regressão da Etapa 6 (item 10): o app precisa de um ícone de verdade —
tanto o arquivo (``.ico``/``.png`` gerados por ``scripts/generate_icon.py``)
quanto a janela principal usando ele."""

from __future__ import annotations

from app.config import icon_path
from app.shell.main_window import StudioWindow


def test_icon_path_resolves_to_an_existing_file():
    assert icon_path().is_file()
    assert icon_path().suffix == ".ico"


def test_studio_window_has_a_non_null_icon(qt_core_app):
    window = StudioWindow()
    assert not window.windowIcon().isNull()
