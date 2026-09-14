"""Leitura de metadados de arquivos de áudio via mutagen.

Projetado para nunca lançar exceção para o chamador: bibliotecas de RPG
tendem a ter arquivos baixados de fontes variadas, com tags ausentes,
corrompidas ou em formatos inesperados. Quando a leitura falha, retornamos
valores padrão sensatos (duração 0, título = nome do arquivo) em vez de
interromper o escaneamento.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from mutagen import File as MutagenFile

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AudioMetadata:
    title: str
    artist: str | None
    album: str | None
    duration_seconds: float
    has_embedded_cover: bool


def read_audio_metadata(path: Path) -> AudioMetadata:
    """Lê metadados de um arquivo de áudio, com fallback seguro para o nome do arquivo."""
    fallback_title = path.stem

    try:
        audio = MutagenFile(path, easy=False)
    except Exception:  # noqa: BLE001 - qualquer erro de parsing vira fallback
        logger.warning("Falha ao ler metadados de %s", path, exc_info=True)
        audio = None

    if audio is None:
        return AudioMetadata(
            title=fallback_title,
            artist=None,
            album=None,
            duration_seconds=0.0,
            has_embedded_cover=False,
        )

    duration = 0.0
    if audio.info is not None:
        duration = float(getattr(audio.info, "length", 0.0) or 0.0)

    title, artist, album = _extract_common_tags(audio, fallback_title)
    has_cover = _has_embedded_cover(audio)

    return AudioMetadata(
        title=title or fallback_title,
        artist=artist,
        album=album,
        duration_seconds=duration,
        has_embedded_cover=has_cover,
    )


def _first(values) -> str | None:
    if not values:
        return None
    value = values[0] if isinstance(values, list) else values
    text = str(value).strip()
    return text or None


def _extract_common_tags(audio, fallback_title: str) -> tuple[str, str | None, str | None]:
    tags = audio.tags
    if tags is None:
        return fallback_title, None, None

    # Tags "fáceis" (EasyID3/EasyMP4/Vorbis comment) usam chaves minúsculas comuns.
    for title_key, artist_key, album_key in (
        ("title", "artist", "album"),
        ("TIT2", "TPE1", "TALB"),  # ID3 bruto
        ("\xa9nam", "\xa9ART", "\xa9alb"),  # MP4 bruto
    ):
        if title_key in tags or artist_key in tags or album_key in tags:
            title = _first(tags.get(title_key)) or fallback_title
            artist = _first(tags.get(artist_key))
            album = _first(tags.get(album_key))
            return title, artist, album

    return fallback_title, None, None


def _has_embedded_cover(audio) -> bool:
    try:
        tags = audio.tags
        if tags is None:
            return False
        # ID3 (MP3)
        if hasattr(tags, "getall"):
            return bool(tags.getall("APIC"))
        # MP4
        if "covr" in tags:
            return bool(tags["covr"])
        # FLAC
        if hasattr(audio, "pictures"):
            return bool(audio.pictures)
    except Exception:  # noqa: BLE001
        return False
    return False
