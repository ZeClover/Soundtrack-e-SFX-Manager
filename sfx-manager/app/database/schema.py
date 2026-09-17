"""Definição do schema SQLite do RPG SFX Manager.

Entidades (item 79 da especificação): SfxTrack, SfxCategory, Tag,
SfxTrackTag, SfxPack, SfxPackItem, Favorite (campo em sfx_tracks, como no
Soundtrack Manager), Hotkey, PlayHistory.
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

CREATE TABLE IF NOT EXISTS sfx_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS sfx_tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    library_root_id INTEGER NOT NULL REFERENCES library_roots(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES sfx_categories(id) ON DELETE SET NULL,
    absolute_path TEXT NOT NULL UNIQUE,
    relative_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    extension TEXT NOT NULL,
    title TEXT NOT NULL,
    duration_seconds REAL NOT NULL DEFAULT 0,
    file_size INTEGER NOT NULL DEFAULT 0,
    partial_hash TEXT,
    is_favorite INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '',
    is_missing INTEGER NOT NULL DEFAULT 0,
    play_count INTEGER NOT NULL DEFAULT 0,
    last_played_at TEXT,
    date_detected TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sfx_tracks_library_root ON sfx_tracks(library_root_id);
CREATE INDEX IF NOT EXISTS idx_sfx_tracks_category ON sfx_tracks(category_id);
CREATE INDEX IF NOT EXISTS idx_sfx_tracks_favorite ON sfx_tracks(is_favorite);
CREATE INDEX IF NOT EXISTS idx_sfx_tracks_missing ON sfx_tracks(is_missing);
CREATE INDEX IF NOT EXISTS idx_sfx_tracks_partial_hash ON sfx_tracks(partial_hash);

CREATE TABLE IF NOT EXISTS sfx_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS sfx_track_tags (
    track_id INTEGER NOT NULL REFERENCES sfx_tracks(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES sfx_tags(id) ON DELETE CASCADE,
    PRIMARY KEY (track_id, tag_id)
);
CREATE INDEX IF NOT EXISTS idx_sfx_track_tags_tag ON sfx_track_tags(tag_id);

CREATE TABLE IF NOT EXISTS sfx_packs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sfx_pack_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pack_id INTEGER NOT NULL REFERENCES sfx_packs(id) ON DELETE CASCADE,
    track_id INTEGER NOT NULL REFERENCES sfx_tracks(id) ON DELETE CASCADE,
    position INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sfx_pack_items_pack ON sfx_pack_items(pack_id);
CREATE INDEX IF NOT EXISTS idx_sfx_pack_items_track ON sfx_pack_items(track_id);

CREATE TABLE IF NOT EXISTS sfx_hotkeys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id INTEGER NOT NULL UNIQUE REFERENCES sfx_tracks(id) ON DELETE CASCADE,
    key TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS sfx_play_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id INTEGER NOT NULL REFERENCES sfx_tracks(id) ON DELETE CASCADE,
    played_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sfx_history_played_at ON sfx_play_history(played_at);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""
