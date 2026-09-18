from __future__ import annotations

from pathlib import Path

from app.settings.database import Database
from app.settings.settings_repository import StudioSettingsRepository


def test_get_returns_default_when_missing(tmp_path: Path):
    db = Database(tmp_path / "settings.db")
    try:
        repo = StudioSettingsRepository(db)
        assert repo.get("nope", default="fallback") == "fallback"
    finally:
        db.close()


def test_set_then_get_roundtrips_various_types(tmp_path: Path):
    db = Database(tmp_path / "settings.db")
    try:
        repo = StudioSettingsRepository(db)
        repo.set("a_string", "valor")
        repo.set("a_bool", True)
        repo.set("a_number", 42)
        repo.set("a_dict", {"x": 1})

        assert repo.get("a_string") == "valor"
        assert repo.get("a_bool") is True
        assert repo.get("a_number") == 42
        assert repo.get("a_dict") == {"x": 1}
    finally:
        db.close()


def test_set_overwrites_existing_key(tmp_path: Path):
    db = Database(tmp_path / "settings.db")
    try:
        repo = StudioSettingsRepository(db)
        repo.set("k", "first")
        repo.set("k", "second")
        assert repo.get("k") == "second"
    finally:
        db.close()


def test_all_returns_every_key(tmp_path: Path):
    db = Database(tmp_path / "settings.db")
    try:
        repo = StudioSettingsRepository(db)
        repo.set("k1", "v1")
        repo.set("k2", "v2")
        assert repo.all() == {"k1": "v1", "k2": "v2"}
    finally:
        db.close()


def test_settings_persist_across_reconnect(tmp_path: Path):
    path = tmp_path / "settings.db"
    db1 = Database(path)
    StudioSettingsRepository(db1).set("persisted", "yes")
    db1.close()

    db2 = Database(path)
    try:
        assert StudioSettingsRepository(db2).get("persisted") == "yes"
    finally:
        db2.close()
