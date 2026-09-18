import os
from pathlib import Path

import pytest

# Ambiente de teste é headless (sem display) — precisa ser definido antes de
# qualquer QApplication/QGuiApplication ser criada neste processo.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from soundtrack_app.database import Database  # noqa: E402
from soundtrack_app.repositories import (
    CampaignRepository,
    HistoryRepository,
    LibraryRootRepository,
    SettingsRepository,
    SoundtrackRepository,
    TagRepository,
    TrackRepository,
)


@pytest.fixture(scope="session", autouse=True)
def qt_core_app():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(tmp_path / "test.db")
    yield database
    database.close()


@pytest.fixture
def track_repo(db: Database) -> TrackRepository:
    return TrackRepository(db)


@pytest.fixture
def tag_repo(db: Database) -> TagRepository:
    return TagRepository(db)


@pytest.fixture
def campaign_repo(db: Database) -> CampaignRepository:
    return CampaignRepository(db)


@pytest.fixture
def soundtrack_repo(db: Database) -> SoundtrackRepository:
    return SoundtrackRepository(db)


@pytest.fixture
def history_repo(db: Database) -> HistoryRepository:
    return HistoryRepository(db)


@pytest.fixture
def settings_repo(db: Database) -> SettingsRepository:
    return SettingsRepository(db)


@pytest.fixture
def library_root_repo(db: Database) -> LibraryRootRepository:
    return LibraryRootRepository(db)


@pytest.fixture
def sample_track_id(track_repo: TrackRepository, library_root_repo: LibraryRootRepository) -> int:
    root_id = library_root_repo.get_or_create("/library")
    return track_repo.upsert_from_scan(
        library_root_id=root_id,
        absolute_path="/library/song.mp3",
        relative_path="song.mp3",
        filename="song.mp3",
        extension=".mp3",
        title="Battle Theme",
        artist="Composer",
        album="OST",
        duration_seconds=120.0,
        file_size=4096,
        partial_hash="abc123",
        has_embedded_cover=False,
    )
