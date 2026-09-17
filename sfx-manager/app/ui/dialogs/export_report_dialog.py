"""Relatório final de exportação de pack (item 35, equivalente para SFX)."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QListWidget, QVBoxLayout

from app.services.export_service import ExportReport
from rpg_audio_shared.formatting import format_file_size


class ExportReportDialog(QDialog):
    def __init__(self, report: ExportReport, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pack exportado")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        summary = QLabel(
            f"<b>Pack exportado.</b><br><br>"
            f"{report.exported_count} efeito(s)<br>"
            f"{format_file_size(report.total_bytes)}<br>"
            f"{report.destination}"
        )
        layout.addWidget(summary)

        if report.skipped_count:
            layout.addWidget(QLabel(f"{report.skipped_count} arquivo(s) ignorado(s) (já existiam)."))

        if report.errors:
            layout.addWidget(QLabel(f"⚠ {len(report.errors)} erro(s):"))
            error_list = QListWidget()
            error_list.addItems(report.errors)
            layout.addWidget(error_list)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
