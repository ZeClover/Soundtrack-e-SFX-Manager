"""Lista simples dos últimos downloads concluídos, usada pela Home e pelo
Histórico unificado do Studio (não é um banco de dados — só um JSON
pequeno, guardando só título/data, nunca o arquivo de áudio em si)."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from modules.downloader.config import downloader_data_dir

logger = logging.getLogger(__name__)

_MAX_ENTRIES = 30


@dataclass
class RecentDownloadEntry:
    title: str
    downloaded_at: str


def recent_downloads_path() -> Path:
    return downloader_data_dir() / "recent_downloads.json"


def _load(path: Path) -> list[RecentDownloadEntry]:
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [RecentDownloadEntry(**item) for item in raw]
    except Exception:
        logger.warning("Falha ao ler recent_downloads.json — ignorando conteúdo corrompido", exc_info=True)
        return []


def record_downloads(titles: list[str], path: Path | None = None) -> None:
    if not titles:
        return
    target = path or recent_downloads_path()
    entries = _load(target)
    now = datetime.now(timezone.utc).isoformat()
    entries = [RecentDownloadEntry(title=title, downloaded_at=now) for title in titles] + entries
    entries = entries[:_MAX_ENTRIES]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps([asdict(e) for e in entries], ensure_ascii=False, indent=2), encoding="utf-8")


def list_recent_titles(path: Path | None = None, limit: int = 5) -> list[str]:
    target = path or recent_downloads_path()
    return [entry.title for entry in _load(target)[:limit]]
