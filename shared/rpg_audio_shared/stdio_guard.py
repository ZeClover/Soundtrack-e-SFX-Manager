"""Garante que ``sys.stdout``/``sys.stderr`` nunca sejam ``None``.

Quando um app Qt é iniciado com ``pythonw.exe`` (sem console) no Windows —
como acontece ao abrir por duplo clique, sem terminal — o Python deixa
``sys.stdout`` e ``sys.stderr`` como ``None``. Qualquer biblioteca que
tente escrever neles diretamente (em vez de usar ``logging``) quebra com
``'NoneType' object has no attribute 'write'``. O RPG Audio Downloader já
teve exatamente esse bug com o yt-dlp.

Chamar :func:`ensure_stdio` bem no início do ``main()`` de qualquer app da
suíte substitui um ``None`` por um escritor nulo (que aceita ``.write()``,
``.flush()``, ``.isatty()`` sem erro), tornando o processo seguro tanto com
``python.exe`` quanto com ``pythonw.exe`` — e também dentro do executável
final (Etapa 6), que roda sem console.
"""

from __future__ import annotations

import sys


class _NullWriter:
    """Stream nula: aceita escrita/flush sem erro e nunca é um terminal."""

    def write(self, data: str) -> int:
        return len(data) if data else 0

    def flush(self) -> None:
        return None

    def isatty(self) -> bool:
        return False

    def close(self) -> None:
        return None


def ensure_stdio() -> None:
    """Substitui ``sys.stdout``/``sys.stderr`` por uma stream nula se
    estiverem ``None`` (caso do ``pythonw.exe``/app empacotado sem
    console)."""
    if sys.stdout is None:
        sys.stdout = _NullWriter()
    if sys.stderr is None:
        sys.stderr = _NullWriter()
