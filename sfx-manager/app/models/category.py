from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Category:
    id: int
    name: str


@dataclass(slots=True)
class Tag:
    id: int
    name: str
