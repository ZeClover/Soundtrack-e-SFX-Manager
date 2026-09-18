"""Scanner de biblioteca de músicas, rodando em uma QThread separada.

Requisitos atendidos (ver especificação):
- Nunca trava a UI: todo o trabalho de I/O roda em uma thread própria e só
  se comunica com a UI via signals/slots (nunca manipulando widgets
  diretamente).
- Não duplica, não move, não renomeia os arquivos originais — apenas lê.
- Detecta arquivos novos, removidos e não reprocessa metadados de arquivos
  já conhecidos (rescan rápido).
- Um arquivo problemático não interrompe o restante do escaneamento; o erro
  é coletado e reportado no resumo final.
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

from soundtrack_app.database import Database
from soundtrack_app.repositories import LibraryRootRepository, TrackRepository

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
    """Escaneia recursivamente uma pasta em busca de arquivos de áudio."""

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
            track_repo = TrackRepository(self._database)
            root_id = library_root_repo.get_or_create(str(self._root_path))

            errors: list[str] = []
            files = self._collect_audio_files(errors)
            total = len(files)

            existing_paths = self._existing_paths(root_id)
            seen_paths: set[str] = set()
            new_count = 0
            last_emit = 0.0

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
                    self._process_new_file(track_repo, root_id, file_path)
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
            "SELECT absolute_path FROM tracks WHERE library_root_id = ?", (root_id,)
        )
        return {row["absolute_path"] for row in rows}

    def _process_new_file(self, track_repo: TrackRepository, root_id: int, file_path: Path) -> None:
        metadata = read_audio_metadata(file_path)
        stat = file_path.stat()
        file_hash = partial_hash(file_path)
        relative = file_path.relative_to(self._root_path)

        track_repo.upsert_from_scan(
            library_root_id=root_id,
            absolute_path=str(file_path),
            relative_path=str(relative),
            filename=file_path.name,
            extension=file_path.suffix.lower(),
            title=metadata.title,
            artist=metadata.artist,
            album=metadata.album,
            duration_seconds=metadata.duration_seconds,
            file_size=stat.st_size,
            partial_hash=file_hash,
            has_embedded_cover=metadata.has_embedded_cover,
        )
