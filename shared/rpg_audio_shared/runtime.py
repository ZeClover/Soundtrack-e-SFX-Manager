"""Detecção de app empacotado (frozen, via PyInstaller) — item 8 da Etapa 6.

Nunca confundir isto com onde os DADOS DO USUÁRIO ficam: dados do usuário
sempre usam :mod:`rpg_audio_shared.app_dirs` (baseado em ``%APPDATA%``),
frozen ou não. Este módulo só resolve onde os RECURSOS do próprio app
(ícone, FFmpeg empacotado, assets) estão — que muda conforme o app está
rodando do código-fonte ou de um executável gerado pelo PyInstaller.
"""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    """True quando rodando dentro de um executável gerado pelo PyInstaller
    (ou equivalente que define ``sys.frozen``)."""
    return bool(getattr(sys, "frozen", False))


def frozen_base_dir() -> Path | None:
    """Diretório base dos recursos empacotados, ou ``None`` se não estiver
    rodando como executável empacotado (nesse caso cada app resolve seus
    próprios recursos relativos ao código-fonte).

    - One-file: PyInstaller extrai tudo para uma pasta temporária exposta
      em ``sys._MEIPASS`` — os recursos ficam lá.
    - One-folder: o processo roda direto da pasta que contém o ``.exe``
      (``sys.executable``), e os recursos ficam ao lado dele.
    """
    if not is_frozen():
        return None
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(sys.executable).resolve().parent
