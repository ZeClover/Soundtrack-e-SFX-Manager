"""Relatório final de exportação (item 35)."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QListWidget, QVBoxLayout

from soundtrack_app.services.export_service import ExportReport
from rpg_audio_shared.formatting import format_file_size


class ExportReportDialog(QDialog):
    def __init__(self, report: ExportReport, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Soundtrack exportada")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        summary = QLabel(
            f"<b>Soundtrack exportada.</b><br><br>"
            f"{report.exported_count} música(s)<br>"
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
