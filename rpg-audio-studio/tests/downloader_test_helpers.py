"""Fábricas de yt-dlp falso compartilhadas entre ``test_download_worker.py``
e ``test_downloader_page.py``.

Importado sempre por caminho relativo (``from .downloader_test_helpers
import ...``), nunca como ``from tests.downloader_test_helpers import
...`` — o monorepo tem uma pasta ``tests/`` em cada um dos quatro
projetos (``shared``, ``soundtrack-manager``, ``sfx-manager``,
``rpg-audio-studio``), e um import absoluto começando com ``tests.`` pode
resolver para a pasta ``tests/`` de outro projeto quando os testes de mais
de um projeto rodam no mesmo processo Python (por exemplo,
`BUILD_WINDOWS.bat` chamando `pytest` várias vezes a partir do mesmo
diretório de trabalho) — o nome "tests" nesse caso não é exclusivo desta
pasta.
"""

from __future__ import annotations


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
