"""Conexão SQLite e inicialização do schema.

A conexão é aberta com ``check_same_thread=False`` porque o scanner roda em
uma QThread separada, mas todo o acesso concorrente é serializado por um
``threading.Lock`` em :class:`Database` — SQLite não lida bem com escritas
paralelas de múltiplas conexões/threads.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from .schema import SCHEMA_SQL, SCHEMA_VERSION


def _dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    fields = [column[0] for column in cursor.description]
    return dict(zip(fields, row))


class Database:
    """Wrapper fino sobre :mod:`sqlite3` com inicialização de schema e lock."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(str(path), check_same_thread=False)
        self._connection.row_factory = _dict_factory
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        with self._lock, self._connection:
            self._connection.executescript(SCHEMA_SQL)
            self._connection.execute(
                "INSERT OR REPLACE INTO schema_info (key, value) VALUES ('version', ?)",
                (str(SCHEMA_VERSION),),
            )

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cursor = self._connection.execute(sql, params)
            self._connection.commit()
            return cursor

    def executemany(self, sql: str, seq_of_params) -> sqlite3.Cursor:
        with self._lock:
            cursor = self._connection.executemany(sql, seq_of_params)
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

    def transaction(self):
        """Context manager para agrupar múltiplas escritas em uma transação."""
        return _Transaction(self)

    def close(self) -> None:
        with self._lock:
            self._connection.close()


class _Transaction:
    def __init__(self, db: Database):
        self._db = db

    def __enter__(self) -> sqlite3.Connection:
        self._db._lock.acquire()
        return self._db._connection

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is None:
                self._db._connection.commit()
            else:
                self._db._connection.rollback()
        finally:
            self._db._lock.release()
