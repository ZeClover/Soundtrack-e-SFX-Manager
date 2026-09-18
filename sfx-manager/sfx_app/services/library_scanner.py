"""Scanner de biblioteca de SFX, rodando em uma QThread separada.

Segue o mesmo padrão do Soundtrack Manager (ver item 50 da especificação):
nunca trava a UI, nunca duplica/move/renomeia arquivos, não reprocessa
metadados de arquivos já conhecidos e um arquivo problemático não
interrompe o restante do escaneamento.

Diferença específica do SFX Manager (item 37): a subpasta imediata de cada
arquivo vira sua categoria automaticamente (ex.: ``SFX/Espadas/golpe.wav``
→ categoria "Espadas"). Arquivos direto na raiz da biblioteca ficam sem
categoria.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from rpg_audio_shared.audio_meta import read_audio_metadata
from rpg_audio_shared.formats import is_supported_audio_file
from rpg_audio_shared.hashing import partial_hash

from sfx_app.database import Database
from sfx_app.repositories import CategoryRepository, LibraryRootRepository, SfxTrackRepository

logger = logging.getLogger(__name__)

_PROGRESS_MIN_INTERVAL = 0.05  # segundos entre atualizações de progresso na UI


@dataclass(slots=True)
class ScanResult:
    library_root_id: int
    total_files_found: int
    new_tracks: int
    missing_tracks: int
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


class LibraryScanner(QThread):
    """Escaneia recursivamente uma pasta em busca de efeitos sonoros."""

    progress = Signal(int, int, str)  # processados, total, nome do arquivo atual
    scan_finished = Signal(object)  # ScanResult
    scan_failed = Signal(str)

    def __init__(self, database: Database, root_path: Path, parent=None):
        super().__init__(parent)
        self._database = database
        self._root_path = Path(root_path)
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        start = time.monotonic()
        try:
            if not self._root_path.is_dir():
                self.scan_failed.emit(f"A pasta '{self._root_path}' não foi encontrada.")
                return

            library_root_repo = LibraryRootRepository(self._database)
            track_repo = SfxTrackRepository(self._database)
            category_repo = CategoryRepository(self._database)
            root_id = library_root_repo.get_or_create(str(self._root_path))

            errors: list[str] = []
            files = self._collect_audio_files(errors)
            total = len(files)

            existing_paths = self._existing_paths(root_id)
            seen_paths: set[str] = set()
            new_count = 0
            last_emit = 0.0
            category_cache: dict[str, int] = {}

            for index, file_path in enumerate(files, start=1):
                if self._cancelled:
                    break

                absolute = str(file_path)
                seen_paths.add(absolute)

                now = time.monotonic()
                should_emit = (
                    now - last_emit >= _PROGRESS_MIN_INTERVAL or index == total or index == 1
                )
                if should_emit:
                    self.progress.emit(index, total, file_path.name)
                    last_emit = now

                if absolute in existing_paths:
                    continue  # já conhecido: não relê metadados (rescan rápido)

                try:
                    self._process_new_file(track_repo, category_repo, category_cache, root_id, file_path)
                    new_count += 1
                except Exception as exc:  # noqa: BLE001 - um arquivo ruim não pode parar o scan
                    logger.warning("Falha ao processar %s", file_path, exc_info=True)
                    errors.append(f"{file_path.name}: {exc}")

            missing_count = 0
            if not self._cancelled:
                missing_count = track_repo.mark_missing(root_id, seen_paths)
                library_root_repo.touch_scanned(root_id)

            result = ScanResult(
                library_root_id=root_id,
                total_files_found=total,
                new_tracks=new_count,
                missing_tracks=missing_count,
                errors=errors,
                duration_seconds=time.monotonic() - start,
            )
            self.scan_finished.emit(result)
        except Exception as exc:  # noqa: BLE001 - falha inesperada e fatal do scan
            logger.exception("Erro fatal durante o escaneamento")
            self.scan_failed.emit(str(exc))

    # ------------------------------------------------------------------

    def _collect_audio_files(self, errors: list[str]) -> list[Path]:
        files: list[Path] = []
        try:
            for entry in self._root_path.rglob("*"):
                if self._cancelled:
                    break
                try:
                    if entry.is_file() and is_supported_audio_file(entry):
                        files.append(entry)
                except OSError as exc:
                    errors.append(f"{entry}: {exc}")
        except OSError as exc:
            errors.append(f"{self._root_path}: {exc}")
        return files

    def _existing_paths(self, root_id: int) -> set[str]:
        rows = self._database.query_all(
            "SELECT absolute_path FROM sfx_tracks WHERE library_root_id = ?", (root_id,)
        )
        return {row["absolute_path"] for row in rows}

    def _category_id_for(
        self, category_repo: CategoryRepository, cache: dict[str, int], file_path: Path
    ) -> int | None:
        relative = file_path.relative_to(self._root_path)
        if len(relative.parts) < 2:
            return None  # arquivo direto na raiz, sem subpasta
        category_name = relative.parts[0]
        if category_name not in cache:
            cache[category_name] = category_repo.get_or_create(category_name).id
        return cache[category_name]

    def _process_new_file(
        self,
        track_repo: SfxTrackRepository,
        category_repo: CategoryRepository,
        category_cache: dict[str, int],
        root_id: int,
        file_path: Path,
    ) -> None:
        metadata = read_audio_metadata(file_path)
        stat = file_path.stat()
        file_hash = partial_hash(file_path)
        relative = file_path.relative_to(self._root_path)
        category_id = self._category_id_for(category_repo, category_cache, file_path)

        track_repo.upsert_from_scan(
            library_root_id=root_id,
            category_id=category_id,
            absolute_path=str(file_path),
            relative_path=str(relative),
            filename=file_path.name,
            extension=file_path.suffix.lower(),
            title=metadata.title,
            duration_seconds=metadata.duration_seconds,
            file_size=stat.st_size,
            partial_hash=file_hash,
        )
