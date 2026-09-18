"""Janela principal (shell) do RPG Audio Studio.

O shell não conhece os módulos concretos (Soundtrack, SFX, Downloader...) —
eles se registram de fora via :meth:`StudioWindow.register_page`, cada um
com uma fábrica (``Callable[[], QWidget]``) chamada só na primeira vez que
a página é aberta (item 38: lazy initialization). Isso mantém o shell
testável isoladamente (dá pra registrar páginas falsas em teste) e evita
qualquer acoplamento do shell com regras de negócio de um módulo específico.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QStatusBar, QVBoxLayout, QWidget

from app.config import APP_NAME, icon_path
from app.shell.sidebar import Sidebar

PageFactory = Callable[[], QWidget]


class StudioWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(APP_NAME)
        self.resize(1400, 860)

        # Ícone da janela (item 10 da Etapa 6) — usado mesmo fora do fluxo
        # normal de main() (ex.: testes que criam StudioWindow diretamente),
        # então fica aqui e não só em QApplication.setWindowIcon.
        icon_file = icon_path()
        if icon_file.is_file():
            self.setWindowIcon(QIcon(str(icon_file)))

        self._page_factories: dict[str, PageFactory] = {}
        self._page_instances: dict[str, QWidget] = {}
        self._active_key: str | None = None

        central = QWidget()
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.navigate_requested.connect(self.show_page)
        root_layout.addWidget(self.sidebar)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.stack = QStackedWidget()
        right_layout.addWidget(self.stack, stretch=1)

        # Slot para a barra de player global (item 17) — preenchido de fora
        # (main.py) assim que o módulo de música existir, sem o shell
        # precisar conhecer PlayerBar/PlayerService diretamente.
        self._global_player_container = QWidget()
        self._global_player_layout = QVBoxLayout(self._global_player_container)
        self._global_player_layout.setContentsMargins(0, 0, 0, 0)
        self._global_player_layout.setSpacing(0)
        right_layout.addWidget(self._global_player_container)

        root_layout.addWidget(right, stretch=1)
        self.setCentralWidget(central)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    # ------------------------------------------------------------------
    # Registro/navegação de páginas
    # ------------------------------------------------------------------

    def register_page(self, key: str, factory: PageFactory) -> None:
        self._page_factories[key] = factory

    def is_page_created(self, key: str) -> bool:
        return key in self._page_instances

    def get_page(self, key: str) -> QWidget | None:
        return self._page_instances.get(key)

    def ensure_page_created(self, key: str) -> QWidget | None:
        """Cria a página (se ainda não existir) sem navegar até ela — útil
        para uma integração entre módulos que precisa falar com um módulo
        que o usuário talvez nunca tenha aberto ainda (ex.: Downloader
        perguntando à Música qual é a pasta da biblioteca configurada)."""
        if key not in self._page_instances:
            if key not in self._page_factories:
                return None
            widget = self._page_factories[key]()
            self._page_instances[key] = widget
            self.stack.addWidget(widget)
        return self._page_instances[key]

    def show_page(self, key: str) -> None:
        if self.ensure_page_created(key) is None:
            return

        if self._active_key is not None and self._active_key != key:
            previous = self._page_instances.get(self._active_key)
            if previous is not None and hasattr(previous, "set_module_active"):
                previous.set_module_active(False)

        widget = self._page_instances[key]
        if hasattr(widget, "set_module_active"):
            widget.set_module_active(True)
        if hasattr(widget, "on_page_shown"):
            widget.on_page_shown()

        self.stack.setCurrentWidget(widget)
        self._active_key = key
        self.sidebar.set_current(key)

    def current_page_key(self) -> str | None:
        return self._active_key

    # ------------------------------------------------------------------
    # Barra de player global
    # ------------------------------------------------------------------

    def set_global_player_bar(self, widget: QWidget) -> None:
        while self._global_player_layout.count():
            item = self._global_player_layout.takeAt(0)
            taken = item.widget()
            if taken is not None:
                taken.setParent(None)
        self._global_player_layout.addWidget(widget)

    # ------------------------------------------------------------------
    # Encerramento
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Propaga o encerramento para todo módulo já instanciado (item 32:
        fechar o app com música/SFX tocando ou scan/download em andamento
        precisa ser seguro)."""
        for widget in self._page_instances.values():
            if hasattr(widget, "shutdown"):
                widget.shutdown()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.shutdown()
        super().closeEvent(event)
