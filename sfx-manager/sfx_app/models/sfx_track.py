"""Modelo de dados de um efeito sonoro (SfxTrack)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SfxTrack:
    id: int
    library_root_id: int
    category_id: int | None
    absolute_path: str
    relative_path: str
    filename: str
    extension: str
    title: str
    duration_seconds: float
    file_size: int
    partial_hash: str | None
    is_favorite: bool
    note: str
    is_missing: bool
    play_count: int
    last_played_at: str | None
    date_detected: str
    updated_at: str
    tags: list[str] = field(default_factory=list)
    category_name: str | None = None
    hotkey: str | None = None
    in_pack_count: int = 0

    @classmethod
    def from_row(cls, row: dict) -> "SfxTrack":
        return cls(
            id=row["id"],
            library_root_id=row["library_root_id"],
            category_id=row.get("category_id"),
            absolute_path=row["absolute_path"],
            relative_path=row["relative_path"],
            filename=row["filename"],
            extension=row["extension"],
            title=row["title"],
            duration_seconds=row["duration_seconds"],
            file_size=row["file_size"],
            partial_hash=row.get("partial_hash"),
            is_favorite=bool(row["is_favorite"]),
            note=row.get("note") or "",
            is_missing=bool(row["is_missing"]),
            play_count=row["play_count"],
            last_played_at=row.get("last_played_at"),
            date_detected=row["date_detected"],
            updated_at=row["updated_at"],
            tags=_split_multi(row.get("tags")),
            category_name=row.get("category_name"),
            hotkey=row.get("hotkey"),
            in_pack_count=row.get("in_pack_count") or 0,
        )


def _split_multi(value) -> list[str]:
    if not value:
        return []
    return sorted({part for part in str(value).split("\x1f") if part})
