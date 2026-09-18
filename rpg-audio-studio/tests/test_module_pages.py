"""Testes de integração dos módulos reais (Soundtrack Manager e SFX
Manager) dentro do shell do Studio — cada um com banco isolado em
tmp_path, nunca tocando no %APPDATA% real."""

from __future__ import annotations

from pathlib import Path

from app.shell.main_window import StudioWindow
from modules.sfx.page import create_sfx_page
from modules.soundtrack.page import create_soundtrack_page


def test_soundtrack_page_embeds_without_its_own_player_bar(qt_core_app, tmp_path: Path):
    module = create_soundtrack_page(db_path=tmp_path / "soundtrack.db")
    try:
        # embed_player_bar=False: o Studio usa uma barra global própria.
        assert module.player_bar is None
        assert hasattr(module, "player_service")
    finally:
        module.shutdown()


def test_sfx_page_creates_normally(qt_core_app, tmp_path: Path):
    module = create_sfx_page(db_path=tmp_path / "sfx.db")
    try:
        assert hasattr(module, "player_service")
        assert hasattr(module, "pack_panel")
    finally:
        module.shutdown()


def test_soundtrack_shortcuts_disabled_when_module_not_active(qt_core_app, tmp_path: Path):
    module = create_soundtrack_page(db_path=tmp_path / "soundtrack.db")
    try:
        assert module._shortcuts_enabled() is True
        module.set_module_active(False)
        assert module._shortcuts_enabled() is False
        module.set_module_active(True)
        assert module._shortcuts_enabled() is True
    finally:
        module.shutdown()


def test_sfx_hotkey_ignored_when_module_not_active(qt_core_app, tmp_path: Path):
    module = create_sfx_page(db_path=tmp_path / "sfx.db")
    try:
        # Sem efeito cadastrado ainda, mas o flag de ativo já deve bloquear
        # a checagem de "digitando em campo de texto" independentemente.
        module.set_module_active(False)
        calls = []
        original = module.track_repo.get_by_id
        module.track_repo.get_by_id = lambda *a, **k: calls.append(a) or original(*a, **k)
        module._on_hotkey_triggered("A")
        assert calls == []  # nunca chegou a consultar o banco: saiu cedo
    finally:
        module.shutdown()


def test_music_and_sfx_pages_coexist_in_shell(qt_core_app, tmp_path: Path):
    window = StudioWindow()
    window.register_page("music", lambda: create_soundtrack_page(db_path=tmp_path / "soundtrack.db"))
    window.register_page("sfx", lambda: create_sfx_page(db_path=tmp_path / "sfx.db"))

    window.show_page("music")
    window.show_page("sfx")
    window.show_page("music")
    window.show_page("sfx")

    # Cada módulo foi instanciado exatamente uma vez (sem duplicar workers
    # de scanner, player, etc. — item 32 do pedido).
    assert len(window._page_instances) == 2

    window.shutdown()
