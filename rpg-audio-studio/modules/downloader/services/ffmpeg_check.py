"""Detecção do FFmpeg (item 14, revisado na Etapa 6/item 5) — necessário só
para converter para MP3. Procura primeiro a cópia empacotada com o Studio,
só cai pro PATH do sistema como alternativa."""

from __future__ import annotations

from rpg_audio_shared.ffmpeg_locator import ffmpeg_available as _locate_ffmpeg

from app.config import bundled_ffmpeg_dir


def ffmpeg_available() -> bool:
    return _locate_ffmpeg(bundled_dir=bundled_ffmpeg_dir())
