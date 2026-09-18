"""Página 'Música e Soundtracks' do RPG Audio Studio.

Não recria nada: só instancia o widget já existente do RPG Soundtrack
Manager (``soundtrack_app.ui.main_window.MainWindow``), pedindo pra ele
não montar sua própria barra de player — o Studio usa uma barra global
compartilhada (item 17), construída a partir do mesmo ``player_service``.
"""

from __future__ import annotations

from pathlib import Path

from app.bootstrap import ensure_sibling_modules_importable

ensure_sibling_modules_importable()

from soundtrack_app.ui.main_window import MainWindow  # noqa: E402


def create_soundtrack_page(db_path: Path | None = None) -> MainWindow:
    return MainWindow(db_path=db_path, embed_player_bar=False)
