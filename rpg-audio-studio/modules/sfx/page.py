"""Página 'SFX e Packs' do RPG Audio Studio.

Só instancia o widget já existente do RPG SFX Manager
(``sfx_app.ui.main_window.MainWindow``) — biblioteca de efeitos e packs já
vêm juntos nessa tela, exatamente como no app standalone.
"""

from __future__ import annotations

from pathlib import Path

from app.bootstrap import ensure_sibling_modules_importable

ensure_sibling_modules_importable()

from sfx_app.ui.main_window import MainWindow  # noqa: E402


def create_sfx_page(db_path: Path | None = None) -> MainWindow:
    return MainWindow(db_path=db_path)
