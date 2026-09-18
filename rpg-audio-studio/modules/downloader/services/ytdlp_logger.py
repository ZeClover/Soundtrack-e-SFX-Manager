"""Logger próprio para o yt-dlp.

Nunca deixa o yt-dlp escrever diretamente em stdout/stderr — tudo passa
pelo módulo ``logging`` (arquivo de log) e por um callback opcional para
mensagens amigáveis na UI. Isso é o que evita reproduzir a regressão
conhecida do Downloader antigo: rodando com ``pythonw.exe`` (sem console),
``sys.stdout``/``sys.stderr`` ficam ``None``, e qualquer biblioteca que
tente escrever neles quebra com
``'NoneType' object has no attribute 'write'``. Combinado com
``rpg_audio_shared.stdio_guard.ensure_stdio()`` (chamado no início do
``main()`` do Studio) e com ``quiet=True``/``noprogress=True`` nas opções
do yt-dlp, este logger garante que a biblioteca nunca tenta escrever fora
do ``logging``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)


class YtDlpLogger:
    def __init__(self, on_message: Callable[[str], None] | None = None):
        self._on_message = on_message

    def debug(self, msg: str) -> None:
        logger.debug(msg)

    def info(self, msg: str) -> None:
        logger.info(msg)

    def warning(self, msg: str) -> None:
        logger.warning(msg)
        self._notify(f"Aviso: {msg}")

    def error(self, msg: str) -> None:
        logger.error(msg)
        self._notify(f"Erro: {msg}")

    def _notify(self, msg: str) -> None:
        if self._on_message is None:
            return
        try:
            self._on_message(msg)
        except Exception:
            logger.exception("Falha ao notificar mensagem de log do downloader")
