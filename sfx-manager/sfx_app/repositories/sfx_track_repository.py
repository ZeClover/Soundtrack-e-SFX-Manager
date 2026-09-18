"""Repositório de acesso a efeitos sonoros (sfx_tracks) no banco SQLite.

Segue o mesmo padrão do ``TrackRepository`` do Soundtrack Manager: upsert
idempotente durante o escaneamento (preservando classificações do usuário),
filtros de biblioteca e ações pontuais (favorito, nota, categoria, hotkey).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sfx_app.database import Database
from sfx_app.models import SfxTrack

_SELECT_BASE = """
SELECT
    t.*,
    cat.name AS category_name,
    (SELECT GROUP_CONCAT(tg.name, char(31)) FROM sfx_track_tags tt
        JOIN sfx_tags tg ON tg.id = tt.tag_id WHERE tt.track_id = t.id) AS tags,
    (SELECT hk.key FROM sfx_hotkeys hk WHERE hk.track_id = t.id) AS hotkey,
    (SELECT COUNT(*) FROM sfx_pack_items pi WHERE pi.track_id = t.id) AS in_pack_count
FROM sfx_tracks t
LEFT JOIN sfx_categories cat ON cat.id = t.category_id
"""


@dataclass(slots=True)
class SfxTrackFilter:
    search_text: str = ""
    library_root_id: int | None = None
    category_id: int | None = None
    tag_ids: tuple[int, ...] = field(default_factory=tuple)
    favorites_only: bool = False
    missing_only: bool = False
    exclude_missing: bool = True
    order_by: str = "title"  # title | date_detected
    limit: int | None = None


_ORDER_CLAUSES = {
    "title": "ORDER BY t.title COLLATE NOCASE ASC",
    "date_detected": "ORDER BY t.date_detected DESC",
}


class SfxTrackRepository:
    def __init__(self, db: Database):
        self._db = db

    # ------------------------------------------------------------------
    # Escaneamento / upsert
    # ------------------------------------------------------------------

    def upsert_from_scan(
        self,
        *,
        library_root_id: int,
        category_id: int | None,
        absolute_path: str,
        relative_path: str,
        filename: str,
        extension: str,
        title: str,
        duration_seconds: float,
        file_size: int,
        partial_hash: str,
    ) -> int:
        now = _now_iso()
        existing = self._db.query_one(
            "SELECT id FROM sfx_tracks WHERE absolute_path = ?", (absolute_path,)
        )
        if existing:
            self._db.execute(
                """
                UPDATE sfx_tracks SET
                    relative_path = ?, filename = ?, extension = ?, title = ?,
                    duration_seconds = ?, file_size = ?, partial_hash = ?,
                    is_missing = 0, updated_at = ?
                WHERE id = ?
                """,
                (relative_path, filename, extension, title, duration_seconds,
                 file_size, partial_hash, now, existing["id"]),
            )
            return existing["id"]

        cursor = self._db.execute(
            """
            INSERT INTO sfx_tracks (
                library_root_id, category_id, absolute_path, relative_path, filename,
                extension, title, duration_seconds, file_size, partial_hash,
                is_favorite, note, is_missing, play_count, last_played_at,
                date_detected, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, '', 0, 0, NULL, ?, ?)
            """,
            (library_root_id, category_id, absolute_path, relative_path, filename,
             extension, title, duration_seconds, file_size, partial_hash, now, now),
        )
        return cursor.lastrowid

    def mark_missing(self, library_root_id: int, seen_paths: set[str]) -> int:
        rows = self._db.query_all(
            "SELECT id, absolute_path FROM sfx_tracks WHERE library_root_id = ? AND is_missing = 0",
            (library_root_id,),
        )
        missing_ids = [row["id"] for row in rows if row["absolute_path"] not in seen_paths]
        if missing_ids:
            placeholders = ",".join("?" * len(missing_ids))
            self._db.execute(
                f"UPDATE sfx_tracks SET is_missing = 1 WHERE id IN ({placeholders})",
                tuple(missing_ids),
            )
        return len(missing_ids)

    def relocate(self, track_id: int, new_absolute_path: str, new_relative_path: str) -> None:
        self._db.execute(
            """
            UPDATE sfx_tracks SET absolute_path = ?, relative_path = ?, is_missing = 0, updated_at = ?
            WHERE id = ?
            """,
            (new_absolute_path, new_relative_path, _now_iso(), track_id),
        )

    # ------------------------------------------------------------------
    # Leitura / filtros
    # ------------------------------------------------------------------

    def get_by_id(self, track_id: int) -> SfxTrack | None:
        row = self._db.query_one(_SELECT_BASE + " WHERE t.id = ?", (track_id,))
        return SfxTrack.from_row(row) if row else None

    def find(self, filt: SfxTrackFilter) -> list[SfxTrack]:
        clauses: list[str] = []
        params: list = []

        if filt.library_root_id is not None:
            clauses.append("t.library_root_id = ?")
            params.append(filt.library_root_id)

        if filt.exclude_missing and not filt.missing_only:
            clauses.append("t.is_missing = 0")

        if filt.missing_only:
            clauses.append("t.is_missing = 1")

        if filt.favorites_only:
            clauses.append("t.is_favorite = 1")

        if filt.category_id is not None:
            clauses.append("t.category_id = ?")
            params.append(filt.category_id)

        if filt.tag_ids:
            placeholders = ",".join("?" * len(filt.tag_ids))
            clauses.append(
                f"EXISTS (SELECT 1 FROM sfx_track_tags tt WHERE tt.track_id = t.id "
                f"AND tt.tag_id IN ({placeholders}))"
            )
            params.extend(filt.tag_ids)

        if filt.search_text.strip():
            like = f"%{filt.search_text.strip()}%"
            clauses.append(
                """(
                    t.title LIKE ? OR t.filename LIKE ? OR t.note LIKE ? OR
                    t.relative_path LIKE ? OR cat.name LIKE ? OR
                    EXISTS (SELECT 1 FROM sfx_track_tags tt JOIN sfx_tags tg ON tg.id = tt.tag_id
                            WHERE tt.track_id = t.id AND tg.name LIKE ?)
                )"""
            )
            params.extend([like] * 6)

        sql = _SELECT_BASE
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " " + _ORDER_CLAUSES.get(filt.order_by, _ORDER_CLAUSES["title"])
        if filt.limit:
            sql += " LIMIT ?"
            params.append(filt.limit)

        rows = self._db.query_all(sql, tuple(params))
        return [SfxTrack.from_row(row) for row in rows]

    def get_many_by_ids(self, track_ids: list[int]) -> dict[int, SfxTrack]:
        if not track_ids:
            return {}
        placeholders = ",".join("?" * len(track_ids))
        rows = self._db.query_all(_SELECT_BASE + f" WHERE t.id IN ({placeholders})", tuple(track_ids))
        return {row["id"]: SfxTrack.from_row(row) for row in rows}

    def stats(self, library_root_id: int | None = None) -> dict[str, int]:
        where = "WHERE t.is_missing = 0"
        params: tuple = ()
        if library_root_id is not None:
            where += " AND t.library_root_id = ?"
            params = (library_root_id,)

        row = self._db.query_one(
            f"""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN t.is_favorite = 1 THEN 1 ELSE 0 END) AS favorites
            FROM sfx_tracks t
            {where}
            """,
            params,
        )
        return {"total": row["total"] or 0, "favorites": row["favorites"] or 0}

    # ------------------------------------------------------------------
    # Ações do usuário
    # ------------------------------------------------------------------

    def set_favorite(self, track_id: int, is_favorite: bool) -> None:
        self._db.execute(
            "UPDATE sfx_tracks SET is_favorite = ?, updated_at = ? WHERE id = ?",
            (int(is_favorite), _now_iso(), track_id),
        )

    def set_note(self, track_id: int, note: str) -> None:
        self._db.execute(
            "UPDATE sfx_tracks SET note = ?, updated_at = ? WHERE id = ?", (note, _now_iso(), track_id)
        )

    def set_category(self, track_id: int, category_id: int | None) -> None:
        self._db.execute(
            "UPDATE sfx_tracks SET category_id = ?, updated_at = ? WHERE id = ?",
            (category_id, _now_iso(), track_id),
        )

    def register_play(self, track_id: int) -> None:
        now = _now_iso()
        self._db.execute(
            "UPDATE sfx_tracks SET play_count = play_count + 1, last_played_at = ? WHERE id = ?",
            (now, track_id),
        )
        self._db.execute(
            "INSERT INTO sfx_play_history (track_id, played_at) VALUES (?, ?)", (track_id, now)
        )

    def delete(self, track_id: int) -> None:
        self._db.execute("DELETE FROM sfx_tracks WHERE id = ?", (track_id,))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
