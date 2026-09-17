"""Repositório de packs de SFX (item 45) e seus itens.

Mais simples que o de soundtracks: packs de SFX não têm seções — só uma
lista ordenada de efeitos.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.database import Database
from app.models import SfxPack, SfxPackItem, SfxTrack


class PackRepository:
    def __init__(self, db: Database):
        self._db = db

    def list_all(self) -> list[SfxPack]:
        rows = self._db.query_all(
            """
            SELECT p.*, COUNT(pi.id) AS track_count
            FROM sfx_packs p
            LEFT JOIN sfx_pack_items pi ON pi.pack_id = p.id
            GROUP BY p.id
            ORDER BY p.updated_at DESC
            """
        )
        return [SfxPack.from_row(row) for row in rows]

    def get(self, pack_id: int) -> SfxPack | None:
        row = self._db.query_one(
            """
            SELECT p.*, COUNT(pi.id) AS track_count
            FROM sfx_packs p
            LEFT JOIN sfx_pack_items pi ON pi.pack_id = p.id
            WHERE p.id = ?
            GROUP BY p.id
            """,
            (pack_id,),
        )
        return SfxPack.from_row(row) if row else None

    def create(self, name: str) -> SfxPack:
        now = _now_iso()
        cursor = self._db.execute(
            "INSERT INTO sfx_packs (name, created_at, updated_at) VALUES (?, ?, ?)",
            (name.strip(), now, now),
        )
        return SfxPack(id=cursor.lastrowid, name=name.strip(), created_at=now, updated_at=now, track_count=0)

    def rename(self, pack_id: int, name: str) -> None:
        self._db.execute(
            "UPDATE sfx_packs SET name = ?, updated_at = ? WHERE id = ?", (name.strip(), _now_iso(), pack_id)
        )

    def delete(self, pack_id: int) -> None:
        self._db.execute("DELETE FROM sfx_packs WHERE id = ?", (pack_id,))

    def touch(self, pack_id: int) -> None:
        self._db.execute("UPDATE sfx_packs SET updated_at = ? WHERE id = ?", (_now_iso(), pack_id))

    def get_items(self, pack_id: int) -> list[SfxPackItem]:
        rows = self._db.query_all(
            """
            SELECT pi.id AS item_id, pi.pack_id, pi.track_id, pi.position,
                t.*,
                cat.name AS category_name,
                (SELECT GROUP_CONCAT(tg.name, char(31)) FROM sfx_track_tags tt
                    JOIN sfx_tags tg ON tg.id = tt.tag_id WHERE tt.track_id = t.id) AS tags,
                (SELECT hk.key FROM sfx_hotkeys hk WHERE hk.track_id = t.id) AS hotkey,
                (SELECT COUNT(*) FROM sfx_pack_items pi2 WHERE pi2.track_id = t.id) AS in_pack_count
            FROM sfx_pack_items pi
            JOIN sfx_tracks t ON t.id = pi.track_id
            LEFT JOIN sfx_categories cat ON cat.id = t.category_id
            WHERE pi.pack_id = ?
            ORDER BY pi.position ASC
            """,
            (pack_id,),
        )
        items = []
        for row in rows:
            track = SfxTrack.from_row(row)
            items.append(SfxPackItem(id=row["item_id"], pack_id=row["pack_id"],
                                      track_id=row["track_id"], position=row["position"], track=track))
        return items

    def has_track(self, pack_id: int, track_id: int) -> bool:
        row = self._db.query_one(
            "SELECT 1 FROM sfx_pack_items WHERE pack_id = ? AND track_id = ? LIMIT 1",
            (pack_id, track_id),
        )
        return row is not None

    def add_track(self, pack_id: int, track_id: int) -> SfxPackItem:
        row = self._db.query_one(
            "SELECT COALESCE(MAX(position), 0) AS max_pos FROM sfx_pack_items WHERE pack_id = ?",
            (pack_id,),
        )
        next_position = (row["max_pos"] if row else 0) + 1
        cursor = self._db.execute(
            "INSERT INTO sfx_pack_items (pack_id, track_id, position) VALUES (?, ?, ?)",
            (pack_id, track_id, next_position),
        )
        self.touch(pack_id)
        return SfxPackItem(id=cursor.lastrowid, pack_id=pack_id, track_id=track_id, position=next_position)

    def remove_item(self, item_id: int, pack_id: int) -> None:
        self._db.execute("DELETE FROM sfx_pack_items WHERE id = ?", (item_id,))
        self.touch(pack_id)

    def reorder(self, pack_id: int, ordered_item_ids: list[int]) -> None:
        with self._db.transaction() as conn:
            for position, item_id in enumerate(ordered_item_ids, start=1):
                conn.execute(
                    "UPDATE sfx_pack_items SET position = ? WHERE id = ? AND pack_id = ?",
                    (position, item_id, pack_id),
                )
            conn.execute("UPDATE sfx_packs SET updated_at = ? WHERE id = ?", (_now_iso(), pack_id))

    def move_item(self, pack_id: int, item_id: int, direction: int) -> None:
        items = self._db.query_all(
            "SELECT id FROM sfx_pack_items WHERE pack_id = ? ORDER BY position ASC", (pack_id,)
        )
        ids = [row["id"] for row in items]
        if item_id not in ids:
            return
        index = ids.index(item_id)
        new_index = index + direction
        if new_index < 0 or new_index >= len(ids):
            return
        ids[index], ids[new_index] = ids[new_index], ids[index]
        self.reorder(pack_id, ids)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
