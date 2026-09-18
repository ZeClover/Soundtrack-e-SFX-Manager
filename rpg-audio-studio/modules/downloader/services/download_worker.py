"""Worker de download (yt-dlp + FFmpeg), rodando em uma QThread própria.

Segue o mesmo padrão já usado pelo ``LibraryScanner`` dos outros módulos:
todo o trabalho roda fora da UI thread, só se comunica por signals, um item
com erro não aborta o restante da playlist, e ``run()`` pode ser chamado
diretamente (sem ``start()``) nos testes para execução síncrona.

``ydl_class`` é injetável (usa ``yt_dlp.YoutubeDL`` por padrão) para os
testes automatizados nunca dependerem de rede de verdade — item 31.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Protocol

from PySide6.QtCore import QThread, Signal
from rpg_audio_shared.paths import ensure_directory, sanitize_filename

from modules.downloader.models import (
    MP3_QUALITY_KBPS,
    AudioFormat,
    DownloadItemResult,
    DownloadOptions,
    DownloadReport,
    ItemStatus,
)
from modules.downloader.services.download_archive import DownloadArchive
from modules.downloader.services.ffmpeg_check import ffmpeg_available
from modules.downloader.services.formatting import format_eta, format_speed
from modules.downloader.services.ytdlp_logger import YtDlpLogger

logger = logging.getLogger(__name__)


class SupportsYoutubeDL(Protocol):
    def __init__(self, opts: dict[str, Any]) -> None: ...
    def __enter__(self) -> "SupportsYoutubeDL": ...
    def __exit__(self, *exc: object) -> None: ...
    def extract_info(self, url: str, download: bool) -> dict[str, Any] | None: ...
    def download(self, urls: list[str]) -> int: ...


def _default_ydl_class():
    import yt_dlp

    return yt_dlp.YoutubeDL


class DownloadWorker(QThread):
    playlist_detected = Signal(int, str)  # total de itens, título da playlist ("" se não for)
    item_started = Signal(int, int, str)  # índice (1-based), total, título
    item_progress = Signal(int, float, str, str)  # índice, percentual 0-100, velocidade, eta
    item_finished = Signal(int, str)  # índice, caminho final do arquivo
    item_failed = Signal(int, str)  # índice, mensagem de erro
    item_skipped = Signal(int, str)  # índice, motivo
    log_message = Signal(str)
    finished_all = Signal(object)  # DownloadReport

    def __init__(
        self,
        options: DownloadOptions,
        ydl_class=None,
        ffmpeg_checker=ffmpeg_available,
        parent=None,
    ):
        super().__init__(parent)
        self._options = options
        self._ydl_class = ydl_class or _default_ydl_class()
        self._ffmpeg_checker = ffmpeg_checker
        self._cancelled = False
        self._archive = DownloadArchive(options.archive_path) if options.archive_path else None

    def cancel(self) -> None:
        self._cancelled = True

    # ------------------------------------------------------------------

    def run(self) -> None:
        report = DownloadReport(total_items=0)

        if self._options.audio_format == AudioFormat.MP3 and not self._ffmpeg_checker():
            message = (
                "FFmpeg não foi encontrado. Ele é necessário para converter para MP3 — "
                "instale o FFmpeg ou escolha 'Melhor áudio original'."
            )
            self.log_message.emit(message)
            report.fatal_error = message
            self.finished_all.emit(report)
            return

        try:
            entries, playlist_title = self._probe(self._options.url)
        except Exception as exc:  # noqa: BLE001 - link inválido não pode derrubar o app
            logger.warning("Falha ao abrir o link do Downloader", exc_info=True)
            message = f"Não foi possível abrir o link: {exc}"
            self.log_message.emit(message)
            report.fatal_error = message
            self.finished_all.emit(report)
            return

        total = len(entries)
        report.total_items = total
        self.playlist_detected.emit(total, playlist_title)

        if total == 0:
            self.log_message.emit("Nenhum item encontrado nesse link.")
            self.finished_all.emit(report)
            return

        if total > 1:
            self.log_message.emit(f"Playlist detectada\n{total} itens encontrados")
        self.log_message.emit("Download iniciado")

        for index, entry in enumerate(entries, start=1):
            if self._cancelled:
                self.log_message.emit("Cancelado pelo usuário.")
                report.cancelled = True
                break

            self._download_entry(entry, index, total, playlist_title, report)

        if not report.cancelled:
            self.log_message.emit("Finalizado")
        self.finished_all.emit(report)

    # ------------------------------------------------------------------

    def _download_entry(
        self, entry: dict[str, Any], index: int, total: int, playlist_title: str, report: DownloadReport
    ) -> None:
        title = entry.get("title") or entry.get("id") or f"Item {index}"
        video_id = str(entry.get("id") or "")

        if self._archive is not None and self._archive.contains(video_id):
            self.item_skipped.emit(index, "já baixado anteriormente")
            self.log_message.emit(f"{index:02d} já baixado — pulando")
            report.completed.append(DownloadItemResult(index, title, ItemStatus.SKIPPED))
            return

        self.item_started.emit(index, total, title)
        try:
            file_path = self._download_one(entry, index, total, playlist_title)
            if self._archive is not None and video_id:
                self._archive.add(video_id)
            self.item_finished.emit(index, str(file_path) if file_path else "")
            self.log_message.emit(f"{index:02d} concluído")
            report.completed.append(DownloadItemResult(index, title, ItemStatus.DONE, file_path=file_path))
        except Exception as exc:  # noqa: BLE001 - um item ruim não pode abortar a playlist
            logger.warning("Falha ao baixar item %s (%s)", index, title, exc_info=True)
            self.item_failed.emit(index, str(exc))
            self.log_message.emit(f"{index:02d} indisponível — continuando")
            report.completed.append(
                DownloadItemResult(index, title, ItemStatus.ERROR, error_message=str(exc))
            )

    def _probe(self, url: str) -> tuple[list[dict[str, Any]], str]:
        probe_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": "in_playlist",
            "logger": YtDlpLogger(self.log_message.emit),
        }
        with self._ydl_class(probe_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if info is None:
            return [], ""
        if info.get("entries") is not None:
            entries = [e for e in info["entries"] if e]
            return entries, info.get("title") or ""
        return [info], ""

    def _download_one(
        self, entry: dict[str, Any], index: int, total: int, playlist_title: str
    ) -> Path | None:
        outtmpl = self._build_outtmpl(index, total, playlist_title)
        ydl_opts = self._build_ydl_opts(outtmpl, index)

        result: dict[str, str] = {}

        def _hook(data: dict[str, Any]) -> None:
            status = data.get("status")
            if status == "downloading":
                downloaded = data.get("downloaded_bytes") or 0
                total_bytes = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
                percent = (downloaded / total_bytes * 100) if total_bytes else 0.0
                self.item_progress.emit(
                    index, percent, format_speed(data.get("speed")), format_eta(data.get("eta"))
                )
            elif status == "finished":
                filename = data.get("filename")
                if filename:
                    result["path"] = filename

        ydl_opts["progress_hooks"] = [_hook]

        entry_url = entry.get("webpage_url") or entry.get("url") or entry.get("id")
        with self._ydl_class(ydl_opts) as ydl:
            ydl.download([str(entry_url)])

        path_str = result.get("path")
        return Path(path_str) if path_str else None

    def _build_outtmpl(self, index: int, total: int, playlist_title: str) -> str:
        destination = Path(self._options.destination_folder)
        if self._options.create_playlist_subfolder and playlist_title:
            destination = destination / sanitize_filename(playlist_title)
        ensure_directory(destination)

        prefix = f"{index:03d} - " if self._options.number_tracks and total > 1 else ""
        return str(destination / f"{prefix}%(title)s.%(ext)s")

    def _build_ydl_opts(self, outtmpl: str, index: int) -> dict[str, Any]:
        opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            # Nunca deixa o yt-dlp escrever nomes de arquivo inválidos no
            # Windows (\\ / : * ? " < > |) — reforça o que sanitize_filename
            # já faz para a subpasta da playlist.
            "windowsfilenames": True,
            "logger": YtDlpLogger(self.log_message.emit),
            "outtmpl": outtmpl,
            "retries": 3,
        }
        if self._options.audio_format == AudioFormat.MP3:
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": MP3_QUALITY_KBPS[self._options.mp3_quality],
                }
            ]
        else:
            opts["format"] = "bestaudio/best"
        return opts
