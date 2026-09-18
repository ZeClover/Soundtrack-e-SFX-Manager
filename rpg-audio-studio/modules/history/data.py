"""Coleta os três históricos (música, SFX, downloads) sem precisar montar
as telas pesadas dos módulos — mesma ideia do ``modules.home.stats``."""

from __future__ import annotations

import logging
from pathlib import Path

from app.bootstrap import ensure_sibling_modules_importable

logger = logging.getLogger(__name__)


def collect_recent_music_titles(limit: int = 20, db_path: Path | None = None) -> list[str]:
    """``db_path`` só existe para os testes apontarem pra um banco isolado
    em ``tmp_path`` — em produção fica ``None`` e usa o caminho real."""
    ensure_sibling_modules_importable()
    try:
        from soundtrack_app.config import database_path
        from soundtrack_app.database import Database
        from soundtrack_app.repositories import HistoryRepository

        db = Database(db_path or database_path())
        try:
            return [track.title for track in HistoryRepository(db).recent_tracks(limit=limit)]
        finally:
            db.close()
    except Exception:
        logger.exception("Falha ao coletar histórico de músicas")
        return []


def collect_recent_sfx_titles(limit: int = 20, db_path: Path | None = None) -> list[str]:
    ensure_sibling_modules_importable()
    try:
        from sfx_app.config import database_path
        from sfx_app.database import Database
        from sfx_app.repositories import HistoryRepository

        db = Database(db_path or database_path())
        try:
            return [track.title for track in HistoryRepository(db).recent_tracks(limit=limit)]
        finally:
            db.close()
    except Exception:
        logger.exception("Falha ao coletar histórico de SFX")
        return []


def collect_recent_download_titles(limit: int = 20) -> list[str]:
    try:
        from modules.downloader.services.recent_downloads import list_recent_titles

        return list_recent_titles(limit=limit)
    except Exception:
        logger.exception("Falha ao coletar histórico de downloads")
        return []
