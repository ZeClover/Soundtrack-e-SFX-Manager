# -*- mode: python ; coding: utf-8 -*-
"""Build reproduzível do RPG Audio Studio (Etapa 6, item 65).

Uso:
    pyinstaller RPGAudioStudio.spec --noconfirm

(normalmente chamado por ``BUILD_WINDOWS.bat``, que também prepara o
ambiente, roda os testes e gera ``version_info.txt`` antes disto.)

IMPORTANTE — leitura obrigatória antes de "corrigir" um build que não gerou
um .exe: o PyInstaller NÃO faz cross-compile. Rodando este .spec num Linux
o resultado é um binário ELF do Linux (útil só como build de validação —
ver ``docs/BUILD_VALIDATION_LINUX.md``); o .exe real do Windows só sai
rodando isto numa máquina ou CI Windows de verdade, com um Python/venv
Windows.

Formato de distribuição: one-folder (não one-file). One-file extrai tudo
pra uma pasta temporária a cada execução (mais lento pra abrir, e mais um
lugar pra coisa dar errado com antivírus prendendo o extractor) — one-folder
é mais estável e mais fácil de depurar se algo faltar, e o pedido da Etapa 6
prioriza estabilidade sobre ter um único arquivo.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

SPEC_DIR = Path(SPECPATH)  # rpg-audio-studio/
SUITE_ROOT = SPEC_DIR.parent
SOUNDTRACK_ROOT = SUITE_ROOT / "soundtrack-manager"
SFX_ROOT = SUITE_ROOT / "sfx-manager"
SHARED_ROOT = SUITE_ROOT / "shared"

APP_NAME = "RPG Audio Studio"

# ---------------------------------------------------------------------
# Imports que o PyInstaller não descobre sozinho por análise estática:
# soundtrack_app/sfx_app só existem no sys.path em tempo de execução (via
# app/bootstrap.py) — aqui entram como pathex pra análise enxergar os
# pacotes, e collect_submodules garante que todo submódulo é incluído
# mesmo os que só são importados de forma indireta (factories lazy em
# main.py). yt_dlp tem centenas de extractors carregados dinamicamente —
# pyinstaller-hooks-contrib já traz um hook pra isso, reforçado aqui.
# ---------------------------------------------------------------------
hiddenimports = []
hiddenimports += collect_submodules("soundtrack_app")
hiddenimports += collect_submodules("sfx_app")
hiddenimports += collect_submodules("rpg_audio_shared")
hiddenimports += collect_submodules("yt_dlp")
hiddenimports += collect_submodules("mutagen")
hiddenimports += [
    "PySide6.QtMultimedia",
    "PySide6.QtNetwork",
    "PySide6.QtSvg",
]

# ---------------------------------------------------------------------
# Dados não-Python: ícone (item 10) — o resto do tema é gerado em código
# (rpg_audio_shared/theme.py), sem .qss/.ttf externos a bundlar.
# ---------------------------------------------------------------------
datas = [
    (str(SPEC_DIR / "assets" / "icon.ico"), "assets"),
    (str(SPEC_DIR / "assets" / "icon.png"), "assets"),
]

# ---------------------------------------------------------------------
# FFmpeg/FFprobe empacotados (item 5) — OPCIONAL neste .spec: se
# ``rpg-audio-studio/ffmpeg/ffmpeg.exe`` e ``ffprobe.exe`` existirem na
# hora do build (colocados manualmente ou por BUILD_WINDOWS.bat antes de
# chamar o PyInstaller), entram na distribuição em uma pasta "ffmpeg/" ao
# lado do .exe. Se não existirem, o build segue normalmente e o app usa o
# FFmpeg do PATH do sistema em tempo de execução — ver
# app/config.py:bundled_ffmpeg_dir() e rpg_audio_shared/ffmpeg_locator.py,
# que já fazem esse fallback sozinhos, sem precisar saber se o build atual
# empacotou o FFmpeg ou não.
# ---------------------------------------------------------------------
binaries = []
ffmpeg_source_dir = SPEC_DIR / "ffmpeg"
for exe_name in ("ffmpeg.exe", "ffprobe.exe"):
    exe_path = ffmpeg_source_dir / exe_name
    if exe_path.is_file():
        binaries.append((str(exe_path), "ffmpeg"))

version_info_path = SPEC_DIR / "version_info.txt"
icon_path = SPEC_DIR / "assets" / "icon.ico"

a = Analysis(
    ["main.py"],
    pathex=[str(SPEC_DIR), str(SOUNDTRACK_ROOT), str(SFX_ROOT), str(SHARED_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # sem console (item 8) — main.py já sobrevive a stdout/stderr None (item 6)
    icon=str(icon_path) if icon_path.is_file() else None,
    version=str(version_info_path) if version_info_path.is_file() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name=APP_NAME,
)
