"""Imprime só APP_VERSION (app/version.py) em stdout.

Usado pelo BUILD_WINDOWS.bat pra nomear o ZIP final via FOR /F, sem
depender de um "python -c '...'" embutido dentro de um FOR /F — as aspas e
os parênteses do próprio código Python (``print(APP_VERSION)``,
``sys.path.insert(0, '.')``) colidem com a sintaxe de parsing do FOR /F no
cmd.exe, e a versão capturada saía vazia; o release acabava se chamando
"RPG-Audio-Studio-v-Windows.zip" em vez de "...-v1.0.0-...".

Uso:
    python scripts/print_version.py
"""

from __future__ import annotations

import sys
from pathlib import Path

STUDIO_ROOT = Path(__file__).resolve().parent.parent
if str(STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDIO_ROOT))

from app.version import APP_VERSION

if __name__ == "__main__":
    print(APP_VERSION)
