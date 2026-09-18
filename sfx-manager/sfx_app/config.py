"""Configuração central do RPG SFX Manager (caminhos, constantes)."""

from __future__ import annotations

from pathlib import Path

from rpg_audio_shared.app_dirs import app_cache_dir, app_data_dir, app_log_dir

APP_SLUG = "sfx-manager"
APP_NAME = "RPG SFX Manager"
# Cor de destaque discreta e diferente do Soundtrack Manager, para os dois
# apps não parecerem visualmente idênticos mesmo compartilhando o tema base.
ACCENT_COLOR = "#e0a458"

DATABASE_FILENAME = "sfx_manager.db"


def database_path() -> Path:
    return app_data_dir(APP_SLUG) / DATABASE_FILENAME


def log_dir() -> Path:
    return app_log_dir(APP_SLUG)


def cache_dir() -> Path:
    return app_cache_dir(APP_SLUG)


# Categorias sugeridas (item 40) — não fixas, o usuário pode criar outras.
SUGGESTED_CATEGORIES: tuple[str, ...] = (
    "Armas",
    "Espadas",
    "Flechas",
    "Armas de fogo",
    "Impactos",
    "Magia",
    "Fogo",
    "Gelo",
    "Eletricidade",
    "Explosões",
    "Monstros",
    "Animais",
    "Humanos",
    "Passos",
    "Portas",
    "Objetos",
    "Natureza",
    "Clima",
    "Ambiente",
    "Cidade",
    "Dungeon",
    "Interface",
    "Terror",
)

# Teclas simples permitidas para hotkeys (item 44) — dígitos e letras, sem
# modificadores, para manter o sistema simples e sem conflitos.
ALLOWED_HOTKEYS: tuple[str, ...] = tuple("1234567890") + tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
