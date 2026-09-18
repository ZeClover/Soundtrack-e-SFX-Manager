"""Configuração central do RPG Audio Studio (identidade, caminhos, cores)."""

from __future__ import annotations

from pathlib import Path

from rpg_audio_shared.app_dirs import app_cache_dir, app_data_dir, app_log_dir
from rpg_audio_shared.runtime import frozen_base_dir

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


# ----------------------------------------------------------------------
# Recursos do PRÓPRIO APP (ícone, FFmpeg empacotado, assets) — item 8.
#
# Nunca confundir com os diretórios acima: aqueles são dados do usuário
# (sempre em %APPDATA%, frozen ou não); estes são arquivos que vêm junto
# com o programa, e mudam de lugar dependendo se está rodando do
# código-fonte (desenvolvimento) ou de dentro do executável empacotado.
# ----------------------------------------------------------------------

_DEV_APP_ROOT = Path(__file__).resolve().parent.parent  # rpg-audio-studio/


def app_base_dir() -> Path:
    """Raiz para resolver recursos empacotados com o app. Em modo frozen,
    é a pasta do executável (ou a pasta temporária extraída, no one-file);
    em desenvolvimento, é a raiz do próprio ``rpg-audio-studio/``."""
    return frozen_base_dir() or _DEV_APP_ROOT


def resource_path(*parts: str) -> Path:
    """Resolve o caminho de um recurso empacotado, ex.:
    ``resource_path("assets", "icon.ico")`` ou
    ``resource_path("ffmpeg", "ffmpeg.exe")``."""
    return app_base_dir().joinpath(*parts)


def bundled_ffmpeg_dir() -> Path:
    """Pasta onde uma cópia do FFmpeg/FFprobe pode vir empacotada junto do
    Studio (ver item 5 da Etapa 6 e ``BUILD_WINDOWS.bat``). Só existe de
    fato se alguém tiver colocado os binários lá antes do build — quando
    não existe, tudo cai de volta pro PATH do sistema normalmente."""
    return resource_path("ffmpeg")


def icon_path() -> Path:
    return resource_path("assets", "icon.ico")
