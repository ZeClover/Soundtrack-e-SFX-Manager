"""Caminhos próprios do módulo Downloader dentro dos dados do Studio."""

from __future__ import annotations

from pathlib import Path

from rpg_audio_shared.app_dirs import app_data_dir
from rpg_audio_shared.paths import ensure_directory

APP_SLUG = "rpg-audio-studio"


def downloader_data_dir() -> Path:
    return ensure_directory(app_data_dir(APP_SLUG) / "downloader")


def download_archive_path() -> Path:
    """Um ID de vídeo por linha — usado para nunca baixar a mesma música
    duas vezes entre execuções diferentes do Downloader."""
    return downloader_data_dir() / "download_archive.txt"
