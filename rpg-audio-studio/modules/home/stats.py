"""Coleta estatísticas para a Home sem precisar montar as telas pesadas dos
módulos (item 38: lazy initialization) — abre uma conexão curta e direta
com cada banco só para contar linhas, e fecha em seguida."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from app.bootstrap import ensure_sibling_modules_importable

logger = logging.getLogger(__name__)


@dataclass
class StudioStats:
    music_count: int = 0
    soundtrack_count: int = 0
    sfx_count: int = 0
    pack_count: int = 0
    music_available: bool = True
    sfx_available: bool = True


def collect_stats(soundtrack_db_path: Path | None = None, sfx_db_path: Path | None = None) -> StudioStats:
    """Os dois parâmetros só existem para os testes poderem apontar pra um
    banco isolado em ``tmp_path`` (mesmo padrão de ``db_path`` usado em todo
    o resto da suíte) — sem eles, cada módulo usa seu caminho real de
    sempre, exatamente o mesmo que o módulo já usaria se estivesse aberto."""
    ensure_sibling_modules_importable()
    stats = StudioStats()

    try:
        from soundtrack_app.config import database_path as default_soundtrack_db_path
        from soundtrack_app.database import Database as SoundtrackDatabase
        from soundtrack_app.repositories import SoundtrackRepository, TrackRepository

        db = SoundtrackDatabase(soundtrack_db_path or default_soundtrack_db_path())
        try:
            stats.music_count = TrackRepository(db).stats()["total"]
            stats.soundtrack_count = len(SoundtrackRepository(db).list_all())
        finally:
            db.close()
    except Exception:
        logger.exception("Falha ao coletar estatísticas do módulo Música")
        stats.music_available = False

    try:
        from sfx_app.config import database_path as default_sfx_db_path
        from sfx_app.database import Database as SfxDatabase
        from sfx_app.repositories import PackRepository, SfxTrackRepository

        db = SfxDatabase(sfx_db_path or default_sfx_db_path())
        try:
            stats.sfx_count = SfxTrackRepository(db).stats()["total"]
            stats.pack_count = len(PackRepository(db).list_all())
        finally:
            db.close()
    except Exception:
        logger.exception("Falha ao coletar estatísticas do módulo SFX")
        stats.sfx_available = False

    return stats
