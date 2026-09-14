"""Repositório de histórico de reprodução (item 68 — últimas 50 músicas)."""

from __future__ import annotations

from app.database import Database
from app.models import Track


class HistoryRepository:
    def __init__(self, db: Database):
        self._db = db

    def recent_tracks(self, limit: int = 50) -> list[Track]:
        rows = self._db.query_all(
            """
            SELECT t.*,
                (SELECT GROUP_CONCAT(tg.name, char(31)) FROM track_tags tt
                    JOIN tags tg ON tg.id = tt.tag_id WHERE tt.track_id = t.id) AS tags,
                (SELECT GROUP_CONCAT(c.name, char(31)) FROM track_campaigns tc
                    JOIN campaigns c ON c.id = tc.campaign_id WHERE tc.track_id = t.id) AS campaigns,
                (SELECT COUNT(*) FROM soundtrack_items si WHERE si.track_id = t.id) AS in_soundtrack_count,
                MAX(ph.played_at) AS last_play_at
            FROM play_history ph
            JOIN tracks t ON t.id = ph.track_id
            GROUP BY t.id
            ORDER BY last_play_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [Track.from_row(row) for row in rows]

    def clear(self) -> None:
        self._db.execute("DELETE FROM play_history")
