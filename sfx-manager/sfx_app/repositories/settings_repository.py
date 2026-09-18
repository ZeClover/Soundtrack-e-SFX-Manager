"""Repositório de configurações chave/valor (tema, pasta padrão, volume, etc)."""

from __future__ import annotations

import json
from typing import Any

from sfx_app.database import Database


class SettingsRepository:
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
        result = {}
        for row in rows:
            try:
                result[row["key"]] = json.loads(row["value"])
            except (json.JSONDecodeError, TypeError):
                result[row["key"]] = row["value"]
        return result
