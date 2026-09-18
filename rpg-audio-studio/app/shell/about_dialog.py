"""Diálogo "Sobre" (item 13 da Etapa 6) — simples, sem sofisticação."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from app.version import APP_DESCRIPTION, APP_DISPLAY_NAME, APP_MODULES, APP_VERSION


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Sobre o {APP_DISPLAY_NAME}")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)

        title = QLabel(APP_DISPLAY_NAME)
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        version = QLabel(f"v{APP_VERSION}")
        version.setStyleSheet("color: #9aa0ad;")
        layout.addWidget(version)

        description = QLabel(APP_DESCRIPTION)
        description.setWordWrap(True)
        layout.addWidget(description)

        modules_title = QLabel("Módulos:")
        modules_title.setStyleSheet("font-weight: 600; margin-top: 8px;")
        layout.addWidget(modules_title)

        for module_name in APP_MODULES:
            layout.addWidget(QLabel(f"• {module_name}"))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
