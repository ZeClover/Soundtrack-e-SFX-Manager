"""Diálogo de exportação de pack de SFX (item 46)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
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

from app.services.export_service import ExportOptions


class ExportDialog(QDialog):
    def __init__(self, pack_name: str, track_count: int, default_folder: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Exportar — {pack_name}")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        info = QLabel(f"{track_count} efeito(s) serão copiados (os arquivos originais não são alterados).")
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()

        folder_row = QHBoxLayout()
        self.folder_edit = QLineEdit(default_folder)
        self.folder_edit.setPlaceholderText("Escolha a pasta de destino...")
        folder_row.addWidget(self.folder_edit)
        browse_button = QPushButton("Escolher pasta...")
        browse_button.clicked.connect(self._browse)
        folder_row.addWidget(browse_button)
        form.addRow("Pasta de destino:", folder_row)

        self.format_combo = QComboBox()
        self.format_combo.addItem("Manter formato original", "keep")
        self.format_combo.addItem("Converter tudo para WAV", "wav")
        self.format_combo.addItem("Converter tudo para MP3", "mp3")
        form.addRow("Formato:", self.format_combo)

        self.conflict_combo = QComboBox()
        self.conflict_combo.addItem("Criar nome alternativo", "rename")
        self.conflict_combo.addItem("Sobrescrever", "overwrite")
        self.conflict_combo.addItem("Ignorar", "skip")
        form.addRow("Se o arquivo já existir:", self.conflict_combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("EXPORTAR")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Escolher pasta de destino")
        if folder:
            self.folder_edit.setText(folder)

    def _on_accept(self) -> None:
        if not self.folder_edit.text().strip():
            self.folder_edit.setFocus()
            return
        self.accept()

    def export_options(self) -> ExportOptions:
        return ExportOptions(
            destination_folder=Path(self.folder_edit.text().strip()),
            export_format=self.format_combo.currentData() or "keep",
            conflict_policy=self.conflict_combo.currentData() or "rename",
        )
