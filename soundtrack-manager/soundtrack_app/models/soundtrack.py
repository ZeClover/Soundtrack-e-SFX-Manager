"""Modelos de Soundtrack, Seção e Item de soundtrack."""

from __future__ import annotations

from dataclasses import dataclass, field

from .track import Track


@dataclass(slots=True)
class SoundtrackItem:
    id: int
    soundtrack_id: int
    section_id: int | None
    track_id: int
    position: int
    track: Track | None = None


@dataclass(slots=True)
class SoundtrackSection:
    id: int
    soundtrack_id: int
    name: str
    position: int
    items: list[SoundtrackItem] = field(default_factory=list)


@dataclass(slots=True)
class Soundtrack:
    id: int
    name: str
    campaign_id: int | None
    created_at: str
    updated_at: str
    track_count: int = 0

    @classmethod
    def from_row(cls, row: dict) -> "Soundtrack":
        return cls(
            id=row["id"],
            name=row["name"],
            campaign_id=row.get("campaign_id"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            track_count=row.get("track_count") or 0,
        )
