"""Testes do DownloadWorker com yt-dlp totalmente mockado (item 31: "use
mocks para YouTube... não dependa de internet nos testes automatizados").
"""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.downloader.models import AudioFormat, DownloadOptions, ItemStatus, Mp3Quality
from modules.downloader.services.download_worker import DownloadWorker


def make_fake_ydl_class(probe_result, download_effects):
    """``download_effects`` é consumida em ordem, uma por chamada a
    ``.download()`` (uma por item da playlist, na ordem em que o worker
    processa) — cada efeito simula o que o hook de progresso do yt-dlp
    faria (sucesso) ou lança uma exceção (falha daquele item)."""
    state = {"call_index": 0}

    class FakeYDL:
        instances: list["FakeYDL"] = []

        def __init__(self, opts):
            self.opts = opts
            FakeYDL.instances.append(self)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def extract_info(self, url, download=False):
            return probe_result

        def download(self, urls):
            index = state["call_index"]
            state["call_index"] += 1
            effect = download_effects[index]
            effect(self, urls)
            return 0

    return FakeYDL


def _finish(path: str):
    def _effect(ydl, urls):
        ydl.opts["progress_hooks"][0]({"status": "downloading", "downloaded_bytes": 50, "total_bytes": 100})
        ydl.opts["progress_hooks"][0]({"status": "finished", "filename": path})

    return _effect


def _fail(message: str):
    def _effect(ydl, urls):
        raise RuntimeError(message)

    return _effect


def _run_worker(worker: DownloadWorker):
    events: dict[str, list] = {
        "playlist_detected": [], "item_started": [], "item_progress": [], "item_finished": [],
        "item_failed": [], "item_skipped": [], "log_message": [], "finished_all": [],
    }
    worker.playlist_detected.connect(lambda *a: events["playlist_detected"].append(a))
    worker.item_started.connect(lambda *a: events["item_started"].append(a))
    worker.item_progress.connect(lambda *a: events["item_progress"].append(a))
    worker.item_finished.connect(lambda *a: events["item_finished"].append(a))
    worker.item_failed.connect(lambda *a: events["item_failed"].append(a))
    worker.item_skipped.connect(lambda *a: events["item_skipped"].append(a))
    worker.log_message.connect(lambda msg: events["log_message"].append(msg))
    worker.finished_all.connect(lambda report: events["finished_all"].append(report))
    worker.run()  # síncrono — sem start(), igual ao padrão do LibraryScanner
    return events


def test_single_video_download_success(tmp_path: Path):
    probe_result = {"id": "abc123", "title": "Song A", "webpage_url": "https://youtu.be/abc123"}
    ydl_class = make_fake_ydl_class(probe_result, [_finish(str(tmp_path / "Song A.mp3"))])

    options = DownloadOptions(url="https://youtu.be/abc123", destination_folder=tmp_path)
    worker = DownloadWorker(options, ydl_class=ydl_class, ffmpeg_checker=lambda: True)
    events = _run_worker(worker)

    report = events["finished_all"][0]
    assert report.total_items == 1
    assert report.success_count == 1
    assert events["item_finished"][0] == (1, str(tmp_path / "Song A.mp3"))
    assert events["playlist_detected"][0] == (1, "")


def test_playlist_item_failure_does_not_abort_playlist(tmp_path: Path):
    probe_result = {
        "title": "Minha Playlist",
        "entries": [
            {"id": "v1", "title": "Track 1", "url": "v1"},
            {"id": "v2", "title": "Track 2", "url": "v2"},
            {"id": "v3", "title": "Track 3", "url": "v3"},
        ],
    }
    ydl_class = make_fake_ydl_class(
        probe_result,
        [
            _finish(str(tmp_path / "001 - Track 1.mp3")),
            _fail("Vídeo indisponível"),
            _finish(str(tmp_path / "003 - Track 3.mp3")),
        ],
    )

    options = DownloadOptions(url="https://youtu.be/playlist?list=x", destination_folder=tmp_path)
    worker = DownloadWorker(options, ydl_class=ydl_class, ffmpeg_checker=lambda: True)
    events = _run_worker(worker)

    report = events["finished_all"][0]
    assert report.total_items == 3
    assert report.success_count == 2
    assert report.error_count == 1
    assert len(events["item_failed"]) == 1
    assert events["item_failed"][0][0] == 2  # o item 2 falhou...
    assert len(events["item_finished"]) == 2  # ...mas 1 e 3 continuaram normalmente


def test_cancel_stops_before_remaining_items(tmp_path: Path):
    probe_result = {
        "title": "Playlist Grande",
        "entries": [{"id": f"v{i}", "title": f"Track {i}", "url": f"v{i}"} for i in range(1, 6)],
    }

    worker_holder: dict[str, DownloadWorker] = {}

    def _finish_then_cancel(path: str):
        def _effect(ydl, urls):
            ydl.opts["progress_hooks"][0]({"status": "finished", "filename": path})
            worker_holder["worker"].cancel()

        return _effect

    ydl_class = make_fake_ydl_class(
        probe_result,
        [_finish_then_cancel(str(tmp_path / "001.mp3"))] + [_finish(str(tmp_path / f"{i:03d}.mp3")) for i in range(2, 6)],
    )

    options = DownloadOptions(url="https://youtu.be/playlist?list=x", destination_folder=tmp_path)
    worker = DownloadWorker(options, ydl_class=ydl_class, ffmpeg_checker=lambda: True)
    worker_holder["worker"] = worker
    events = _run_worker(worker)

    report = events["finished_all"][0]
    assert report.cancelled is True
    assert len(report.completed) == 1  # só o primeiro item foi processado
    assert len(ydl_class.instances) == 2  # 1 probe + 1 download (o resto nunca chegou a rodar)


def test_download_archive_skips_already_downloaded_item(tmp_path: Path):
    archive_path = tmp_path / "archive.txt"
    archive_path.write_text("v1\n", encoding="utf-8")

    probe_result = {
        "title": "Playlist",
        "entries": [
            {"id": "v1", "title": "Já baixada", "url": "v1"},
            {"id": "v2", "title": "Nova", "url": "v2"},
        ],
    }
    ydl_class = make_fake_ydl_class(probe_result, [_finish(str(tmp_path / "Nova.mp3"))])

    options = DownloadOptions(
        url="https://youtu.be/playlist?list=x", destination_folder=tmp_path, archive_path=archive_path,
    )
    worker = DownloadWorker(options, ydl_class=ydl_class, ffmpeg_checker=lambda: True)
    events = _run_worker(worker)

    report = events["finished_all"][0]
    assert report.skipped_count == 1
    assert report.success_count == 1
    assert events["item_skipped"][0][0] == 1
    # só baixou o item novo: 1 probe + 1 download (não 2)
    assert len(ydl_class.instances) == 2
    # e o item novo foi registrado no archive para a próxima vez
    assert "v2" in archive_path.read_text(encoding="utf-8")


def test_ffmpeg_missing_blocks_mp3_download_with_friendly_error(tmp_path: Path):
    ydl_class = make_fake_ydl_class({"id": "x", "title": "X"}, [])
    options = DownloadOptions(
        url="https://youtu.be/x", destination_folder=tmp_path, audio_format=AudioFormat.MP3,
    )
    worker = DownloadWorker(options, ydl_class=ydl_class, ffmpeg_checker=lambda: False)
    events = _run_worker(worker)

    report = events["finished_all"][0]
    assert report.fatal_error != ""
    assert "FFmpeg" in report.fatal_error
    assert ydl_class.instances == []  # nunca chegou a tentar extrair nem baixar nada


def test_best_original_format_does_not_require_ffmpeg(tmp_path: Path):
    probe_result = {"id": "abc", "title": "Song", "webpage_url": "https://youtu.be/abc"}
    ydl_class = make_fake_ydl_class(probe_result, [_finish(str(tmp_path / "Song.opus"))])
    options = DownloadOptions(
        url="https://youtu.be/abc", destination_folder=tmp_path, audio_format=AudioFormat.BEST_ORIGINAL,
    )
    worker = DownloadWorker(options, ydl_class=ydl_class, ffmpeg_checker=lambda: False)
    events = _run_worker(worker)

    report = events["finished_all"][0]
    assert report.success_count == 1


def test_ydl_opts_never_rely_on_stdout_and_sanitize_windows_names(tmp_path: Path):
    probe_result = {"id": "abc", "title": "Song", "webpage_url": "https://youtu.be/abc"}
    ydl_class = make_fake_ydl_class(probe_result, [_finish(str(tmp_path / "Song.mp3"))])
    options = DownloadOptions(url="https://youtu.be/abc", destination_folder=tmp_path)
    worker = DownloadWorker(options, ydl_class=ydl_class, ffmpeg_checker=lambda: True)
    _run_worker(worker)

    download_opts = ydl_class.instances[1].opts  # instances[0] é o probe
    assert download_opts["quiet"] is True
    assert download_opts["noprogress"] is True
    assert download_opts["windowsfilenames"] is True
    assert "logger" in download_opts
    assert download_opts["postprocessors"][0]["preferredcodec"] == "mp3"
    assert download_opts["postprocessors"][0]["preferredquality"] == "192"  # HIGH por padrão


def test_numbering_and_playlist_subfolder_in_outtmpl(tmp_path: Path):
    options = DownloadOptions(
        url="x", destination_folder=tmp_path, create_playlist_subfolder=True, number_tracks=True,
    )
    worker = DownloadWorker(options, ydl_class=object, ffmpeg_checker=lambda: True)
    outtmpl = worker._build_outtmpl(index=3, total=10, playlist_title="Trilha: Épica / Final")

    assert str(tmp_path) in outtmpl
    assert "003 - " in outtmpl
    assert "%(title)s.%(ext)s" in outtmpl
    # nome de playlist sanitizado (sem ':' nem '/', inválidos no Windows)
    assert ":" not in Path(outtmpl).parent.name
    assert "/" not in Path(outtmpl).parent.name.replace(str(tmp_path), "")


def test_numbering_disabled_and_no_subfolder(tmp_path: Path):
    options = DownloadOptions(
        url="x", destination_folder=tmp_path, create_playlist_subfolder=False, number_tracks=False,
    )
    worker = DownloadWorker(options, ydl_class=object, ffmpeg_checker=lambda: True)
    outtmpl = worker._build_outtmpl(index=1, total=5, playlist_title="Alguma Playlist")

    assert outtmpl == str(tmp_path / "%(title)s.%(ext)s")


@pytest.mark.parametrize("quality,expected", [
    (Mp3Quality.HIGH, "192"), (Mp3Quality.MEDIUM, "128"), (Mp3Quality.ECONOMIC, "96"),
])
def test_mp3_quality_maps_to_expected_bitrate(tmp_path: Path, quality, expected):
    options = DownloadOptions(url="x", destination_folder=tmp_path, mp3_quality=quality)
    worker = DownloadWorker(options, ydl_class=object, ffmpeg_checker=lambda: True)
    opts = worker._build_ydl_opts("out.%(ext)s", index=1)
    assert opts["postprocessors"][0]["preferredquality"] == expected
