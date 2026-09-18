from __future__ import annotations

from PySide6.QtWidgets import QLabel

from app.shell.about_dialog import AboutDialog
from app.version import APP_DISPLAY_NAME, APP_MODULES, APP_VERSION


def test_about_dialog_shows_version_and_modules(qt_core_app):
    dialog = AboutDialog()
    assert APP_DISPLAY_NAME in dialog.windowTitle()

    all_text = " ".join(label.text() for label in dialog.findChildren(QLabel))
    assert APP_VERSION in all_text
    for module_name in APP_MODULES:
        assert module_name in all_text
