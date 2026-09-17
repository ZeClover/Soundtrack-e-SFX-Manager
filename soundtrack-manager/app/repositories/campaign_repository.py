"""Repositório de campanhas e sua associação com faixas."""

from __future__ import annotations

from app.database import Database
from app.models import Campaign


class CampaignRepository:
    def __init__(self, db: Database):
        self._db = db

    def list_all(self) -> list[Campaign]:
        rows = self._db.query_all("SELECT id, name FROM campaigns ORDER BY name COLLATE NOCASE ASC")
        return [Campaign(id=row["id"], name=row["name"]) for row in rows]

    def get_or_create(self, name: str) -> Campaign:
        name = name.strip()
        row = self._db.query_one("SELECT id, name FROM campaigns WHERE name = ? COLLATE NOCASE", (name,))
        if row:
            return Campaign(id=row["id"], name=row["name"])
        cursor = self._db.execute("INSERT INTO campaigns (name) VALUES (?)", (name,))
        return Campaign(id=cursor.lastrowid, name=name)

    def rename(self, campaign_id: int, name: str) -> None:
        self._db.execute("UPDATE campaigns SET name = ? WHERE id = ?", (name.strip(), campaign_id))

    def delete(self, campaign_id: int) -> None:
        self._db.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))

    def set_campaigns_for_track(self, track_id: int, campaign_names: list[str]) -> None:
        with self._db.transaction() as conn:
            conn.execute("DELETE FROM track_campaigns WHERE track_id = ?", (track_id,))
            for raw_name in campaign_names:
                name = raw_name.strip()
                if not name:
                    continue
                row = conn.execute(
                    "SELECT id FROM campaigns WHERE name = ? COLLATE NOCASE", (name,)
                ).fetchone()
                campaign_id = row["id"] if row else conn.execute(
                    "INSERT INTO campaigns (name) VALUES (?)", (name,)
                ).lastrowid
                conn.execute(
                    "INSERT OR IGNORE INTO track_campaigns (track_id, campaign_id) VALUES (?, ?)",
                    (track_id, campaign_id),
                )
