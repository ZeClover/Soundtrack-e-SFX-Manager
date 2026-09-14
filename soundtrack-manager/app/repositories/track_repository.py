"""Repositório de acesso a faixas (tracks) no banco SQLite.

Concentra toda a montagem de SQL relacionada a `tracks`: upsert durante o
escaneamento, filtros da biblioteca (busca, campanha, tags, favoritos,
não avaliadas, ausentes) e atualizações pontuais de metadados do usuário
(favorito, nota, tags, campanhas).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.database import Database
from app.models import Track

_SELECT_BASE = """
SELECT
    t.*,
    (SELECT GROUP_CONCAT(tg.name, char(31)) FROM track_tags tt
        JOIN tags tg ON tg.id = tt.tag_id WHERE tt.track_id = t.id) AS tags,
    (SELECT GROUP_CONCAT(c.name, char(31)) FROM track_campaigns tc
        JOIN campaigns c ON c.id = tc.campaign_id WHERE tc.track_id = t.id) AS campaigns,
    (SELECT COUNT(*) FROM soundtrack_items si WHERE si.track_id = t.id) AS in_soundtrack_count
FROM tracks t
"""


@dataclass(slots=True)
class TrackFilter:
    search_text: str = ""
    library_root_id: int | None = None
    campaign_id: int | None = None
    tag_ids: tuple[int, ...] = field(default_factory=tuple)
    favorites_only: bool = False
    unrated_only: bool = False
    missing_only: bool = False
    exclude_missing: bool = True
    order_by: str = "title"  # title | date_detected | random
    limit: int | None = None


_ORDER_CLAUSES = {
    "title": "ORDER BY t.title COLLATE NOCASE ASC",
    "date_detected": "ORDER BY t.date_detected DESC",
    "random": "ORDER BY RANDOM()",
    "recent_play": "ORDER BY t.last_played_at DESC",
}


class TrackRepository:
    def __init__(self, db: Database):
        self._db = db

    # ------------------------------------------------------------------
    # Escaneamento / upsert
    # ------------------------------------------------------------------

    def upsert_from_scan(
        self,
        *,
        library_root_id: int,
        absolute_path: str,
        relative_path: str,
        filename: str,
        extension: str,
        title: str,
        artist: str | None,
        album: str | None,
        duration_seconds: float,
        file_size: int,
        partial_hash: str,
        has_embedded_cover: bool,
    ) -> int:
        """Insere a faixa se for nova, ou atualiza metadados de arquivo se já existir.

        Preserva campos que são "do usuário" (favorito, nota, tags) em
        atualizações — o scan nunca deve apagar essas classificações.
        """
        now = _now_iso()
        existing = self._db.query_one(
            "SELECT id, is_missing FROM tracks WHERE absolute_path = ?", (absolute_path,)
        )
        if existing:
            self._db.execute(
                """
                UPDATE tracks SET
                    relative_path = ?, filename = ?, extension = ?,
                    title = ?, artist = ?, album = ?, duration_seconds = ?,
                    file_size = ?, partial_hash = ?, has_embedded_cover = ?,
                    is_missing = 0, updated_at = ?
                WHERE id = ?
                """,
                (
                    relative_path, filename, extension, title, artist, album,
                    duration_seconds, file_size, partial_hash, int(has_embedded_cover),
                    now, existing["id"],
                ),
            )
            return existing["id"]

        cursor = self._db.execute(
            """
            INSERT INTO tracks (
                library_root_id, absolute_path, relative_path, filename, extension,
                title, artist, album, duration_seconds, file_size, partial_hash,
                has_embedded_cover, is_favorite, note, is_missing, play_count,
                last_played_at, date_detected, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, '', 0, 0, NULL, ?, ?)
            """,
            (
                library_root_id, absolute_path, relative_path, filename, extension,
                title, artist, album, duration_seconds, file_size, partial_hash,
                int(has_embedded_cover), now, now,
            ),
        )
        return cursor.lastrowid

    def mark_missing(self, library_root_id: int, seen_paths: set[str]) -> int:
        """Marca como ausentes as faixas do root que não apareceram neste scan."""
        rows = self._db.query_all(
            "SELECT id, absolute_path FROM tracks WHERE library_root_id = ? AND is_missing = 0",
            (library_root_id,),
        )
        missing_ids = [row["id"] for row in rows if row["absolute_path"] not in seen_paths]
        if missing_ids:
            placeholders = ",".join("?" * len(missing_ids))
            self._db.execute(
                f"UPDATE tracks SET is_missing = 1 WHERE id IN ({placeholders})",
                tuple(missing_ids),
            )
        return len(missing_ids)

    def unmark_missing(self, track_id: int) -> None:
        self._db.execute("UPDATE tracks SET is_missing = 0 WHERE id = ?", (track_id,))

    def relocate(self, track_id: int, new_absolute_path: str, new_relative_path: str) -> None:
        self._db.execute(
            """
            UPDATE tracks SET absolute_path = ?, relative_path = ?, is_missing = 0, updated_at = ?
            WHERE id = ?
            """,
            (new_absolute_path, new_relative_path, _now_iso(), track_id),
        )

    # ------------------------------------------------------------------
    # Leitura / filtros
    # ------------------------------------------------------------------

    def get_by_id(self, track_id: int) -> Track | None:
        row = self._db.query_one(_SELECT_BASE + " WHERE t.id = ?", (track_id,))
        return Track.from_row(row) if row else None

    def find(self, filt: TrackFilter) -> list[Track]:
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

        if filt.unrated_only:
            clauses.append(
                "t.play_count = 0 AND t.is_favorite = 0 "
                "AND NOT EXISTS (SELECT 1 FROM soundtrack_items si WHERE si.track_id = t.id)"
            )

        if filt.campaign_id is not None:
            clauses.append(
                "EXISTS (SELECT 1 FROM track_campaigns tc WHERE tc.track_id = t.id AND tc.campaign_id = ?)"
            )
            params.append(filt.campaign_id)

        if filt.tag_ids:
            placeholders = ",".join("?" * len(filt.tag_ids))
            clauses.append(
                f"EXISTS (SELECT 1 FROM track_tags tt WHERE tt.track_id = t.id "
                f"AND tt.tag_id IN ({placeholders}))"
            )
            params.extend(filt.tag_ids)

        if filt.search_text.strip():
            like = f"%{filt.search_text.strip()}%"
            clauses.append(
                """(
                    t.title LIKE ? OR t.filename LIKE ? OR t.artist LIKE ? OR
                    t.note LIKE ? OR t.relative_path LIKE ? OR
                    EXISTS (SELECT 1 FROM track_tags tt JOIN tags tg ON tg.id = tt.tag_id
                            WHERE tt.track_id = t.id AND tg.name LIKE ?) OR
                    EXISTS (SELECT 1 FROM track_campaigns tc JOIN campaigns c ON c.id = tc.campaign_id
                            WHERE tc.track_id = t.id AND c.name LIKE ?)
                )"""
            )
            params.extend([like] * 7)

        sql = _SELECT_BASE
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " " + _ORDER_CLAUSES.get(filt.order_by, _ORDER_CLAUSES["title"])
        if filt.limit:
            sql += " LIMIT ?"
            params.append(filt.limit)

        rows = self._db.query_all(sql, tuple(params))
        return [Track.from_row(row) for row in rows]

    def get_many_by_ids(self, track_ids: list[int]) -> dict[int, Track]:
        if not track_ids:
            return {}
        placeholders = ",".join("?" * len(track_ids))
        rows = self._db.query_all(_SELECT_BASE + f" WHERE t.id IN ({placeholders})", tuple(track_ids))
        return {row["id"]: Track.from_row(row) for row in rows}

    def count(self, library_root_id: int | None = None) -> int:
        if library_root_id is None:
            row = self._db.query_one("SELECT COUNT(*) AS n FROM tracks WHERE is_missing = 0")
        else:
            row = self._db.query_one(
                "SELECT COUNT(*) AS n FROM tracks WHERE library_root_id = ? AND is_missing = 0",
                (library_root_id,),
            )
        return row["n"] if row else 0

    def stats(self, library_root_id: int | None = None) -> dict[str, int]:
        """Estatísticas simples para o item 71 (contadores da biblioteca)."""
        where = "WHERE t.is_missing = 0"
        params: tuple = ()
        if library_root_id is not None:
            where += " AND t.library_root_id = ?"
            params = (library_root_id,)

        row = self._db.query_one(
            f"""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN t.is_favorite = 1 THEN 1 ELSE 0 END) AS favorites,
                SUM(CASE WHEN t.play_count > 0 OR t.is_favorite = 1 THEN 1 ELSE 0 END) AS evaluated,
                SUM(CASE WHEN EXISTS (
                    SELECT 1 FROM soundtrack_items si WHERE si.track_id = t.id
                ) THEN 1 ELSE 0 END) AS used_in_soundtracks
            FROM tracks t
            {where}
            """,
            params,
        )
        return {
            "total": row["total"] or 0,
            "favorites": row["favorites"] or 0,
            "evaluated": row["evaluated"] or 0,
            "used_in_soundtracks": row["used_in_soundtracks"] or 0,
        }

    # ------------------------------------------------------------------
    # Ações do usuário
    # ------------------------------------------------------------------

    def set_favorite(self, track_id: int, is_favorite: bool) -> None:
        self._db.execute(
            "UPDATE tracks SET is_favorite = ?, updated_at = ? WHERE id = ?",
            (int(is_favorite), _now_iso(), track_id),
        )

    def set_note(self, track_id: int, note: str) -> None:
        self._db.execute(
            "UPDATE tracks SET note = ?, updated_at = ? WHERE id = ?", (note, _now_iso(), track_id)
        )

    def register_play(self, track_id: int) -> None:
        now = _now_iso()
        self._db.execute(
            "UPDATE tracks SET play_count = play_count + 1, last_played_at = ? WHERE id = ?",
            (now, track_id),
        )
        self._db.execute(
            "INSERT INTO play_history (track_id, played_at) VALUES (?, ?)", (track_id, now)
        )

    def delete(self, track_id: int) -> None:
        self._db.execute("DELETE FROM tracks WHERE id = ?", (track_id,))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
