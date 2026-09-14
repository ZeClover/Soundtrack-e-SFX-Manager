"""Formatos de áudio suportados pela suíte.

Mantido como um conjunto simples para facilitar a adição de novos formatos
no futuro sem precisar alterar o código do scanner.
"""

from __future__ import annotations

SUPPORTED_AUDIO_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".mp3",
        ".wav",
        ".flac",
        ".ogg",
        ".m4a",
        ".opus",
    }
)


def is_supported_audio_file(path) -> bool:
    """Retorna True se a extensão do arquivo é um formato de áudio suportado."""
    suffix = getattr(path, "suffix", None)
    if suffix is None:
        suffix = str(path).rsplit(".", 1)[-1]
        suffix = f".{suffix}" if suffix else ""
    return suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS
