"""Diálogo de progresso do escaneamento da biblioteca (item 50 — feedback visual)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QPushButton, QVBoxLayout


class ScanProgressDialog(QDialog):
    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Escaneando biblioteca...")
        self.setMinimumWidth(380)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        layout = QVBoxLayout(self)
        self.status_label = QLabel("Procurando arquivos de áudio...")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        layout.addWidget(self.progress_bar)

        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.cancel_requested)
        layout.addWidget(cancel_button)

    def set_progress(self, current: int, total: int, filename: str) -> None:
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
        self.status_label.setText(f"{current} / {total}\n{filename}")
