"""Repositório de tags livres e sua associação com efeitos sonoros."""

from __future__ import annotations

from sfx_app.database import Database
from sfx_app.models import Tag


class TagRepository:
    def __init__(self, db: Database):
        self._db = db

    def list_all(self) -> list[Tag]:
        rows = self._db.query_all(
            """
            SELECT tg.id, tg.name, COUNT(tt.track_id) AS usage_count
            FROM sfx_tags tg
            LEFT JOIN sfx_track_tags tt ON tt.tag_id = tg.id
            GROUP BY tg.id
            ORDER BY tg.name COLLATE NOCASE ASC
            """
        )
        return [Tag(id=row["id"], name=row["name"]) for row in rows]

    def get_or_create(self, name: str) -> Tag:
        name = name.strip()
        row = self._db.query_one("SELECT id, name FROM sfx_tags WHERE name = ? COLLATE NOCASE", (name,))
        if row:
            return Tag(id=row["id"], name=row["name"])
        cursor = self._db.execute("INSERT INTO sfx_tags (name) VALUES (?)", (name,))
        return Tag(id=cursor.lastrowid, name=name)

    def set_tags_for_track(self, track_id: int, tag_names: list[str]) -> None:
        """Substitui o conjunto de tags de um efeito pelo informado (cria as que faltam)."""
        with self._db.transaction() as conn:
            conn.execute("DELETE FROM sfx_track_tags WHERE track_id = ?", (track_id,))
            for raw_name in tag_names:
                name = raw_name.strip()
                if not name:
                    continue
                row = conn.execute(
                    "SELECT id FROM sfx_tags WHERE name = ? COLLATE NOCASE", (name,)
                ).fetchone()
                tag_id = row["id"] if row else conn.execute(
                    "INSERT INTO sfx_tags (name) VALUES (?)", (name,)
                ).lastrowid
                conn.execute(
                    "INSERT OR IGNORE INTO sfx_track_tags (track_id, tag_id) VALUES (?, ?)",
                    (track_id, tag_id),
                )

    def delete_unused(self) -> int:
        cursor = self._db.execute(
            "DELETE FROM sfx_tags WHERE id NOT IN (SELECT DISTINCT tag_id FROM sfx_track_tags)"
        )
        return cursor.rowcount
