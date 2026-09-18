from __future__ import annotations

import logging
from pathlib import Path

from rpg_audio_shared.logging_setup import configure_module_log_stream


def _reset_logger(name: str) -> None:
    logger = logging.getLogger(name)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


def test_configure_module_log_stream_writes_to_its_own_file(tmp_path: Path):
    _reset_logger("test.module.a")
    try:
        log_path = configure_module_log_stream("test.module.a", tmp_path, "soundtrack")
        logging.getLogger("test.module.a").info("mensagem de teste")
        for handler in logging.getLogger("test.module.a").handlers:
            handler.flush()

        assert log_path.exists()
        assert "mensagem de teste" in log_path.read_text(encoding="utf-8")
        assert log_path.name.startswith("soundtrack-")
    finally:
        _reset_logger("test.module.a")


def test_configure_module_log_stream_is_idempotent(tmp_path: Path):
    _reset_logger("test.module.b")
    try:
        configure_module_log_stream("test.module.b", tmp_path, "sfx")
        configure_module_log_stream("test.module.b", tmp_path, "sfx")
        handlers = [h for h in logging.getLogger("test.module.b").handlers if isinstance(h, logging.FileHandler)]
        assert len(handlers) == 1  # não duplica o handler em chamadas repetidas
    finally:
        _reset_logger("test.module.b")


def test_different_prefixes_get_different_files(tmp_path: Path):
    _reset_logger("test.module.c")
    try:
        path_a = configure_module_log_stream("test.module.c", tmp_path, "downloader")
        path_b = configure_module_log_stream("test.module.c", tmp_path, "other")
        assert path_a != path_b
        handlers = [h for h in logging.getLogger("test.module.c").handlers if isinstance(h, logging.FileHandler)]
        assert len(handlers) == 2
    finally:
        _reset_logger("test.module.c")


def test_messages_still_propagate_to_root_logger(tmp_path: Path):
    """O arquivo dedicado é um extra — as mensagens continuam indo pro
    root logger normalmente (app.log geral continua recebendo tudo)."""
    _reset_logger("test.module.d")
    try:
        configure_module_log_stream("test.module.d", tmp_path, "sfx")
        assert logging.getLogger("test.module.d").propagate is True
    finally:
        _reset_logger("test.module.d")
