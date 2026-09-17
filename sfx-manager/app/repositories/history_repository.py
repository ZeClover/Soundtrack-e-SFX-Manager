"""Repositório de histórico de reprodução de SFX."""

from __future__ import annotations

from app.database import Database
from app.models import SfxTrack


class HistoryRepository:
    def __init__(self, db: Database):
        self._db = db

    def recent_tracks(self, limit: int = 50) -> list[SfxTrack]:
        rows = self._db.query_all(
            """
            SELECT t.*,
                cat.name AS category_name,
                (SELECT GROUP_CONCAT(tg.name, char(31)) FROM sfx_track_tags tt
                    JOIN sfx_tags tg ON tg.id = tt.tag_id WHERE tt.track_id = t.id) AS tags,
                (SELECT hk.key FROM sfx_hotkeys hk WHERE hk.track_id = t.id) AS hotkey,
                (SELECT COUNT(*) FROM sfx_pack_items pi WHERE pi.track_id = t.id) AS in_pack_count,
                MAX(ph.played_at) AS last_play_at
            FROM sfx_play_history ph
            JOIN sfx_tracks t ON t.id = ph.track_id
            LEFT JOIN sfx_categories cat ON cat.id = t.category_id
            GROUP BY t.id
            ORDER BY last_play_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [SfxTrack.from_row(row) for row in rows]
