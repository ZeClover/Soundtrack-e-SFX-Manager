"""Repositório de hotkeys simples (item 44) — no máximo uma tecla por efeito."""

from __future__ import annotations

from app.database import Database


class HotkeyRepository:
    def __init__(self, db: Database):
        self._db = db

    def get_map(self) -> dict[str, int]:
        """Retorna {tecla: track_id} para montar os atalhos de teclado da UI."""
        rows = self._db.query_all("SELECT key, track_id FROM sfx_hotkeys")
        return {row["key"]: row["track_id"] for row in rows}

    def get_key_for_track(self, track_id: int) -> str | None:
        row = self._db.query_one("SELECT key FROM sfx_hotkeys WHERE track_id = ?", (track_id,))
        return row["key"] if row else None

    def assign(self, track_id: int, key: str) -> None:
        """Atribui ``key`` a ``track_id``, liberando-a de qualquer outro efeito antes."""
        key = key.strip().upper()
        with self._db.transaction() as conn:
            conn.execute("DELETE FROM sfx_hotkeys WHERE key = ?", (key,))
            conn.execute("DELETE FROM sfx_hotkeys WHERE track_id = ?", (track_id,))
            conn.execute("INSERT INTO sfx_hotkeys (track_id, key) VALUES (?, ?)", (track_id, key))

    def clear(self, track_id: int) -> None:
        self._db.execute("DELETE FROM sfx_hotkeys WHERE track_id = ?", (track_id,))
