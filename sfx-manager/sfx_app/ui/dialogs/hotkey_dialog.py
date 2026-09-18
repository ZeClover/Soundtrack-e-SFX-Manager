"""Atribuir uma tecla de atalho simples a um efeito (item 44)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from sfx_app.config import ALLOWED_HOTKEYS


class HotkeyDialog(QDialog):
    def __init__(self, track_title: str, current_key: str | None, taken: dict[str, str], parent=None):
        """``taken`` é {tecla: titulo_do_efeito_que_ja_usa} para mostrar o conflito."""
        super().__init__(parent)
        self.setWindowTitle("Atribuir tecla")
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Efeito: <b>{track_title}</b>"))

        form = QFormLayout()
        self.key_combo = QComboBox()
        self.key_combo.addItem("(nenhuma)", None)
        for key in ALLOWED_HOTKEYS:
            label = key
            if key in taken and taken[key] != track_title:
                label += f"  (em uso: {taken[key]})"
            self.key_combo.addItem(label, key)
        if current_key:
            index = self.key_combo.findData(current_key)
            if index >= 0:
                self.key_combo.setCurrentIndex(index)
        form.addRow("Tecla:", self.key_combo)
        layout.addLayout(form)

        hint = QLabel("Pressionar essa tecla (fora de campos de texto) toca o efeito na hora.")
        hint.setStyleSheet("color: #9aa0ad;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_key(self) -> str | None:
        return self.key_combo.currentData()
