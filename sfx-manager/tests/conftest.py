import os
from pathlib import Path

import pytest

# Ambiente de teste é headless (sem display) — precisa ser definido antes de
# qualquer QApplication/QGuiApplication ser criada neste processo.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.database import Database  # noqa: E402
from app.repositories import (  # noqa: E402
    CategoryRepository,
    HistoryRepository,
    HotkeyRepository,
    LibraryRootRepository,
    PackRepository,
    SettingsRepository,
    SfxTrackRepository,
    TagRepository,
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
def track_repo(db: Database) -> SfxTrackRepository:
    return SfxTrackRepository(db)


@pytest.fixture
def tag_repo(db: Database) -> TagRepository:
    return TagRepository(db)


@pytest.fixture
def category_repo(db: Database) -> CategoryRepository:
    return CategoryRepository(db)


@pytest.fixture
def pack_repo(db: Database) -> PackRepository:
    return PackRepository(db)


@pytest.fixture
def hotkey_repo(db: Database) -> HotkeyRepository:
    return HotkeyRepository(db)


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
def sample_track_id(track_repo: SfxTrackRepository, library_root_repo: LibraryRootRepository) -> int:
    root_id = library_root_repo.get_or_create("/library")
    return track_repo.upsert_from_scan(
        library_root_id=root_id,
        category_id=None,
        absolute_path="/library/sword.wav",
        relative_path="sword.wav",
        filename="sword.wav",
        extension=".wav",
        title="Sword Slash",
        duration_seconds=0.8,
        file_size=4096,
        partial_hash="abc123",
    )
