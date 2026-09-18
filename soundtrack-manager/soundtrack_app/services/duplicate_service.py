"""Detector de duplicados (item 47).

Nunca apaga nada sozinho — só identifica e classifica em dois grupos:

- "confirmado": o conteúdo dos arquivos é byte-a-byte idêntico (hash
  completo). Só é calculado para faixas que já compartilham o hash parcial
  barato + tamanho salvos no escaneamento, para não precisar reler a
  biblioteca inteira toda vez que o usuário pedir para procurar duplicados.
- "possível": título normalizado igual, ou mesmo tamanho+duração — sinais
  fortes, mas não uma prova (pode ser uma faixa diferente com nome igual,
  ou o mesmo áudio em outro bitrate).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rpg_audio_shared.hashing import full_hash

from soundtrack_app.models import Track

DuplicateKind = Literal["confirmed", "possible"]


@dataclass(slots=True)
class DuplicateGroup:
    kind: DuplicateKind
    tracks: list[Track]


class DuplicateService:
    def find_duplicates(self, tracks: list[Track]) -> list[DuplicateGroup]:
        groups: list[DuplicateGroup] = []
        confirmed_ids: set[int] = set()

        for full_group in self._confirmed_groups(tracks):
            groups.append(DuplicateGroup(kind="confirmed", tracks=full_group))
            confirmed_ids.update(t.id for t in full_group)

        remaining = [t for t in tracks if t.id not in confirmed_ids]
        for cluster in self._possible_groups(remaining):
            groups.append(DuplicateGroup(kind="possible", tracks=cluster))

        return groups

    def _confirmed_groups(self, tracks: list[Track]) -> list[list[Track]]:
        by_partial: dict[tuple[str, int], list[Track]] = {}
        for t in tracks:
            if not t.partial_hash or t.is_missing:
                continue
            by_partial.setdefault((t.partial_hash, t.file_size), []).append(t)

        confirmed: list[list[Track]] = []
        for candidates in by_partial.values():
            if len(candidates) < 2:
                continue
            by_full: dict[str, list[Track]] = {}
            for t in candidates:
                path = Path(t.absolute_path)
                if not path.exists():
                    continue
                try:
                    digest = full_hash(path)
                except OSError:
                    continue
                by_full.setdefault(digest, []).append(t)
            for full_group in by_full.values():
                if len(full_group) >= 2:
                    confirmed.append(full_group)
        return confirmed

    def _possible_groups(self, tracks: list[Track]) -> list[list[Track]]:
        parent = {t.id: t.id for t in tracks}

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        by_title: dict[str, list[int]] = {}
        by_size_duration: dict[tuple[int, int], list[int]] = {}
        for t in tracks:
            by_title.setdefault(_normalize_title(t.title), []).append(t.id)
            by_size_duration.setdefault((t.file_size, round(t.duration_seconds)), []).append(t.id)

        for ids in by_title.values():
            for other in ids[1:]:
                union(ids[0], other)
        for ids in by_size_duration.values():
            for other in ids[1:]:
                union(ids[0], other)

        clusters: dict[int, list[Track]] = {}
        for t in tracks:
            clusters.setdefault(find(t.id), []).append(t)

        return [cluster for cluster in clusters.values() if len(cluster) >= 2]


def _normalize_title(title: str) -> str:
    return " ".join(title.strip().lower().split())
