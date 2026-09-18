"""Testes da página do Downloader — reaproveita os mocks de yt-dlp de
test_download_worker.py e roda o worker de forma síncrona (start() vira
run(), assim como os outros testes do repositório fazem com QThread)."""

from __future__ import annotations

from pathlib import Path

from modules.downloader.models import AudioFormat, DownloadReport
from modules.downloader.services.download_worker import DownloadWorker
from modules.downloader.ui.downloader_page import DownloaderPage
from tests.test_download_worker import _fail, _finish, make_fake_ydl_class


def _make_synchronous_page(monkeypatch, ydl_class, tmp_path: Path) -> DownloaderPage:
    # QThread.start() de verdade cria uma thread do SO; nos testes (sem
    # app.exec() rodando) isso não entrega os sinais de forma confiável, então
    # trocamos start() por run() só aqui — mesma técnica usada nos testes do
    # LibraryScanner dos outros módulos.
    monkeypatch.setattr(DownloadWorker, "start", DownloadWorker.run)
    # archive_path isolado: sem isso, a página usaria o archive real do
    # usuário (~/.rpg-audio-toolkit/...) e poluiria/seria poluída por
    # execuções anteriores — mesmo cuidado que db_path=tmp_path nos outros módulos.
    return DownloaderPage(
        ydl_class=ydl_class, ffmpeg_checker=lambda: True, archive_path=tmp_path / "archive.txt"
    )


def test_download_button_requires_url_and_destination(qt_core_app, monkeypatch, tmp_path: Path):
    page = _make_synchronous_page(monkeypatch, make_fake_ydl_class({}, []), tmp_path)
    monkeypatch.setattr(
        "modules.downloader.ui.downloader_page.QMessageBox.information", lambda *a, **k: None
    )

    page._on_download_clicked()  # sem URL nem pasta: não deve criar worker
    assert page._worker is None


def test_full_flow_updates_progress_and_item_list(qt_core_app, tmp_path: Path, monkeypatch):
    probe_result = {
        "title": "Minha Playlist",
        "entries": [
            {"id": "v1", "title": "Track 1", "url": "v1"},
            {"id": "v2", "title": "Track 2", "url": "v2"},
        ],
    }
    ydl_class = make_fake_ydl_class(
        probe_result,
        [_finish(str(tmp_path / "001 - Track 1.mp3")), _fail("indisponível")],
    )
    page = _make_synchronous_page(monkeypatch, ydl_class, tmp_path)

    page.url_edit.setText("https://youtu.be/playlist?list=x")
    page.destination_edit.setText(str(tmp_path))

    received: list[tuple] = []
    page.download_finished.connect(lambda report, dest: received.append((report, dest)))

    page._on_download_clicked()

    assert page.progress_counter_label.text() == "2 / 2"
    assert page.items_list.count() == 2
    assert page.items_list.item(0).text().startswith("✓")
    assert page.items_list.item(1).text().startswith("!")

    assert len(received) == 1
    report, destination = received[0]
    assert isinstance(report, DownloadReport)
    assert report.success_count == 1
    assert report.error_count == 1
    assert destination == tmp_path

    # UI volta ao estado pronto para um novo download
    assert page.download_button.isEnabled() is True
    assert page.cancel_button.isEnabled() is False
    assert page._worker is None


def test_ffmpeg_missing_shows_warning_and_keeps_ui_usable(qt_core_app, tmp_path: Path, monkeypatch):
    ydl_class = make_fake_ydl_class({"id": "x", "title": "X"}, [])
    monkeypatch.setattr(DownloadWorker, "start", DownloadWorker.run)
    warnings: list[str] = []
    monkeypatch.setattr(
        "modules.downloader.ui.downloader_page.QMessageBox.warning",
        lambda *a, **k: warnings.append(a[2] if len(a) > 2 else ""),
    )

    page = DownloaderPage(ydl_class=ydl_class, ffmpeg_checker=lambda: False, archive_path=tmp_path / "archive.txt")
    page.url_edit.setText("https://youtu.be/x")
    page.destination_edit.setText(str(tmp_path))
    page.format_combo.setCurrentIndex(0)  # MP3

    page._on_download_clicked()

    assert warnings and "FFmpeg" in warnings[0]
    assert page.download_button.isEnabled() is True  # não trava a UI


def test_details_panel_starts_collapsed_and_toggles(qt_core_app):
    # isVisibleTo (não isVisible) porque a página nunca é exibida de
    # verdade (.show()) neste teste headless — isVisible() dependeria da
    # cadeia inteira de ancestrais estar numa janela realmente visível.
    page = DownloaderPage()
    assert page.log_view.isVisibleTo(page) is False
    page.details_toggle.setChecked(True)
    page._on_toggle_details()
    assert page.log_view.isVisibleTo(page) is True


def test_format_change_disables_quality_for_best_original(qt_core_app):
    page = DownloaderPage()
    assert page.quality_combo.isEnabled() is True
    index = page.format_combo.findData(AudioFormat.BEST_ORIGINAL)
    page.format_combo.setCurrentIndex(index)
    assert page.quality_combo.isEnabled() is False


def test_archive_path_is_isolated_and_never_touches_real_user_archive(qt_core_app, tmp_path: Path, monkeypatch):
    """Regressão: a página não pode usar o archive real do usuário nos
    testes (foi pego durante o desenvolvimento — sem um archive_path
    injetável, um "v1" gravado por um teste anterior fazia outro teste
    pular um item que deveria baixar, e sujava dados reais do usuário)."""
    monkeypatch.setattr(DownloadWorker, "start", DownloadWorker.run)
    real_path_calls = []
    monkeypatch.setattr(
        "modules.downloader.ui.downloader_page.download_archive_path",
        lambda: real_path_calls.append(True) or (tmp_path / "should-not-be-used.txt"),
    )

    probe_result = {"id": "v1", "title": "Track", "webpage_url": "v1"}
    ydl_class = make_fake_ydl_class(probe_result, [_finish(str(tmp_path / "Track.mp3"))])
    page = DownloaderPage(ydl_class=ydl_class, ffmpeg_checker=lambda: True, archive_path=tmp_path / "own.txt")
    page.url_edit.setText("https://youtu.be/v1")
    page.destination_edit.setText(str(tmp_path))

    page._on_download_clicked()

    assert real_path_calls == []  # nunca chamou o resolvedor do caminho real
    assert (tmp_path / "own.txt").exists()


def test_shutdown_cancels_running_worker(qt_core_app, tmp_path: Path, monkeypatch):
    # Worker que nunca termina sozinho (simula um download em andamento) —
    # shutdown() precisa cancelar e não travar o teste.
    class _NeverEndingWorker(DownloadWorker):
        def run(self) -> None:  # não emite finished_all — simula "em andamento"
            return

    page = DownloaderPage()
    page._worker = _NeverEndingWorker.__new__(_NeverEndingWorker)  # não roda de verdade
    cancelled = []
    page._worker.cancel = lambda: cancelled.append(True)
    page._worker.wait = lambda *_a, **_k: True

    page.shutdown()
    assert cancelled == [True]
