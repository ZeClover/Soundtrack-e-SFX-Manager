"""Escolha de uma música aleatória (item 69), evitando repetição imediata.

Separado em um módulo puro (sem Qt) para ser fácil de testar: a função só
recebe a lista de músicas atualmente visíveis (já filtrada pela UI) e os
ids tocados recentemente por este botão.
"""

from __future__ import annotations

import random

from soundtrack_app.models import Track


def pick_random_track(tracks: list[Track], recent_ids: list[int]) -> Track | None:
    """Escolhe uma faixa aleatória entre ``tracks``, evitando ``recent_ids`` quando possível.

    Se todas as faixas disponíveis já estiverem em ``recent_ids`` (biblioteca/
    filtro muito pequeno), cai de volta para sortear entre todas mesmo assim
    — nunca retorna None só porque a faixa "óbvia" já tocou, a menos que a
    lista de faixas esteja vazia.
    """
    if not tracks:
        return None

    candidates = [t for t in tracks if t.id not in recent_ids]
    if not candidates:
        candidates = tracks

    return random.choice(candidates)
