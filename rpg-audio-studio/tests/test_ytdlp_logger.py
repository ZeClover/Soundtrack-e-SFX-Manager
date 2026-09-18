"""Regressão específica do Downloader (item 13): o yt-dlp nunca deve tentar
escrever em stdout/stderr diretamente — tudo passa pelo YtDlpLogger, que só
usa ``logging`` e um callback opcional."""

from __future__ import annotations

import sys

from modules.downloader.services.ytdlp_logger import YtDlpLogger


def test_logger_methods_work_even_with_stdout_and_stderr_none(monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    logger = YtDlpLogger()
    logger.debug("[debug] alguma linha interna do yt-dlp")
    logger.info("info qualquer")
    logger.warning("algum aviso")
    logger.error("algum erro")
    # se chegou até aqui sem AttributeError, a regressão não se repetiu


def test_warning_and_error_forward_to_on_message_callback():
    messages: list[str] = []
    logger = YtDlpLogger(on_message=messages.append)

    logger.debug("não deveria aparecer para o usuário")
    logger.warning("aviso importante")
    logger.error("erro importante")

    assert any("aviso importante" in m for m in messages)
    assert any("erro importante" in m for m in messages)
    assert not any("não deveria aparecer" in m for m in messages)


def test_broken_callback_never_propagates_out_of_logger():
    def _broken(_msg: str) -> None:
        raise RuntimeError("callback quebrado")

    logger = YtDlpLogger(on_message=_broken)
    logger.warning("teste")  # não deve lançar
    logger.error("teste")  # não deve lançar
