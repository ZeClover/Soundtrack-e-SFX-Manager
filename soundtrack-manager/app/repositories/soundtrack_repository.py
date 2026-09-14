"""Repositório de soundtracks (projetos) e seus itens.

Seções de soundtrack (item 28 da especificação) já têm suporte no schema
(``soundtrack_sections`` / ``soundtrack_items.section_id``) para não exigir
migração de banco no futuro, mas a manipulação de seções pela UI é um
recurso da experiência avançada (etapa 3) e não faz parte deste repositório
ainda — os itens são tratados como uma lista simples e ordenada.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.database import Database
from app.models import Soundtrack, SoundtrackItem, Track


class SoundtrackRepository:
    def __init__(self, db: Database):
        self._db = db

    # ------------------------------------------------------------------
    # Soundtracks
    # ------------------------------------------------------------------

    def list_all(self) -> list[Soundtrack]:
        rows = self._db.query_all(
            """
            SELECT s.*, COUNT(si.id) AS track_count
            FROM soundtracks s
            LEFT JOIN soundtrack_items si ON si.soundtrack_id = s.id
            GROUP BY s.id
            ORDER BY s.updated_at DESC
            """
        )
        return [Soundtrack.from_row(row) for row in rows]

    def get(self, soundtrack_id: int) -> Soundtrack | None:
        row = self._db.query_one(
            """
            SELECT s.*, COUNT(si.id) AS track_count
            FROM soundtracks s
            LEFT JOIN soundtrack_items si ON si.soundtrack_id = s.id
            WHERE s.id = ?
            GROUP BY s.id
            """,
            (soundtrack_id,),
        )
        return Soundtrack.from_row(row) if row else None

    def create(self, name: str, campaign_id: int | None = None) -> Soundtrack:
        now = _now_iso()
        cursor = self._db.execute(
            "INSERT INTO soundtracks (name, campaign_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (name.strip(), campaign_id, now, now),
        )
        return Soundtrack(id=cursor.lastrowid, name=name.strip(), campaign_id=campaign_id,
                           created_at=now, updated_at=now, track_count=0)

    def rename(self, soundtrack_id: int, name: str) -> None:
        self._db.execute(
            "UPDATE soundtracks SET name = ?, updated_at = ? WHERE id = ?",
            (name.strip(), _now_iso(), soundtrack_id),
        )

    def delete(self, soundtrack_id: int) -> None:
        self._db.execute("DELETE FROM soundtracks WHERE id = ?", (soundtrack_id,))

    def touch(self, soundtrack_id: int) -> None:
        self._db.execute(
            "UPDATE soundtracks SET updated_at = ? WHERE id = ?", (_now_iso(), soundtrack_id)
        )

    # ------------------------------------------------------------------
    # Itens
    # ------------------------------------------------------------------

    def get_items(self, soundtrack_id: int) -> list[SoundtrackItem]:
        rows = self._db.query_all(
            """
            SELECT si.id, si.soundtrack_id, si.section_id, si.track_id, si.position,
                t.*,
                (SELECT GROUP_CONCAT(tg.name, char(31)) FROM track_tags tt
                    JOIN tags tg ON tg.id = tt.tag_id WHERE tt.track_id = t.id) AS tags,
                (SELECT GROUP_CONCAT(c.name, char(31)) FROM track_campaigns tc
                    JOIN campaigns c ON c.id = tc.campaign_id WHERE tc.track_id = t.id) AS campaigns,
                (SELECT COUNT(*) FROM soundtrack_items si2 WHERE si2.track_id = t.id) AS in_soundtrack_count
            FROM soundtrack_items si
            JOIN tracks t ON t.id = si.track_id
            WHERE si.soundtrack_id = ?
            ORDER BY si.position ASC
            """,
            (soundtrack_id,),
        )
        items = []
        for row in rows:
            track = Track.from_row(row)
            items.append(
                SoundtrackItem(
                    id=row["id"],
                    soundtrack_id=row["soundtrack_id"],
                    section_id=row["section_id"],
                    track_id=row["track_id"],
                    position=row["position"],
                    track=track,
                )
            )
        return items

    def has_track(self, soundtrack_id: int, track_id: int) -> bool:
        row = self._db.query_one(
            "SELECT 1 FROM soundtrack_items WHERE soundtrack_id = ? AND track_id = ? LIMIT 1",
            (soundtrack_id, track_id),
        )
        return row is not None

    def add_track(self, soundtrack_id: int, track_id: int) -> SoundtrackItem:
        row = self._db.query_one(
            "SELECT COALESCE(MAX(position), 0) AS max_pos FROM soundtrack_items WHERE soundtrack_id = ?",
            (soundtrack_id,),
        )
        next_position = (row["max_pos"] if row else 0) + 1
        cursor = self._db.execute(
            "INSERT INTO soundtrack_items (soundtrack_id, section_id, track_id, position) "
            "VALUES (?, NULL, ?, ?)",
            (soundtrack_id, track_id, next_position),
        )
        self.touch(soundtrack_id)
        return SoundtrackItem(
            id=cursor.lastrowid, soundtrack_id=soundtrack_id, section_id=None,
            track_id=track_id, position=next_position,
        )

    def remove_item(self, item_id: int, soundtrack_id: int) -> None:
        self._db.execute("DELETE FROM soundtrack_items WHERE id = ?", (item_id,))
        self.touch(soundtrack_id)

    def reorder(self, soundtrack_id: int, ordered_item_ids: list[int]) -> None:
        """Reaplica a posição (1..N) de acordo com a ordem informada (drag&drop, mover)."""
        with self._db.transaction() as conn:
            for position, item_id in enumerate(ordered_item_ids, start=1):
                conn.execute(
                    "UPDATE soundtrack_items SET position = ? WHERE id = ? AND soundtrack_id = ?",
                    (position, item_id, soundtrack_id),
                )
            conn.execute(
                "UPDATE soundtracks SET updated_at = ? WHERE id = ?", (_now_iso(), soundtrack_id)
            )

    def move_item(self, soundtrack_id: int, item_id: int, direction: int) -> None:
        """Move um item uma posição para cima (direction=-1) ou para baixo (direction=+1)."""
        items = self._db.query_all(
            "SELECT id, position FROM soundtrack_items WHERE soundtrack_id = ? ORDER BY position ASC",
            (soundtrack_id,),
        )
        ids = [row["id"] for row in items]
        if item_id not in ids:
            return
        index = ids.index(item_id)
        new_index = index + direction
        if new_index < 0 or new_index >= len(ids):
            return
        ids[index], ids[new_index] = ids[new_index], ids[index]
        self.reorder(soundtrack_id, ids)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
