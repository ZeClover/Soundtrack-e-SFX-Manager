"""Regressão: BUILD_WINDOWS.bat captura a versão via
``for /f ... in ('%PY% scripts\\print_version.py') do ...`` — o script
precisa imprimir SÓ a versão, uma linha limpa, sem mais nada, senão o ZIP
final acaba nomeado incorretamente (foi exatamente isso que aconteceu com
a abordagem anterior, um "python -c" embutido direto no FOR /F: o
resultado saía vazio e o release se chamava
"RPG-Audio-Studio-v-Windows.zip" em vez de "...-v1.0.0-...")."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from app.version import APP_VERSION

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "print_version.py"


def test_prints_exactly_the_app_version_and_nothing_else():
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)], capture_output=True, text=True, check=True,
    )
    assert result.stdout == f"{APP_VERSION}\n"
    assert result.stderr == ""
