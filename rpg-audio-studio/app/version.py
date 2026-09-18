"""Fonte única de verdade da versão e dos metadados do RPG Audio Studio
(item 12) — usado pela Home/Sobre e pelo build (.spec do PyInstaller e
metadados do executável no Windows)."""

from __future__ import annotations

APP_VERSION = "1.0.0"
APP_DISPLAY_NAME = "RPG Audio Studio"
APP_DESCRIPTION = (
    "Baixe músicas, organize soundtracks e efeitos sonoros de campanhas de RPG — tudo num só programa."
)
# Sem empresa/autor definido — usa o nome do próprio projeto, como pedido.
APP_AUTHOR = "RPG Audio Studio"
APP_MODULES = ("Soundtrack Manager", "SFX Manager", "Downloader")
