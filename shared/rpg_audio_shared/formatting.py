"""Formatação de valores exibidos na UI (duração, tamanho de arquivo)."""

from __future__ import annotations


def format_duration(seconds: float) -> str:
    """Formata segundos como ``mm:ss`` (ou ``h:mm:ss`` quando >= 1 hora)."""
    seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_file_size(num_bytes: int) -> str:
    """Formata bytes em unidade legível (KB, MB, GB)."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
