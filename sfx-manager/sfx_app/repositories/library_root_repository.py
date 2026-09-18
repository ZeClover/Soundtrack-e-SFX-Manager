"""Repositório de pastas raiz de biblioteca escaneadas."""

from __future__ import annotations

from datetime import datetime, timezone

from sfx_app.database import Database


class LibraryRootRepository:
    def __init__(self, db: Database):
        self._db = db

    def get_or_create(self, path: str) -> int:
        row = self._db.query_one("SELECT id FROM library_roots WHERE path = ?", (path,))
        if row:
            return row["id"]
        cursor = self._db.execute("INSERT INTO library_roots (path) VALUES (?)", (path,))
        return cursor.lastrowid

    def touch_scanned(self, root_id: int) -> None:
        self._db.execute(
            "UPDATE library_roots SET last_scanned_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"), root_id),
        )

    def get_path(self, root_id: int) -> str | None:
        row = self._db.query_one("SELECT path FROM library_roots WHERE id = ?", (root_id,))
        return row["path"] if row else None

    def list_all(self) -> list[dict]:
        return self._db.query_all("SELECT id, path, last_scanned_at FROM library_roots ORDER BY path")
