"""Repositório chave/valor das preferências do Studio — mesmo padrão do
SettingsRepository já usado no Soundtrack Manager e no SFX Manager."""

from __future__ import annotations

import json
from typing import Any

from app.settings.database import Database

# Chaves conhecidas (item 19). Preferências que já moram no banco de um
# módulo (pasta da biblioteca de música/SFX) NÃO são duplicadas aqui — só o
# que é exclusivamente do Studio ou cruza vários módulos.
KEY_DEFAULT_DOWNLOADS_FOLDER = "default_downloads_folder"
KEY_DOWNLOADS_FOLDER_IS_LIBRARY = "downloads_folder_is_library"
KEY_PREFERRED_FORMAT = "downloader_preferred_format"
KEY_MP3_QUALITY = "downloader_mp3_quality"
KEY_NUMBER_TRACKS = "downloader_number_tracks"
KEY_CREATE_PLAYLIST_SUBFOLDER = "downloader_create_playlist_subfolder"
KEY_MUSIC_VOLUME = "music_volume"
KEY_SFX_VOLUME = "sfx_volume"
KEY_EXPORT_CONFLICT_POLICY = "export_conflict_policy"
KEY_THEME = "theme"


class StudioSettingsRepository:
    def __init__(self, db: Database):
        self._db = db

    def get(self, key: str, default: Any = None) -> Any:
        row = self._db.query_one("SELECT value FROM settings WHERE key = ?", (key,))
        if row is None:
            return default
        try:
            return json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            return row["value"]

    def set(self, key: str, value: Any) -> None:
        self._db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value)),
        )

    def all(self) -> dict[str, Any]:
        rows = self._db.query_all("SELECT key, value FROM settings")
        result: dict[str, Any] = {}
        for row in rows:
            try:
                result[row["key"]] = json.loads(row["value"])
            except (json.JSONDecodeError, TypeError):
                result[row["key"]] = row["value"]
        return result
