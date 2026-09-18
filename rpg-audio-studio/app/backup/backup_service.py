"""Backup/Restauração do RPG Audio Studio (item 27).

Inclui os bancos SQLite dos três módulos (que já guardam tags, soundtracks,
packs, histórico e configurações) e os pequenos arquivos auxiliares do
Downloader. NUNCA inclui arquivos de áudio — só o que é pequeno e realmente
"dados do usuário sobre a música/efeito", não a mídia em si.

Os bancos são copiados com a API de backup a quente do próprio sqlite3
(``Connection.backup``), que gera uma cópia consistente mesmo que o banco
esteja em uso (WAL) — bem mais seguro que copiar o arquivo cru.
"""

from __future__ import annotations

import json
import sqlite3
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from rpg_audio_shared.app_dirs import app_data_dir

_MANIFEST_NAME = "manifest.json"
_BACKUP_FORMAT_VERSION = 1


@dataclass(frozen=True)
class BackupSource:
    label: str
    path: Path
    archive_name: str
    is_sqlite: bool = True


def default_sources() -> list[BackupSource]:
    downloader_dir = app_data_dir("rpg-audio-studio") / "downloader"
    return [
        BackupSource(
            "Biblioteca de músicas (Soundtrack Manager)",
            app_data_dir("soundtrack-manager") / "soundtrack_manager.db",
            "soundtrack_manager.db",
        ),
        BackupSource(
            "Biblioteca de SFX (SFX Manager)", app_data_dir("sfx-manager") / "sfx_manager.db", "sfx_manager.db"
        ),
        BackupSource(
            "Configurações do Studio", app_data_dir("rpg-audio-studio") / "studio_settings.db", "studio_settings.db"
        ),
        BackupSource(
            "Registro de downloads já feitos",
            downloader_dir / "download_archive.txt",
            "downloader_archive.txt",
            is_sqlite=False,
        ),
        BackupSource(
            "Downloads recentes", downloader_dir / "recent_downloads.json", "downloader_recent_downloads.json",
            is_sqlite=False,
        ),
    ]


@dataclass
class BackupResult:
    zip_path: Path
    included: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


@dataclass
class RestoreResult:
    restored: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def create_backup(zip_path: Path, sources: list[BackupSource] | None = None) -> BackupResult:
    sources = sources if sources is not None else default_sources()
    result = BackupResult(zip_path=zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    with TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        manifest = {
            "format_version": _BACKUP_FORMAT_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "files": [],
        }

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for source in sources:
                if not source.path.exists():
                    result.skipped.append(source.label)
                    continue

                if source.is_sqlite:
                    snapshot_path = tmp_dir / source.archive_name
                    _hot_backup_sqlite(source.path, snapshot_path)
                    zf.write(snapshot_path, source.archive_name)
                else:
                    zf.write(source.path, source.archive_name)

                manifest["files"].append({"label": source.label, "archive_name": source.archive_name})
                result.included.append(source.label)

            zf.writestr(_MANIFEST_NAME, json.dumps(manifest, ensure_ascii=False, indent=2))

    return result


def restore_backup(zip_path: Path, sources: list[BackupSource] | None = None) -> RestoreResult:
    sources = sources if sources is not None else default_sources()
    by_archive_name = {source.archive_name: source for source in sources}
    result = RestoreResult()

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())
        for archive_name, source in by_archive_name.items():
            if archive_name not in names:
                result.skipped.append(source.label)
                continue

            source.path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(archive_name) as member, source.path.open("wb") as target:
                target.write(member.read())

            if source.is_sqlite:
                # Sidecars de WAL antigos não podem ficar por perto de um
                # banco recém-restaurado — misturariam dados velhos e novos.
                for suffix in ("-wal", "-shm"):
                    sidecar = source.path.with_name(source.path.name + suffix)
                    if sidecar.exists():
                        sidecar.unlink()

            result.restored.append(source.label)

    return result


def _hot_backup_sqlite(source_path: Path, destination_path: Path) -> None:
    source_conn = sqlite3.connect(str(source_path))
    try:
        dest_conn = sqlite3.connect(str(destination_path))
        try:
            source_conn.backup(dest_conn)
        finally:
            dest_conn.close()
    finally:
        source_conn.close()
