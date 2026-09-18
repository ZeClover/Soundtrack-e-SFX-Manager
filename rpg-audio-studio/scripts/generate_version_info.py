"""Gera ``version_info.txt`` (metadados do .exe no Windows: Product Name,
File Description, Company, Version — item 11 da Etapa 6) a partir de
``app/version.py``, a fonte única de verdade da versão.

Chamado pelo ``BUILD_WINDOWS.bat`` antes do PyInstaller. Também pode ser
rodado manualmente:

    python scripts/generate_version_info.py
"""

from __future__ import annotations

import sys
from pathlib import Path

STUDIO_ROOT = Path(__file__).resolve().parent.parent
if str(STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDIO_ROOT))

from app.version import APP_AUTHOR, APP_DESCRIPTION, APP_DISPLAY_NAME, APP_VERSION

OUTPUT_PATH = STUDIO_ROOT / "version_info.txt"


def _file_version_tuple(version: str) -> tuple[int, int, int, int]:
    """Windows exige exatamente 4 números (major, minor, patch, build) —
    completa com 0 quando ``version.py`` só tem 3 (ex.: "1.0.0")."""
    parts = [int(p) for p in version.split(".")]
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])  # type: ignore[return-value]


def generate() -> str:
    file_version = _file_version_tuple(APP_VERSION)
    dotted = ".".join(str(p) for p in file_version)

    content = f'''# UTF-8
#
# Gerado automaticamente por scripts/generate_version_info.py — não edite
# à mão, edite app/version.py e rode o script de novo.
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={file_version!r},
    prodvers={file_version!r},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'{APP_AUTHOR}'),
        StringStruct(u'FileDescription', u'{APP_DISPLAY_NAME} — {APP_DESCRIPTION}'),
        StringStruct(u'FileVersion', u'{dotted}'),
        StringStruct(u'InternalName', u'RPGAudioStudio'),
        StringStruct(u'LegalCopyright', u''),
        StringStruct(u'OriginalFilename', u'RPG Audio Studio.exe'),
        StringStruct(u'ProductName', u'{APP_DISPLAY_NAME}'),
        StringStruct(u'ProductVersion', u'{dotted}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''
    OUTPUT_PATH.write_text(content, encoding="utf-8")
    return str(OUTPUT_PATH)


if __name__ == "__main__":
    path = generate()
    print(f"Gerado: {path}")
