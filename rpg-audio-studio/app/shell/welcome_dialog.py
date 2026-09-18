"""Primeira execução (item 15 da Etapa 6) — três pastas opcionais, nunca
obrigatórias, com um jeito claro de pular por enquanto."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from app.version import APP_DISPLAY_NAME


class WelcomeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Bem-vindo ao {APP_DISPLAY_NAME}")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)

        title = QLabel(f"Bem-vindo ao {APP_DISPLAY_NAME}")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Se quiser, escolha agora as pastas que você já tem — ou pule e configure "
            "depois em Configurações, a qualquer momento."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #9aa0ad;")
        layout.addWidget(subtitle)

        form = QFormLayout()
        self.music_edit, music_row = self._build_folder_row("Selecionar pasta de músicas")
        self.sfx_edit, sfx_row = self._build_folder_row("Selecionar pasta de SFX")
        self.downloads_edit, downloads_row = self._build_folder_row("Selecionar pasta de downloads")
        form.addRow("Pasta de músicas:", music_row)
        form.addRow("Pasta de SFX:", sfx_row)
        form.addRow("Pasta de downloads:", downloads_row)
        layout.addLayout(form)

        buttons = QDialogButtonBox()
        buttons.addButton("Pular por enquanto", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.addButton("Continuar", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_folder_row(self, dialog_title: str) -> tuple[QLineEdit, QHBoxLayout]:
        edit = QLineEdit()
        edit.setReadOnly(True)
        edit.setPlaceholderText("Nenhuma pasta selecionada (opcional)")
        row = QHBoxLayout()
        row.addWidget(edit, stretch=1)
        button = QPushButton("Escolher...")
        button.clicked.connect(lambda: self._choose_folder(edit, dialog_title))
        row.addWidget(button)
        return edit, row

    def _choose_folder(self, edit: QLineEdit, dialog_title: str) -> None:
        folder = QFileDialog.getExistingDirectory(self, dialog_title)
        if folder:
            edit.setText(folder)

    def music_folder(self) -> str:
        return self.music_edit.text().strip()

    def sfx_folder(self) -> str:
        return self.sfx_edit.text().strip()

    def downloads_folder(self) -> str:
        return self.downloads_edit.text().strip()
