"""Formatação de velocidade/ETA para a UI de progresso do Downloader."""

from __future__ import annotations


def format_speed(bytes_per_second: float | None) -> str:
    if not bytes_per_second or bytes_per_second <= 0:
        return ""
    value = float(bytes_per_second)
    for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
        if value < 1024:
            return f"{value:.0f} {unit}" if unit == "B/s" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB/s"


def format_eta(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return ""
    total = int(seconds)
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
