"""Repositório de tags livres e sua associação com faixas."""

from __future__ import annotations

from soundtrack_app.database import Database
from soundtrack_app.models import Tag


class TagRepository:
    def __init__(self, db: Database):
        self._db = db

    def list_all(self) -> list[Tag]:
        rows = self._db.query_all(
            """
            SELECT tg.id, tg.name, COUNT(tt.track_id) AS usage_count
            FROM tags tg
            LEFT JOIN track_tags tt ON tt.tag_id = tg.id
            GROUP BY tg.id
            ORDER BY tg.name COLLATE NOCASE ASC
            """
        )
        return [Tag(id=row["id"], name=row["name"], usage_count=row["usage_count"]) for row in rows]

    def get_or_create(self, name: str) -> Tag:
        name = name.strip()
        row = self._db.query_one("SELECT id, name FROM tags WHERE name = ? COLLATE NOCASE", (name,))
        if row:
            return Tag(id=row["id"], name=row["name"])
        cursor = self._db.execute("INSERT INTO tags (name) VALUES (?)", (name,))
        return Tag(id=cursor.lastrowid, name=name)

    def tags_for_track(self, track_id: int) -> list[Tag]:
        rows = self._db.query_all(
            """
            SELECT tg.id, tg.name FROM tags tg
            JOIN track_tags tt ON tt.tag_id = tg.id
            WHERE tt.track_id = ?
            ORDER BY tg.name COLLATE NOCASE ASC
            """,
            (track_id,),
        )
        return [Tag(id=row["id"], name=row["name"]) for row in rows]

    def set_tags_for_track(self, track_id: int, tag_names: list[str]) -> None:
        """Substitui o conjunto de tags de uma faixa pelo informado (cria as que faltam)."""
        with self._db.transaction() as conn:
            conn.execute("DELETE FROM track_tags WHERE track_id = ?", (track_id,))
            for raw_name in tag_names:
                name = raw_name.strip()
                if not name:
                    continue
                row = conn.execute(
                    "SELECT id FROM tags WHERE name = ? COLLATE NOCASE", (name,)
                ).fetchone()
                if row:
                    tag_id = row["id"]
                else:
                    tag_id = conn.execute("INSERT INTO tags (name) VALUES (?)", (name,)).lastrowid
                conn.execute(
                    "INSERT OR IGNORE INTO track_tags (track_id, tag_id) VALUES (?, ?)",
                    (track_id, tag_id),
                )

    def delete_unused(self) -> int:
        cursor = self._db.execute(
            "DELETE FROM tags WHERE id NOT IN (SELECT DISTINCT tag_id FROM track_tags)"
        )
        return cursor.rowcount

    def rename(self, tag_id: int, new_name: str) -> Tag:
        """Renomeia a tag preservando todas as associações com faixas. Se já
        existir outra tag com o mesmo nome (case-insensitive, mesma regra do
        UNIQUE da coluna), faz merge em vez de duplicar ou falhar: move as
        associações da tag antiga para a existente e remove a antiga — assim
        nenhuma faixa perde a tag e nunca sobra duplicata."""
        new_name = new_name.strip()
        if not new_name:
            raise ValueError("O nome da tag não pode ficar vazio.")

        with self._db.transaction() as conn:
            existing = conn.execute(
                "SELECT id, name FROM tags WHERE name = ? COLLATE NOCASE AND id != ?",
                (new_name, tag_id),
            ).fetchone()
            if existing is not None:
                target_id = existing["id"]
                conn.execute(
                    """
                    INSERT OR IGNORE INTO track_tags (track_id, tag_id)
                    SELECT track_id, ? FROM track_tags WHERE tag_id = ?
                    """,
                    (target_id, tag_id),
                )
                conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
                return Tag(id=target_id, name=existing["name"])

            conn.execute("UPDATE tags SET name = ? WHERE id = ?", (new_name, tag_id))
            return Tag(id=tag_id, name=new_name)

    def delete(self, tag_id: int) -> None:
        """Remove a tag e suas associações (track_tags, via ON DELETE CASCADE) —
        as faixas em si nunca são tocadas."""
        self._db.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
