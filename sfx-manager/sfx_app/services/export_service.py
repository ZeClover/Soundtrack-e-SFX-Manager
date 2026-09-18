"""Exportação de packs de SFX para uma pasta de destino (item 46).

Regra fundamental (item 59): os arquivos originais nunca são apagados,
movidos ou renomeados — a exportação sempre COPIA para a pasta escolhida.
Mais simples que a exportação de soundtrack: sem seções, sem numeração
(os nomes de efeitos já são o que importa num pack).
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from rpg_audio_shared.paths import ensure_directory, sanitize_filename, unique_path

from sfx_app.models import SfxPackItem

logger = logging.getLogger(__name__)

ConflictPolicy = Literal["overwrite", "skip", "rename"]
ExportFormat = Literal["keep", "wav", "mp3"]


@dataclass(slots=True)
class ExportOptions:
    destination_folder: Path
    export_format: ExportFormat = "keep"
    conflict_policy: ConflictPolicy = "rename"


@dataclass(slots=True)
class ExportReport:
    destination: Path
    exported_count: int = 0
    skipped_count: int = 0
    total_bytes: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


class ExportService:
    def export_pack(self, pack_name: str, items: list[SfxPackItem], options: ExportOptions) -> ExportReport:
        folder_name = f"{sanitize_filename(pack_name)} SFX"
        destination = ensure_directory(options.destination_folder / folder_name)
        report = ExportReport(destination=destination)

        for item in items:
            track = item.track
            if track is None:
                continue

            source = Path(track.absolute_path)
            if not source.exists():
                report.errors.append(f"Arquivo não encontrado: {track.title} ({track.absolute_path})")
                continue

            target_format = options.export_format
            will_convert = target_format != "keep" and source.suffix.lower() != f".{target_format}"
            target_suffix = f".{target_format}" if target_format != "keep" else source.suffix

            filename = f"{sanitize_filename(track.title)}{target_suffix}"
            target = destination / filename

            if target.exists():
                if options.conflict_policy == "skip":
                    report.skipped_count += 1
                    continue
                if options.conflict_policy == "rename":
                    target = unique_path(target)

            try:
                if will_convert:
                    _convert_audio(source, target, target_format)
                else:
                    shutil.copy2(source, target)
            except Exception as exc:  # noqa: BLE001 - um erro não pode interromper a exportação
                logger.warning("Falha ao exportar %s", source, exc_info=True)
                report.errors.append(f"{track.title}: {exc}")
                continue

            report.exported_count += 1
            report.total_bytes += target.stat().st_size

        return report


def _convert_audio(source: Path, target: Path, target_format: str) -> None:
    codec = "libmp3lame" if target_format == "mp3" else "pcm_s16le"
    args = ["ffmpeg", "-y", "-i", str(source), "-codec:a", codec]
    if target_format == "mp3":
        args += ["-b:a", "192k"]
    args.append(str(target))

    try:
        result = subprocess.run(args, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "FFmpeg não foi encontrado. Instale o FFmpeg e adicione-o ao PATH do "
            "Windows para converter formato, ou use \"Manter formato original\"."
        ) from exc

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou ao converter: {result.stderr.strip()[-300:]}")
