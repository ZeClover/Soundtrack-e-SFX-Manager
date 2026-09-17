"""Ponto de entrada do RPG SFX Manager.

Uso em desenvolvimento:
    python main.py
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication
from rpg_audio_shared.logging_setup import configure_logging
from rpg_audio_shared.theme import apply_dark_theme

from app.config import ACCENT_COLOR, APP_NAME, APP_SLUG
from app.ui.main_window import MainWindow


def main() -> int:
    configure_logging(APP_SLUG)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    apply_dark_theme(app, ACCENT_COLOR)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
