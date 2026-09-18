"""Configuração central do RPG Audio Studio (identidade, caminhos, cores)."""

from __future__ import annotations

from pathlib import Path

from rpg_audio_shared.app_dirs import app_cache_dir, app_data_dir, app_log_dir

APP_SLUG = "rpg-audio-studio"
APP_NAME = "RPG Audio Studio"

# Cor de destaque do shell (mesma usada pela paleta padrão do tema
# compartilhado). Os módulos mantêm pequenos detalhes próprios pintados
# diretamente no código deles (ex.: cards do SFX em âmbar), então usar um
# único accent aqui para botões/seleção não apaga a identidade de cada um.
ACCENT_COLOR = "#5b8cff"

# Cores só para pequenos detalhes visuais por módulo na barra lateral
# (ponto/indicador ao lado do ícone) — não mudam a paleta global do Qt.
MODULE_ACCENTS = {
    "home": "#5b8cff",
    "soundtrack": "#5b8cff",
    "sfx": "#e0a458",
    "downloader": "#59c98a",
    "history": "#9aa0ad",
    "settings": "#9aa0ad",
}

DATABASE_FILENAME = "studio_settings.db"


def database_path() -> Path:
    """Banco próprio do Studio: só preferências que não pertencem a nenhum
    módulo (pasta padrão de downloads, tema, volumes...). Nunca duplica o
    que já mora nos bancos do Soundtrack Manager / SFX Manager."""
    return app_data_dir(APP_SLUG) / DATABASE_FILENAME


def log_dir() -> Path:
    return app_log_dir(APP_SLUG)


def cache_dir() -> Path:
    return app_cache_dir(APP_SLUG)
