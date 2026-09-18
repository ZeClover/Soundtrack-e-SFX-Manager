"""Conecta o RPG Audio Studio aos módulos Soundtrack e SFX sem duplicar
código nem reescrevê-los.

``soundtrack-manager/`` e ``sfx-manager/`` continuam sendo apps completos e
independentes (cada um roda sozinho com ``python main.py``), cada um com um
pacote Python próprio (``soundtrack_app`` e ``sfx_app`` — renomeados nesta
etapa a partir de ``app`` justamente para não colidir um com o outro dentro
do mesmo processo). O Studio só precisa colocar as duas pastas no
``sys.path`` para poder importar ``soundtrack_app.*`` e ``sfx_app.*``
diretamente, reaproveitando toda a lógica/UI/testes já existentes.
"""

from __future__ import annotations

import sys
from pathlib import Path

STUDIO_ROOT = Path(__file__).resolve().parent.parent
SUITE_ROOT = STUDIO_ROOT.parent

SOUNDTRACK_MANAGER_ROOT = SUITE_ROOT / "soundtrack-manager"
SFX_MANAGER_ROOT = SUITE_ROOT / "sfx-manager"

_DONE = False


def ensure_sibling_modules_importable() -> None:
    """Idempotente: pode ser chamada várias vezes (main.py, conftest.py de
    testes, etc.) sem duplicar entradas no sys.path."""
    global _DONE
    if _DONE:
        return

    for root in (SOUNDTRACK_MANAGER_ROOT, SFX_MANAGER_ROOT):
        root_str = str(root)
        if root.is_dir() and root_str not in sys.path:
            sys.path.insert(0, root_str)

    _DONE = True
