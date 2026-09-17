"""Repositório de categorias de SFX (item 40 — sugeridas, mas livres)."""

from __future__ import annotations

from app.database import Database
from app.models import Category


class CategoryRepository:
    def __init__(self, db: Database):
        self._db = db

    def list_all(self) -> list[Category]:
        rows = self._db.query_all("SELECT id, name FROM sfx_categories ORDER BY name COLLATE NOCASE ASC")
        return [Category(id=row["id"], name=row["name"]) for row in rows]

    def get_or_create(self, name: str) -> Category:
        name = name.strip()
        row = self._db.query_one("SELECT id, name FROM sfx_categories WHERE name = ? COLLATE NOCASE", (name,))
        if row:
            return Category(id=row["id"], name=row["name"])
        cursor = self._db.execute("INSERT INTO sfx_categories (name) VALUES (?)", (name,))
        return Category(id=cursor.lastrowid, name=name)

    def rename(self, category_id: int, name: str) -> None:
        self._db.execute("UPDATE sfx_categories SET name = ? WHERE id = ?", (name.strip(), category_id))

    def delete(self, category_id: int) -> None:
        self._db.execute("DELETE FROM sfx_categories WHERE id = ?", (category_id,))
