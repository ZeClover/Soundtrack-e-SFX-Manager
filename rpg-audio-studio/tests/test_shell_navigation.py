"""Testes do shell (navegação, inicialização preguiçosa dos módulos).

Usa páginas falsas (sem nenhuma dependência dos módulos reais) para
verificar o comportamento genérico do shell isoladamente — o shell não
deveria precisar saber nada sobre Soundtrack/SFX/Downloader para funcionar.
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QWidget

from app.shell.main_window import StudioWindow


class _FakeModulePage(QWidget):
    def __init__(self):
        super().__init__()
        self.active_calls: list[bool] = []
        self.shown_calls = 0
        self.shutdown_calls = 0

    def set_module_active(self, active: bool) -> None:
        self.active_calls.append(active)

    def on_page_shown(self) -> None:
        self.shown_calls += 1

    def shutdown(self) -> None:
        self.shutdown_calls += 1


def test_show_page_lazily_creates_page_only_once(qt_core_app):
    window = StudioWindow()
    creation_count = 0

    def factory():
        nonlocal creation_count
        creation_count += 1
        return _FakeModulePage()

    window.register_page("music", factory)
    assert not window.is_page_created("music")

    window.show_page("music")
    window.show_page("music")
    window.show_page("music")

    assert creation_count == 1
    assert window.is_page_created("music")
    assert window.current_page_key() == "music"


def test_show_page_toggles_module_active_flag(qt_core_app):
    window = StudioWindow()
    window.register_page("music", _FakeModulePage)
    window.register_page("sfx", _FakeModulePage)

    window.show_page("music")
    music = window.get_page("music")
    assert music.active_calls == [True]

    window.show_page("sfx")
    sfx = window.get_page("sfx")
    assert music.active_calls == [True, False]
    assert sfx.active_calls == [True]
    assert music.shown_calls == 1
    assert sfx.shown_calls == 1


def test_get_page_returns_none_before_creation(qt_core_app):
    window = StudioWindow()
    window.register_page("music", _FakeModulePage)
    assert window.get_page("music") is None
    window.show_page("music")
    assert window.get_page("music") is not None


def test_unknown_page_key_is_a_noop(qt_core_app):
    window = StudioWindow()
    window.show_page("does-not-exist")
    assert window.current_page_key() is None


def test_shutdown_only_touches_created_pages(qt_core_app):
    window = StudioWindow()
    window.register_page("music", _FakeModulePage)
    window.register_page("sfx", _FakeModulePage)

    window.show_page("music")  # sfx nunca é visitado
    music = window.get_page("music")

    window.shutdown()

    assert music.shutdown_calls == 1
    assert not window.is_page_created("sfx")


def test_global_player_bar_slot_replaces_previous_widget(qt_core_app):
    window = StudioWindow()
    first = QLabel("primeiro")
    second = QLabel("segundo")

    window.set_global_player_bar(first)
    assert window._global_player_layout.count() == 1

    window.set_global_player_bar(second)
    assert window._global_player_layout.count() == 1
    assert window._global_player_layout.itemAt(0).widget() is second
