"""Tipos de dados do módulo Downloader (sem nenhuma dependência de Qt)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class AudioFormat(str, Enum):
    MP3 = "mp3"
    BEST_ORIGINAL = "best"


class Mp3Quality(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    ECONOMIC = "economic"


MP3_QUALITY_LABELS: dict[Mp3Quality, str] = {
    Mp3Quality.HIGH: "Alta (~192 kbps)",
    Mp3Quality.MEDIUM: "Média (~128 kbps)",
    Mp3Quality.ECONOMIC: "Econômica (~96 kbps)",
}

MP3_QUALITY_KBPS: dict[Mp3Quality, str] = {
    Mp3Quality.HIGH: "192",
    Mp3Quality.MEDIUM: "128",
    Mp3Quality.ECONOMIC: "96",
}


@dataclass
class DownloadOptions:
    url: str
    destination_folder: Path
    audio_format: AudioFormat = AudioFormat.MP3
    mp3_quality: Mp3Quality = Mp3Quality.HIGH
    create_playlist_subfolder: bool = True
    number_tracks: bool = True
    archive_path: Path | None = None


class ItemStatus(str, Enum):
    DONE = "done"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class DownloadItemResult:
    index: int
    title: str
    status: ItemStatus
    error_message: str = ""
    file_path: Path | None = None


@dataclass
class DownloadReport:
    total_items: int
    completed: list[DownloadItemResult] = field(default_factory=list)
    cancelled: bool = False
    fatal_error: str = ""

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.completed if r.status == ItemStatus.DONE)

    @property
    def error_count(self) -> int:
        return sum(1 for r in self.completed if r.status == ItemStatus.ERROR)

    @property
    def skipped_count(self) -> int:
        return sum(1 for r in self.completed if r.status == ItemStatus.SKIPPED)
