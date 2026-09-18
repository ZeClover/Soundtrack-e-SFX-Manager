"""Configuração padrão de logging local (arquivo por dia) para os apps.

Erros nunca devem mostrar traceback bruto ao usuário; o traceback vai para
o arquivo de log e a UI mostra uma mensagem amigável com opção de
"Ver detalhes" que abre o log.
"""

from __future__ import annotations

import logging
import time
from datetime import date
from pathlib import Path

from .app_dirs import app_log_dir

# Cada dia já ganha seu próprio arquivo (rotação por data) — o risco de
# crescimento sem limite não é um arquivo gigante, é acumular um arquivo
# novo por dia para sempre. Mantemos só os últimos N dias (item 61).
_DEFAULT_KEEP_DAYS = 14


def _prune_old_logs(log_dir: Path, filename_prefix: str, keep_days: int = _DEFAULT_KEEP_DAYS) -> None:
    """Apaga arquivos ``{filename_prefix}-*.log`` mais antigos que
    ``keep_days`` dias. Nunca deve impedir o app de abrir: qualquer erro de
    I/O ao limpar (permissão, disco, etc.) é só ignorado."""
    cutoff = time.time() - keep_days * 86400
    try:
        for path in log_dir.glob(f"{filename_prefix}-*.log"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
            except OSError:
                continue
    except OSError:
        pass


def configure_logging(app_slug: str, level: int = logging.INFO) -> Path:
    """Configura logging para console + arquivo diário. Retorna o caminho do arquivo."""
    log_dir = app_log_dir(app_slug)
    log_file = log_dir / f"app-{date.today().isoformat()}.log"
    _prune_old_logs(log_dir, "app")

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Evita handlers duplicados se configure_logging for chamado mais de uma vez
    if not any(isinstance(h, logging.FileHandler) for h in root_logger.handlers):
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    return log_file


def configure_module_log_stream(
    logger_name: str, log_dir: Path, filename_prefix: str, level: int = logging.INFO
) -> Path:
    """Acrescenta um arquivo de log dedicado a um logger específico (por
    prefixo de nome, ex.: ``"soundtrack_app"``), sem parar a propagação
    para o root logger — a mensagem continua indo pro log geral (``app.log``)
    e também vai pro arquivo próprio daquele módulo. Usado pelo RPG Audio
    Studio (item 28: ``logs/app.log``, ``soundtrack.log``, ``sfx.log``,
    ``downloader.log`` — nada de arquivo de log espalhado por aí)."""
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    log_file = log_dir / f"{filename_prefix}-{date.today().isoformat()}.log"
    _prune_old_logs(log_dir, filename_prefix)

    already_routed = any(getattr(handler, "_rpg_audio_route", None) == filename_prefix for handler in logger.handlers)
    if not already_routed:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(formatter)
        handler._rpg_audio_route = filename_prefix  # marca pra não duplicar em chamadas repetidas
        logger.addHandler(handler)

    return log_file
