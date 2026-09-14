"""Localização de diretórios de dados/logs/config por aplicativo.

No Windows, dados de usuário ficam em ``%APPDATA%\\RPG Audio Toolkit\\<app>``.
Em outros sistemas (útil para desenvolvimento/testes em Linux/Mac) cai em
``~/.rpg-audio-toolkit/<app>``. Isso mantém os três apps independentes entre
si (cada um com sua própria subpasta) mas seguindo o mesmo padrão.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .paths import ensure_directory

_SUITE_FOLDER_NAME = "RPG Audio Toolkit"


def suite_data_root() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Roaming"
        return root / _SUITE_FOLDER_NAME
    return Path.home() / f".{_SUITE_FOLDER_NAME.lower().replace(' ', '-')}"


def app_data_dir(app_slug: str) -> Path:
    """Diretório de dados persistentes do app (banco de dados, etc)."""
    return ensure_directory(suite_data_root() / app_slug)


def app_log_dir(app_slug: str) -> Path:
    return ensure_directory(app_data_dir(app_slug) / "logs")


def app_cache_dir(app_slug: str) -> Path:
    return ensure_directory(app_data_dir(app_slug) / "cache")
