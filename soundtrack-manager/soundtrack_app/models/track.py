"""Modelo de dados de uma faixa (Track)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Track:
    id: int
    library_root_id: int
    absolute_path: str
    relative_path: str
    filename: str
    extension: str
    title: str
    artist: str | None
    album: str | None
    duration_seconds: float
    file_size: int
    partial_hash: str | None
    has_embedded_cover: bool
    is_favorite: bool
    note: str
    is_missing: bool
    play_count: int
    last_played_at: str | None
    date_detected: str
    updated_at: str
    tags: list[str] = field(default_factory=list)
    campaigns: list[str] = field(default_factory=list)
    in_soundtrack_count: int = 0

    @property
    def evaluation_state(self) -> str:
        """Estado de avaliação usado pelo filtro 'Ainda não avaliadas' (item 70)."""
        if self.is_favorite:
            return "favorita"
        if self.in_soundtrack_count > 0:
            return "usada"
        if self.play_count > 0:
            return "ouvida"
        return "nunca_ouvida"

    @classmethod
    def from_row(cls, row: dict) -> "Track":
        return cls(
            id=row["id"],
            library_root_id=row["library_root_id"],
            absolute_path=row["absolute_path"],
            relative_path=row["relative_path"],
            filename=row["filename"],
            extension=row["extension"],
            title=row["title"],
            artist=row.get("artist"),
            album=row.get("album"),
            duration_seconds=row["duration_seconds"],
            file_size=row["file_size"],
            partial_hash=row.get("partial_hash"),
            has_embedded_cover=bool(row["has_embedded_cover"]),
            is_favorite=bool(row["is_favorite"]),
            note=row.get("note") or "",
            is_missing=bool(row["is_missing"]),
            play_count=row["play_count"],
            last_played_at=row.get("last_played_at"),
            date_detected=row["date_detected"],
            updated_at=row["updated_at"],
            tags=_split_multi(row.get("tags")),
            campaigns=_split_multi(row.get("campaigns")),
            in_soundtrack_count=row.get("in_soundtrack_count") or 0,
        )


def _split_multi(value) -> list[str]:
    if not value:
        return []
    return sorted({part for part in str(value).split("\x1f") if part})
