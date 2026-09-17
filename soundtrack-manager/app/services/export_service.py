"""Exportação de soundtracks para uma pasta de destino.

Regra fundamental (item 59 da especificação): os arquivos originais NUNCA
são apagados, movidos ou renomeados. A exportação sempre COPIA os arquivos
para a pasta de destino escolhida pelo usuário.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from rpg_audio_shared.paths import ensure_directory, numbered_filename, sanitize_filename, unique_path

from app.models import SoundtrackItem, SoundtrackSection

logger = logging.getLogger(__name__)

ConflictPolicy = Literal["overwrite", "skip", "rename"]
SectionMode = Literal["flat", "subfolders"]

_BITRATE_BY_QUALITY = {
    "alta": "320k",
    "media": "192k",
    "economica": "128k",
}


@dataclass(slots=True)
class ExportOptions:
    destination_folder: Path
    numbering: bool = True
    convert_to_mp3: bool = False
    mp3_quality: str = "media"  # alta | media | economica
    conflict_policy: ConflictPolicy = "rename"
    # Item 32: só relevante quando a soundtrack tem seções.
    # "flat" = tudo na mesma pasta (numeração única, já respeitando a ordem
    # por seção); "subfolders" = uma subpasta por seção (numeração reinicia
    # em cada uma). Faixas sem seção sempre ficam na pasta raiz da exportação.
    section_mode: SectionMode = "flat"


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
    def export_soundtrack(
        self,
        soundtrack_name: str,
        items: list[SoundtrackItem],
        options: ExportOptions,
        sections: list[SoundtrackSection] | None = None,
    ) -> ExportReport:
        folder_name = f"{sanitize_filename(soundtrack_name)} - Soundtrack"
        destination = ensure_directory(options.destination_folder / folder_name)
        report = ExportReport(destination=destination)

        if options.section_mode == "subfolders" and sections:
            for section_name, group_items in _group_by_section(items, sections):
                target_dir = (
                    destination if section_name is None
                    else ensure_directory(destination / sanitize_filename(section_name))
                )
                self._export_items(group_items, target_dir, options, report)
        else:
            # "flat": tudo na mesma pasta, mas a ordem de "items" já respeita
            # o agrupamento por seção (ver SoundtrackRepository.get_items).
            self._export_items(items, destination, options, report)

        return report

    def _export_items(
        self, items: list[SoundtrackItem], target_dir: Path, options: ExportOptions, report: ExportReport
    ) -> None:
        for index, item in enumerate(items, start=1):
            track = item.track
            if track is None:
                continue

            source = Path(track.absolute_path)
            if not source.exists():
                report.errors.append(f"Arquivo não encontrado: {track.title} ({track.absolute_path})")
                continue

            will_convert = options.convert_to_mp3 and source.suffix.lower() != ".mp3"
            target_suffix = ".mp3" if options.convert_to_mp3 else source.suffix

            if options.numbering:
                filename = numbered_filename(index, track.title, target_suffix)
            else:
                filename = f"{sanitize_filename(track.title)}{target_suffix}"

            target = target_dir / filename

            if target.exists():
                if options.conflict_policy == "skip":
                    report.skipped_count += 1
                    continue
                if options.conflict_policy == "rename":
                    target = unique_path(target)
                # "overwrite" apenas segue em frente e sobrescreve

            try:
                if will_convert:
                    _convert_to_mp3(source, target, options.mp3_quality)
                else:
                    shutil.copy2(source, target)
            except Exception as exc:  # noqa: BLE001 - um erro não pode interromper a exportação
                logger.warning("Falha ao exportar %s", source, exc_info=True)
                report.errors.append(f"{track.title}: {exc}")
                continue

            report.exported_count += 1
            report.total_bytes += target.stat().st_size


def _group_by_section(
    items: list[SoundtrackItem], sections: list[SoundtrackSection]
) -> list[tuple[str | None, list[SoundtrackItem]]]:
    """Particiona ``items`` (já ordenados: sem seção, depois cada seção) em
    grupos contíguos ``(nome_da_seção_ou_None, itens)``, na mesma ordem."""
    section_name_by_id = {s.id: s.name for s in sections}
    groups: list[tuple[str | None, list[SoundtrackItem]]] = []
    current_section_id: int | None | object = _NO_GROUP_YET
    current_items: list[SoundtrackItem] = []

    for item in items:
        if item.section_id != current_section_id:
            if current_items:
                groups.append((section_name_by_id.get(current_section_id), current_items))
            current_section_id = item.section_id
            current_items = []
        current_items.append(item)

    if current_items:
        groups.append((section_name_by_id.get(current_section_id), current_items))

    return groups


_NO_GROUP_YET = object()


def _convert_to_mp3(source: Path, target: Path, quality: str) -> None:
    bitrate = _BITRATE_BY_QUALITY.get(quality, "192k")
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(source),
                "-codec:a", "libmp3lame", "-b:a", bitrate,
                str(target),
            ],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "FFmpeg não foi encontrado. Instale o FFmpeg e adicione-o ao PATH do "
            "Windows para poder converter para MP3, ou use \"Manter formato original\"."
        ) from exc

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou ao converter: {result.stderr.strip()[-300:]}")
