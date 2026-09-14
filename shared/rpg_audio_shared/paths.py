"""Utilitários de caminho e sanitização de nomes compatíveis com Windows.

Sempre usa :mod:`pathlib` para lidar corretamente com espaços, acentos,
caracteres Unicode e diferenças entre sistemas operacionais.
"""

from __future__ import annotations

import re
from pathlib import Path

# Caracteres proibidos em nomes de arquivo/pasta no Windows: \ / : * ? " < > |
_INVALID_CHARS_RE = re.compile(r'[\\/:*?"<>|]')
# Nomes reservados no Windows (não podem ser usados como nome de arquivo, com ou sem extensão)
_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
_MAX_COMPONENT_LENGTH = 150  # margem de segurança para o limite de 255 do NTFS


def sanitize_filename(name: str, *, fallback: str = "sem_titulo") -> str:
    """Converte ``name`` em um nome de arquivo/pasta seguro no Windows.

    - Remove caracteres inválidos (``\\ / : * ? " < > |``).
    - Remove espaços e pontos no início/fim (Windows não permite).
    - Evita nomes reservados (CON, PRN, COM1, etc).
    - Limita o tamanho do componente do caminho.
    """
    name = name.strip()
    name = _INVALID_CHARS_RE.sub("_", name)
    # Caracteres de controle
    name = "".join(ch for ch in name if ch.isprintable())
    name = name.strip(" .")

    if not name:
        name = fallback

    if name.upper() in _RESERVED_NAMES:
        name = f"_{name}"

    if len(name) > _MAX_COMPONENT_LENGTH:
        name = name[:_MAX_COMPONENT_LENGTH].rstrip()

    return name or fallback


def unique_path(path: Path) -> Path:
    """Retorna um caminho que não colide com um arquivo existente.

    Se ``path`` já existir, acrescenta " (2)", " (3)", ... antes da extensão,
    preservando a extensão original.
    """
    if not path.exists():
        return path

    stem, suffix, parent = path.stem, path.suffix, path.parent
    counter = 2
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def ensure_directory(path: Path) -> Path:
    """Cria o diretório (e pais) se necessário e retorna o próprio caminho."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def numbered_filename(index: int, title: str, suffix: str, *, width: int = 2) -> str:
    """Monta um nome de arquivo numerado, ex.: ``01 - Nome.mp3``."""
    safe_title = sanitize_filename(title)
    return f"{index:0{width}d} - {safe_title}{suffix}"
