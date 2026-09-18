from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from rpg_audio_shared.logging_setup import _DEFAULT_KEEP_DAYS, configure_module_log_stream


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


def test_old_log_files_of_the_same_prefix_are_pruned(tmp_path: Path):
    """Regressão da Etapa 6 (item 61): sem limpeza, um arquivo novo por dia
    acumularia pra sempre — arquivos com mais de ``_DEFAULT_KEEP_DAYS`` dias
    do mesmo prefixo devem ser removidos ao (re)configurar o logging."""
    old_file = tmp_path / "sfx-2000-01-01.log"
    old_file.write_text("mensagem antiga", encoding="utf-8")
    old_timestamp = time.time() - (_DEFAULT_KEEP_DAYS + 1) * 86400
    os.utime(old_file, (old_timestamp, old_timestamp))

    recent_file = tmp_path / "sfx-2000-01-02.log"
    recent_file.write_text("mensagem recente", encoding="utf-8")

    other_prefix_old_file = tmp_path / "soundtrack-2000-01-01.log"
    other_prefix_old_file.write_text("outro módulo", encoding="utf-8")
    os.utime(other_prefix_old_file, (old_timestamp, old_timestamp))

    _reset_logger("test.module.e")
    try:
        configure_module_log_stream("test.module.e", tmp_path, "sfx")

        assert not old_file.exists()
        assert recent_file.exists()
        assert other_prefix_old_file.exists()  # não mexe em prefixo de outro módulo
    finally:
        _reset_logger("test.module.e")
