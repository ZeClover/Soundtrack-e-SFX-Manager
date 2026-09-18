"""Página do Downloader (yt-dlp + FFmpeg) do RPG Audio Studio."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from modules.downloader.config import download_archive_path
from modules.downloader.models import (
    MP3_QUALITY_LABELS,
    AudioFormat,
    DownloadOptions,
    DownloadReport,
    Mp3Quality,
)
from modules.downloader.services.download_worker import DownloadWorker
from modules.downloader.services.ffmpeg_check import ffmpeg_available

logger = logging.getLogger(__name__)

_STATUS_ICON = {"waiting": "○", "downloading": "↓", "done": "✓", "error": "!", "skipped": "⏭"}


class DownloaderPage(QWidget):
    # Emitido depois de terminar (ou cancelar) um download, com a pasta de
    # destino usada — a integração com a Biblioteca (item 15) ouve este
    # sinal de fora (main.py), sem o Downloader precisar conhecer o módulo
    # Música diretamente.
    download_finished = Signal(object, object)  # DownloadReport, Path | None

    def __init__(self, parent=None, ydl_class=None, ffmpeg_checker=None, archive_path: Path | None = None):
        super().__init__(parent)
        # Injetáveis para teste (mock do yt-dlp, disponibilidade do FFmpeg,
        # e um archive_path isolado em vez do real — mesmo padrão de
        # ``db_path: Path | None = None`` usado nos outros módulos para
        # nunca deixar os testes tocarem em dados reais do usuário), sem
        # afetar o comportamento padrão em produção.
        self._ydl_class = ydl_class
        self._ffmpeg_checker = ffmpeg_checker or ffmpeg_available
        self._archive_path = archive_path
        self._worker: DownloadWorker | None = None
        self._item_widgets: dict[int, QListWidgetItem] = {}
        self._current_item_title = ""
        self._is_active = True
        self._build_ui()

    def set_module_active(self, active: bool) -> None:
        self._is_active = active

    # ------------------------------------------------------------------
    # Construção da UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel("Downloader")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        url_row = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("URL do vídeo ou playlist do YouTube")
        url_row.addWidget(self.url_edit, stretch=1)
        paste_button = QPushButton("COLAR")
        paste_button.clicked.connect(self._on_paste)
        url_row.addWidget(paste_button)
        layout.addLayout(url_row)

        form = QFormLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItem("MP3", AudioFormat.MP3)
        self.format_combo.addItem("Melhor áudio original", AudioFormat.BEST_ORIGINAL)
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        form.addRow("Formato:", self.format_combo)

        self.quality_combo = QComboBox()
        for quality, label in MP3_QUALITY_LABELS.items():
            self.quality_combo.addItem(label, quality)
        form.addRow("Qualidade MP3:", self.quality_combo)

        dest_row = QHBoxLayout()
        self.destination_edit = QLineEdit()
        self.destination_edit.setReadOnly(True)
        self.destination_edit.setPlaceholderText("Nenhuma pasta selecionada")
        dest_row.addWidget(self.destination_edit, stretch=1)
        choose_button = QPushButton("ESCOLHER PASTA")
        choose_button.clicked.connect(self._on_choose_folder)
        dest_row.addWidget(choose_button)
        form.addRow("Pasta de destino:", dest_row)
        layout.addLayout(form)

        self.subfolder_checkbox = QCheckBox("Criar pasta com nome da playlist")
        self.subfolder_checkbox.setChecked(True)
        layout.addWidget(self.subfolder_checkbox)

        self.numbering_checkbox = QCheckBox("Numerar músicas pela ordem")
        self.numbering_checkbox.setChecked(True)
        layout.addWidget(self.numbering_checkbox)

        action_row = QHBoxLayout()
        self.download_button = QPushButton("BAIXAR")
        self.download_button.setObjectName("PrimaryButton")
        self.download_button.clicked.connect(self._on_download_clicked)
        action_row.addWidget(self.download_button)

        self.cancel_button = QPushButton("CANCELAR")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        action_row.addWidget(self.cancel_button)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        self.progress_counter_label = QLabel("")
        layout.addWidget(self.progress_counter_label)

        self.progress_current_label = QLabel("")
        layout.addWidget(self.progress_current_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        self.items_list = QListWidget()
        self.items_list.setMaximumHeight(180)
        layout.addWidget(self.items_list)

        details_row = QHBoxLayout()
        self.details_toggle = QToolButton()
        self.details_toggle.setText("▸ DETALHES")
        self.details_toggle.setCheckable(True)
        self.details_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.details_toggle.clicked.connect(self._on_toggle_details)
        details_row.addWidget(self.details_toggle)
        details_row.addStretch(1)
        layout.addLayout(details_row)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(140)
        self.log_view.setVisible(False)
        layout.addWidget(self.log_view)

        layout.addStretch(1)
        self._set_progress_visible(False)

    # ------------------------------------------------------------------
    # Ações da UI
    # ------------------------------------------------------------------

    def _on_format_changed(self) -> None:
        self.quality_combo.setEnabled(self.format_combo.currentData() == AudioFormat.MP3)

    def _on_paste(self) -> None:
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip() if clipboard else ""
        if text:
            self.url_edit.setText(text)

    def _on_choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Pasta de destino dos downloads")
        if folder:
            self.destination_edit.setText(folder)

    def set_destination_folder(self, folder: str) -> None:
        """Usado pela integração com Configurações (item 15: pasta padrão de
        downloads pode ser a própria pasta da biblioteca)."""
        self.destination_edit.setText(folder)

    def _set_progress_visible(self, visible: bool) -> None:
        self.progress_counter_label.setVisible(visible)
        self.progress_current_label.setVisible(visible)
        self.progress_bar.setVisible(visible)
        self.items_list.setVisible(visible)

    def _on_toggle_details(self) -> None:
        expanded = self.details_toggle.isChecked()
        self.details_toggle.setText("▾ DETALHES" if expanded else "▸ DETALHES")
        self.log_view.setVisible(expanded)

    def _append_log(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    def _on_download_clicked(self) -> None:
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.information(
                self, "URL vazia", "Cole a URL de um vídeo ou playlist do YouTube antes de baixar."
            )
            return
        destination_text = self.destination_edit.text().strip()
        if not destination_text:
            QMessageBox.information(self, "Pasta não selecionada", "Escolha uma pasta de destino antes de baixar.")
            return

        options = DownloadOptions(
            url=url,
            destination_folder=Path(destination_text),
            audio_format=self.format_combo.currentData(),
            mp3_quality=self.quality_combo.currentData(),
            create_playlist_subfolder=self.subfolder_checkbox.isChecked(),
            number_tracks=self.numbering_checkbox.isChecked(),
            archive_path=self._archive_path or download_archive_path(),
        )
        self._start_download(options)

    def _start_download(self, options: DownloadOptions) -> None:
        self.items_list.clear()
        self._item_widgets.clear()
        self.log_view.clear()
        self.progress_counter_label.setText("Preparando...")
        self.progress_current_label.setText("")
        self.progress_bar.setValue(0)
        self._set_progress_visible(True)

        self.download_button.setEnabled(False)
        self.cancel_button.setEnabled(True)

        self._worker = DownloadWorker(options, ydl_class=self._ydl_class, ffmpeg_checker=self._ffmpeg_checker)
        self._worker.playlist_detected.connect(self._on_playlist_detected)
        self._worker.item_started.connect(self._on_item_started)
        self._worker.item_progress.connect(self._on_item_progress)
        self._worker.item_finished.connect(self._on_item_finished)
        self._worker.item_failed.connect(self._on_item_failed)
        self._worker.item_skipped.connect(self._on_item_skipped)
        self._worker.log_message.connect(self._append_log)
        self._worker.finished_all.connect(self._on_finished_all)
        self._worker.start()

    def _on_cancel_clicked(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self.cancel_button.setEnabled(False)

    # ------------------------------------------------------------------
    # Reações aos sinais do DownloadWorker
    # ------------------------------------------------------------------

    def _set_item_row(self, index: int, status: str, title: str, tooltip: str = "") -> None:
        item = self._item_widgets.get(index)
        if item is None:
            return
        item.setText(f"{_STATUS_ICON[status]}  {title}")
        item.setData(Qt.ItemDataRole.UserRole, title)
        item.setToolTip(tooltip)

    def _on_playlist_detected(self, total: int, playlist_title: str) -> None:
        self.progress_counter_label.setText(f"0 / {total}")
        for index in range(1, total + 1):
            item = QListWidgetItem()
            self.items_list.addItem(item)
            self._item_widgets[index] = item
            self._set_item_row(index, "waiting", f"Item {index}")

    def _on_item_started(self, index: int, total: int, title: str) -> None:
        self._current_item_title = title
        self.progress_counter_label.setText(f"{index} / {total}")
        self.progress_current_label.setText(f"Baixando:\n{title}")
        self.progress_bar.setValue(0)
        self._set_item_row(index, "downloading", title)

    def _on_item_progress(self, index: int, percent: float, speed: str, eta: str) -> None:
        self.progress_bar.setValue(int(percent))
        extra = "  •  ".join(part for part in (speed, f"ETA {eta}" if eta else "") if part)
        text = f"Baixando:\n{self._current_item_title}"
        if extra:
            text += f"\n{extra}"
        self.progress_current_label.setText(text)

    def _on_item_finished(self, index: int, file_path: str) -> None:
        title = self._item_widgets[index].data(Qt.ItemDataRole.UserRole) if index in self._item_widgets else ""
        self._set_item_row(index, "done", title or self._current_item_title)

    def _on_item_failed(self, index: int, message: str) -> None:
        title = self._item_widgets[index].data(Qt.ItemDataRole.UserRole) if index in self._item_widgets else ""
        self._set_item_row(index, "error", title or self._current_item_title, tooltip=message)

    def _on_item_skipped(self, index: int, reason: str) -> None:
        item = self._item_widgets.get(index)
        title = item.data(Qt.ItemDataRole.UserRole) if item else f"Item {index}"
        self._set_item_row(index, "skipped", title, tooltip=reason)

    def _on_finished_all(self, report: DownloadReport) -> None:
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        if report.cancelled:
            self.progress_current_label.setText("Cancelado.")
        elif report.fatal_error:
            self.progress_current_label.setText("Não foi possível baixar.")
            QMessageBox.warning(self, "Não foi possível baixar", report.fatal_error)
        else:
            self.progress_current_label.setText(
                f"Concluído: {report.success_count} baixada(s), "
                f"{report.skipped_count} já existia(m), {report.error_count} com erro."
            )

        destination = Path(self.destination_edit.text()) if self.destination_edit.text() else None
        self._worker = None
        self.download_finished.emit(report, destination)

    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Cancela e espera o worker (item 32: fechar o app durante um
        download precisa ser seguro, sem thread órfã)."""
        if self._worker is not None:
            self._worker.cancel()
            self._worker.wait(3000)
