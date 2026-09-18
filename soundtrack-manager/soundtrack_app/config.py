"""Configuração central do RPG Soundtrack Manager (caminhos, constantes)."""

from __future__ import annotations

from pathlib import Path

from rpg_audio_shared.app_dirs import app_cache_dir, app_data_dir, app_log_dir

APP_SLUG = "soundtrack-manager"
APP_NAME = "RPG Soundtrack Manager"
ACCENT_COLOR = "#5b8cff"

DATABASE_FILENAME = "soundtrack_manager.db"


def database_path() -> Path:
    return app_data_dir(APP_SLUG) / DATABASE_FILENAME


def log_dir() -> Path:
    return app_log_dir(APP_SLUG)


def cache_dir() -> Path:
    return app_cache_dir(APP_SLUG)


# Categorias sugeridas (não fixas — usuário pode criar as suas via tags/campanhas)
SUGGESTED_CATEGORIES: tuple[str, ...] = (
    "Tema Principal",
    "Exploração",
    "Combate",
    "Boss",
    "Tensão",
    "Mistério",
    "Terror",
    "Drama",
    "Triste",
    "Vitória",
    "Cidade",
    "Dungeon",
    "Ambiente",
    "Viagem",
    "Vilão",
    "Evento Especial",
)

RECENT_HISTORY_LIMIT = 50
