"""Diálogo de exportação de soundtrack (itens 30-35)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from soundtrack_app.services.export_service import ExportOptions


class ExportDialog(QDialog):
    def __init__(
        self,
        soundtrack_name: str,
        track_count: int,
        default_folder: str = "",
        has_sections: bool = False,
        initial_conflict_policy: str | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Exportar — {soundtrack_name}")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        info = QLabel(f"{track_count} música(s) serão copiadas (os arquivos originais não são alterados).")
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

        self.numbering_checkbox = QCheckBox("Numerar músicas (01 - Nome.mp3)")
        self.numbering_checkbox.setChecked(True)
        form.addRow("", self.numbering_checkbox)

        self.keep_format_radio = QRadioButton("Manter formato original")
        self.keep_format_radio.setChecked(True)
        self.convert_mp3_radio = QRadioButton("Converter tudo para MP3")
        form.addRow("Formato:", self.keep_format_radio)
        form.addRow("", self.convert_mp3_radio)

        self.quality_combo = QComboBox()
        self.quality_combo.addItem("Alta (320 kbps)", "alta")
        self.quality_combo.addItem("Média (192 kbps)", "media")
        self.quality_combo.addItem("Econômica (128 kbps)", "economica")
        self.quality_combo.setCurrentIndex(1)
        self.quality_combo.setEnabled(False)
        self.convert_mp3_radio.toggled.connect(self.quality_combo.setEnabled)
        form.addRow("Qualidade MP3:", self.quality_combo)

        self.conflict_combo = QComboBox()
        self.conflict_combo.addItem("Criar nome alternativo", "rename")
        self.conflict_combo.addItem("Sobrescrever", "overwrite")
        self.conflict_combo.addItem("Ignorar", "skip")
        if initial_conflict_policy is not None:
            # Pré-seleciona com a preferência salva em Configurações (item
            # 14 da Etapa 6) — em vez de sempre reabrir em "rename".
            index = self.conflict_combo.findData(initial_conflict_policy)
            if index >= 0:
                self.conflict_combo.setCurrentIndex(index)
        form.addRow("Se o arquivo já existir:", self.conflict_combo)

        self.section_flat_radio = QRadioButton("Tudo na mesma pasta")
        self.section_flat_radio.setChecked(True)
        self.section_subfolders_radio = QRadioButton("Uma subpasta por seção")
        if has_sections:
            form.addRow("Seções:", self.section_flat_radio)
            form.addRow("", self.section_subfolders_radio)

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
            numbering=self.numbering_checkbox.isChecked(),
            convert_to_mp3=self.convert_mp3_radio.isChecked(),
            mp3_quality=self.quality_combo.currentData() or "media",
            conflict_policy=self.conflict_combo.currentData() or "rename",
            section_mode="subfolders" if self.section_subfolders_radio.isChecked() else "flat",
        )
