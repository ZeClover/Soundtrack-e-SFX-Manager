"""Testes do backup/restauração (item 27) — nunca deve incluir arquivos de
áudio, deve preservar dados dos bancos, e restaurar deve trazer os valores
de volta exatamente como estavam."""

from __future__ import annotations

import sqlite3
import zipfile
from pathlib import Path

from app.backup.backup_service import BackupSource, create_backup, restore_backup


def _make_sqlite_db(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO settings (key, value) VALUES ('marker', ?)", (value,))
    conn.commit()
    conn.close()


def _read_marker(path: Path) -> str:
    conn = sqlite3.connect(str(path))
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = 'marker'").fetchone()
        return row[0]
    finally:
        conn.close()


def test_backup_includes_existing_sqlite_sources(tmp_path: Path):
    db_path = tmp_path / "data" / "app.db"
    _make_sqlite_db(db_path, "hello")

    sources = [BackupSource("Teste", db_path, "app.db")]
    zip_path = tmp_path / "backup.zip"
    result = create_backup(zip_path, sources=sources)

    assert result.included == ["Teste"]
    assert result.skipped == []
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "app.db" in names
        assert "manifest.json" in names


def test_backup_skips_sources_that_do_not_exist_yet(tmp_path: Path):
    sources = [BackupSource("Nunca usado", tmp_path / "missing.db", "missing.db")]
    zip_path = tmp_path / "backup.zip"
    result = create_backup(zip_path, sources=sources)

    assert result.included == []
    assert result.skipped == ["Nunca usado"]
    with zipfile.ZipFile(zip_path) as zf:
        assert "missing.db" not in zf.namelist()


def test_backup_never_includes_audio_files(tmp_path: Path):
    db_path = tmp_path / "data" / "app.db"
    _make_sqlite_db(db_path, "x")
    audio_file = tmp_path / "data" / "musica.mp3"
    audio_file.write_bytes(b"fake audio bytes")

    sources = [BackupSource("Teste", db_path, "app.db")]
    zip_path = tmp_path / "backup.zip"
    create_backup(zip_path, sources=sources)

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert not any(name.endswith(".mp3") for name in names)


def test_backup_and_restore_roundtrip_preserves_data(tmp_path: Path):
    original_path = tmp_path / "original" / "app.db"
    _make_sqlite_db(original_path, "valor original")

    zip_path = tmp_path / "backup.zip"
    sources = [BackupSource("Teste", original_path, "app.db")]
    create_backup(zip_path, sources=sources)

    # simula "perder" o banco (como se o usuário tivesse reinstalado)
    restored_path = tmp_path / "restored" / "app.db"
    restore_sources = [BackupSource("Teste", restored_path, "app.db")]
    result = restore_backup(zip_path, sources=restore_sources)

    assert result.restored == ["Teste"]
    assert _read_marker(restored_path) == "valor original"


def test_restore_reports_missing_entries_in_the_zip(tmp_path: Path):
    zip_path = tmp_path / "empty_backup.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("manifest.json", "{}")

    sources = [BackupSource("Teste", tmp_path / "restored.db", "app.db")]
    result = restore_backup(zip_path, sources=sources)

    assert result.restored == []
    assert result.skipped == ["Teste"]


def test_restore_removes_stale_wal_sidecars(tmp_path: Path):
    original_path = tmp_path / "original" / "app.db"
    _make_sqlite_db(original_path, "novo valor")
    zip_path = tmp_path / "backup.zip"
    create_backup(zip_path, sources=[BackupSource("Teste", original_path, "app.db")])

    restored_path = tmp_path / "restored" / "app.db"
    restored_path.parent.mkdir(parents=True)
    (restored_path.parent / "app.db-wal").write_bytes(b"dado velho de wal")
    (restored_path.parent / "app.db-shm").write_bytes(b"dado velho de shm")
    restored_path.write_bytes(b"banco velho")

    restore_backup(zip_path, sources=[BackupSource("Teste", restored_path, "app.db")])

    assert not (restored_path.parent / "app.db-wal").exists()
    assert not (restored_path.parent / "app.db-shm").exists()
    assert _read_marker(restored_path) == "novo valor"


def test_backup_of_hot_open_database_is_consistent(tmp_path: Path):
    """A conexão de origem continua aberta (como aconteceria com o app
    rodando) — o backup ainda tem que ficar consistente."""
    db_path = tmp_path / "data" / "app.db"
    db_path.parent.mkdir(parents=True)
    live_conn = sqlite3.connect(str(db_path))
    try:
        live_conn.execute("PRAGMA journal_mode = WAL")
        live_conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
        live_conn.execute("INSERT INTO settings (key, value) VALUES ('marker', 'ao_vivo')")
        live_conn.commit()

        zip_path = tmp_path / "backup.zip"
        create_backup(zip_path, sources=[BackupSource("Teste", db_path, "app.db")])
    finally:
        live_conn.close()

    restored_path = tmp_path / "restored" / "app.db"
    restore_backup(zip_path, sources=[BackupSource("Teste", restored_path, "app.db")])
    assert _read_marker(restored_path) == "ao_vivo"


def test_non_sqlite_sources_are_copied_verbatim(tmp_path: Path):
    text_file = tmp_path / "archive.txt"
    text_file.write_text("id1\nid2\n", encoding="utf-8")

    zip_path = tmp_path / "backup.zip"
    sources = [BackupSource("Archive", text_file, "archive.txt", is_sqlite=False)]
    create_backup(zip_path, sources=sources)

    restored = tmp_path / "restored_archive.txt"
    restore_backup(zip_path, sources=[BackupSource("Archive", restored, "archive.txt", is_sqlite=False)])
    assert restored.read_text(encoding="utf-8") == "id1\nid2\n"
