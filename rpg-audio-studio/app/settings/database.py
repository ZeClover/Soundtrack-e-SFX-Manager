"""Banco SQLite próprio do Studio — só preferências que não pertencem a
nenhum módulo (item 19/21: "pode continuar usando bancos separados por
módulo"). Mesmo wrapper fino usado pelos outros dois apps da suíte."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    fields = [column[0] for column in cursor.description]
    return dict(zip(fields, row))


class Database:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(str(path), check_same_thread=False)
        self._connection.row_factory = _dict_factory
        self._connection.execute("PRAGMA journal_mode = WAL")
        with self._lock, self._connection:
            self._connection.executescript(_SCHEMA_SQL)

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cursor = self._connection.execute(sql, params)
            self._connection.commit()
            return cursor

    def query_one(self, sql: str, params: tuple = ()) -> dict | None:
        with self._lock:
            cursor = self._connection.execute(sql, params)
            return cursor.fetchone()

    def query_all(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._lock:
            cursor = self._connection.execute(sql, params)
            return cursor.fetchall()

    def close(self) -> None:
        with self._lock:
            self._connection.close()
