"""Modelos de Pack de SFX e seus itens."""

from __future__ import annotations

from dataclasses import dataclass

from .sfx_track import SfxTrack


@dataclass(slots=True)
class SfxPackItem:
    id: int
    pack_id: int
    track_id: int
    position: int
    track: SfxTrack | None = None


@dataclass(slots=True)
class SfxPack:
    id: int
    name: str
    created_at: str
    updated_at: str
    track_count: int = 0

    @classmethod
    def from_row(cls, row: dict) -> "SfxPack":
        return cls(
            id=row["id"],
            name=row["name"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            track_count=row.get("track_count") or 0,
        )
