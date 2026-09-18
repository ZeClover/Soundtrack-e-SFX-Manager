"""Ponto de entrada do RPG Soundtrack Manager.

Uso em desenvolvimento:
    python main.py

Continua funcionando de forma independente mesmo depois da unificação em
RPG Audio Studio (veja ``rpg-audio-studio/``): este arquivo só embrulha o
widget do módulo (``soundtrack_app.ui.main_window.MainWindow``) numa janela
própria, sem duplicar nenhuma lógica de aplicação.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMainWindow
from rpg_audio_shared.logging_setup import configure_logging
from rpg_audio_shared.theme import apply_dark_theme

from soundtrack_app.config import ACCENT_COLOR, APP_NAME, APP_SLUG
from soundtrack_app.ui.main_window import MainWindow


class StandaloneWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 800)
        self.module = MainWindow()
        self.setCentralWidget(self.module)

    def closeEvent(self, event) -> None:  # noqa: N802
        self.module.shutdown()
        super().closeEvent(event)


def main() -> int:
    configure_logging(APP_SLUG)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    apply_dark_theme(app, ACCENT_COLOR)

    window = StandaloneWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
