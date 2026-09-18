"""Regressão (item 32): fechar o RPG Audio Studio com um download de
verdade em andamento (thread real, não mockada como só .run() síncrono)
precisa ser seguro — cancela e espera, sem travar nem lançar."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from modules.downloader.models import DownloadOptions
from modules.downloader.services.download_worker import DownloadWorker
from modules.downloader.ui.downloader_page import DownloaderPage


def _slow_fake_ydl_class(item_delay: float = 0.2, started_event: threading.Event | None = None):
    """``started_event`` é setado bem no início de ``download()`` — o teste
    espera por ele antes de cancelar, pra garantir que está mesmo
    interrompendo um download em andamento (e não vencendo uma corrida
    contra uma QThread que ainda nem começou a rodar, o que fazia esta
    checagem passar "por acidente" sem testar nada de verdade)."""

    class _SlowFakeYDL:
        instances: list["_SlowFakeYDL"] = []

        def __init__(self, opts):
            self.opts = opts
            _SlowFakeYDL.instances.append(self)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def extract_info(self, url, download=False):
            return {"id": "abc", "title": "Faixa Lenta", "webpage_url": "abc"}

        def download(self, urls):
            if started_event is not None:
                started_event.set()
            time.sleep(item_delay)
            hook = self.opts.get("progress_hooks", [None])[0]
            if hook:
                hook({"status": "finished", "filename": "faixa.mp3"})
            return 0

    return _SlowFakeYDL


def test_downloader_page_shutdown_while_real_thread_is_running_does_not_hang(qt_core_app, tmp_path: Path):
    started = threading.Event()
    ydl_class = _slow_fake_ydl_class(item_delay=0.3, started_event=started)
    page = DownloaderPage(ydl_class=ydl_class, ffmpeg_checker=lambda: True, archive_path=tmp_path / "archive.txt")
    page.url_edit.setText("https://youtu.be/abc")
    page.destination_edit.setText(str(tmp_path))

    page._on_download_clicked()  # dispara worker.start() de verdade (QThread real)
    assert page._worker is not None
    assert started.wait(timeout=2), "o download nunca chegou a começar de verdade"
    assert page._worker.isRunning()  # agora sim, garantidamente no meio do trabalho

    page.shutdown()  # não pode travar nem lançar, mesmo com a thread ainda rodando

    assert page._worker is None or not page._worker.isRunning()


def test_download_worker_cancel_stops_a_real_running_thread(qt_core_app, tmp_path: Path):
    started = threading.Event()
    ydl_class = _slow_fake_ydl_class(item_delay=0.3, started_event=started)
    options = DownloadOptions(url="https://youtu.be/abc", destination_folder=tmp_path)
    worker = DownloadWorker(options, ydl_class=ydl_class, ffmpeg_checker=lambda: True)

    finished = []
    worker.finished_all.connect(finished.append)
    worker.start()
    assert started.wait(timeout=2), "o download nunca chegou a começar de verdade"
    assert worker.isRunning()

    worker.cancel()
    assert worker.wait(3000)  # termina dentro do prazo, sem travar o teste
