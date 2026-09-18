"""Localização do FFmpeg/FFprobe (item 5 da Etapa 6): primeiro tenta uma
cópia empacotada junto do app, só cai pro PATH do sistema como alternativa
— o usuário final não deveria precisar instalar/configurar FFmpeg à mão.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


def _executable_name(base_name: str) -> str:
    return f"{base_name}.exe" if sys.platform == "win32" else base_name


def find_ffmpeg_binary(base_name: str, bundled_dir: Path | None = None) -> Path | None:
    """``base_name`` é ``"ffmpeg"`` ou ``"ffprobe"``. Procura primeiro em
    ``bundled_dir`` (cópia empacotada com o app, se existir), depois no
    PATH do sistema. Retorna ``None`` se não encontrar em nenhum dos dois."""
    exe_name = _executable_name(base_name)

    if bundled_dir is not None:
        candidate = bundled_dir / exe_name
        if candidate.is_file():
            return candidate

    found = shutil.which(base_name)
    return Path(found) if found else None


def ffmpeg_available(bundled_dir: Path | None = None) -> bool:
    return find_ffmpeg_binary("ffmpeg", bundled_dir) is not None
