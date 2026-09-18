"""Navegação pura (sem Qt) de uma lista de reprodução atual.

Separado do :class:`~app.services.player_service.PlayerService` para poder
ser testado sem depender de um backend de áudio real — a lógica de "qual é
a próxima faixa" é a parte que realmente importa cobrir com testes; os
botões em si (item 64 da especificação) não precisam.
"""

from __future__ import annotations

from soundtrack_app.models import Track


class PlaylistCursor:
    def __init__(self) -> None:
        self._items: list[Track] = []
        self._index: int = -1

    @property
    def items(self) -> list[Track]:
        return list(self._items)

    @property
    def index(self) -> int:
        return self._index

    def set_items(self, items: list[Track], start_index: int = 0) -> Track | None:
        self._items = list(items)
        if not self._items:
            self._index = -1
            return None
        self._index = max(0, min(start_index, len(self._items) - 1))
        return self.current()

    def current(self) -> Track | None:
        if 0 <= self._index < len(self._items):
            return self._items[self._index]
        return None

    @property
    def has_next(self) -> bool:
        return 0 <= self._index < len(self._items) - 1

    @property
    def has_previous(self) -> bool:
        return self._index > 0

    def next(self) -> Track | None:
        if not self.has_next:
            return None
        self._index += 1
        return self.current()

    def previous(self) -> Track | None:
        if not self.has_previous:
            return None
        self._index -= 1
        return self.current()

    def jump_to_track_id(self, track_id: int) -> Track | None:
        for i, track in enumerate(self._items):
            if track.id == track_id:
                self._index = i
                return track
        return None

    def remove_track_id(self, track_id: int) -> None:
        """Remove uma faixa da lista atual (ex.: arquivo ficou ausente), ajustando o índice."""
        for i, track in enumerate(self._items):
            if track.id == track_id:
                del self._items[i]
                if i < self._index or (i == self._index and i == len(self._items)):
                    self._index -= 1
                break
