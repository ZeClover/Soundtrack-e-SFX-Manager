"""Definição do schema SQLite do RPG Soundtrack Manager.

Usamos ``CREATE TABLE IF NOT EXISTS`` para permitir migrações simples e
aditivas: novas versões do app podem adicionar tabelas/colunas sem quebrar
bancos já existentes. Para o MVP isso é suficiente; uma tabela
``schema_version`` guarda a versão aplicada para futuras migrações mais
elaboradas.
"""

from __future__ import annotations

SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_info (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS library_roots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    last_scanned_at TEXT
);

CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    library_root_id INTEGER NOT NULL REFERENCES library_roots(id) ON DELETE CASCADE,
    absolute_path TEXT NOT NULL UNIQUE,
    relative_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    extension TEXT NOT NULL,
    title TEXT NOT NULL,
    artist TEXT,
    album TEXT,
    duration_seconds REAL NOT NULL DEFAULT 0,
    file_size INTEGER NOT NULL DEFAULT 0,
    partial_hash TEXT,
    has_embedded_cover INTEGER NOT NULL DEFAULT 0,
    is_favorite INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '',
    is_missing INTEGER NOT NULL DEFAULT 0,
    play_count INTEGER NOT NULL DEFAULT 0,
    last_played_at TEXT,
    date_detected TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tracks_library_root ON tracks(library_root_id);
CREATE INDEX IF NOT EXISTS idx_tracks_favorite ON tracks(is_favorite);
CREATE INDEX IF NOT EXISTS idx_tracks_missing ON tracks(is_missing);
CREATE INDEX IF NOT EXISTS idx_tracks_partial_hash ON tracks(partial_hash);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS track_tags (
    track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (track_id, tag_id)
);
CREATE INDEX IF NOT EXISTS idx_track_tags_tag ON track_tags(tag_id);

CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS track_campaigns (
    track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    PRIMARY KEY (track_id, campaign_id)
);
CREATE INDEX IF NOT EXISTS idx_track_campaigns_campaign ON track_campaigns(campaign_id);

CREATE TABLE IF NOT EXISTS soundtracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    campaign_id INTEGER REFERENCES campaigns(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS soundtrack_sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    soundtrack_id INTEGER NOT NULL REFERENCES soundtracks(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    position INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sections_soundtrack ON soundtrack_sections(soundtrack_id);

CREATE TABLE IF NOT EXISTS soundtrack_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    soundtrack_id INTEGER NOT NULL REFERENCES soundtracks(id) ON DELETE CASCADE,
    section_id INTEGER REFERENCES soundtrack_sections(id) ON DELETE SET NULL,
    track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    position INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_items_soundtrack ON soundtrack_items(soundtrack_id);
CREATE INDEX IF NOT EXISTS idx_items_track ON soundtrack_items(track_id);

CREATE TABLE IF NOT EXISTS play_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    played_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_history_played_at ON play_history(played_at);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""
