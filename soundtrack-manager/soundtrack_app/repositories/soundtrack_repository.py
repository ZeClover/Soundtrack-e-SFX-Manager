"""Repositório de soundtracks (projetos), suas seções e itens.

Seções (item 28/etapa 3) são opcionais: uma soundtrack pode não ter nenhuma
(comportamento idêntico à etapa 2, lista plana) ou combinar itens soltos
("sem seção") com itens agrupados em seções nomeadas. A ordem de exibição
é: itens sem seção primeiro, depois cada seção (na sua própria posição),
e dentro de cada grupo os itens na sua própria posição.
"""

from __future__ import annotations

from datetime import datetime, timezone

from soundtrack_app.database import Database
from soundtrack_app.models import Soundtrack, SoundtrackItem, SoundtrackSection, Track


class SoundtrackRepository:
    def __init__(self, db: Database):
        self._db = db

    # ------------------------------------------------------------------
    # Soundtracks
    # ------------------------------------------------------------------

    def list_all(self) -> list[Soundtrack]:
        rows = self._db.query_all(
            """
            SELECT s.*, COUNT(si.id) AS track_count
            FROM soundtracks s
            LEFT JOIN soundtrack_items si ON si.soundtrack_id = s.id
            GROUP BY s.id
            ORDER BY s.updated_at DESC
            """
        )
        return [Soundtrack.from_row(row) for row in rows]

    def get(self, soundtrack_id: int) -> Soundtrack | None:
        row = self._db.query_one(
            """
            SELECT s.*, COUNT(si.id) AS track_count
            FROM soundtracks s
            LEFT JOIN soundtrack_items si ON si.soundtrack_id = s.id
            WHERE s.id = ?
            GROUP BY s.id
            """,
            (soundtrack_id,),
        )
        return Soundtrack.from_row(row) if row else None

    def create(self, name: str, campaign_id: int | None = None) -> Soundtrack:
        now = _now_iso()
        cursor = self._db.execute(
            "INSERT INTO soundtracks (name, campaign_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (name.strip(), campaign_id, now, now),
        )
        return Soundtrack(id=cursor.lastrowid, name=name.strip(), campaign_id=campaign_id,
                           created_at=now, updated_at=now, track_count=0)

    def rename(self, soundtrack_id: int, name: str) -> None:
        self._db.execute(
            "UPDATE soundtracks SET name = ?, updated_at = ? WHERE id = ?",
            (name.strip(), _now_iso(), soundtrack_id),
        )

    def delete(self, soundtrack_id: int) -> None:
        self._db.execute("DELETE FROM soundtracks WHERE id = ?", (soundtrack_id,))

    def touch(self, soundtrack_id: int) -> None:
        self._db.execute(
            "UPDATE soundtracks SET updated_at = ? WHERE id = ?", (_now_iso(), soundtrack_id)
        )

    # ------------------------------------------------------------------
    # Seções
    # ------------------------------------------------------------------

    def list_sections(self, soundtrack_id: int) -> list[SoundtrackSection]:
        rows = self._db.query_all(
            "SELECT id, soundtrack_id, name, position FROM soundtrack_sections "
            "WHERE soundtrack_id = ? ORDER BY position ASC",
            (soundtrack_id,),
        )
        return [
            SoundtrackSection(id=r["id"], soundtrack_id=r["soundtrack_id"], name=r["name"], position=r["position"])
            for r in rows
        ]

    def create_section(self, soundtrack_id: int, name: str) -> SoundtrackSection:
        row = self._db.query_one(
            "SELECT COALESCE(MAX(position), 0) AS max_pos FROM soundtrack_sections WHERE soundtrack_id = ?",
            (soundtrack_id,),
        )
        next_position = (row["max_pos"] if row else 0) + 1
        cursor = self._db.execute(
            "INSERT INTO soundtrack_sections (soundtrack_id, name, position) VALUES (?, ?, ?)",
            (soundtrack_id, name.strip(), next_position),
        )
        self.touch(soundtrack_id)
        return SoundtrackSection(id=cursor.lastrowid, soundtrack_id=soundtrack_id,
                                  name=name.strip(), position=next_position)

    def rename_section(self, section_id: int, name: str, soundtrack_id: int) -> None:
        self._db.execute("UPDATE soundtrack_sections SET name = ? WHERE id = ?", (name.strip(), section_id))
        self.touch(soundtrack_id)

    def delete_section(self, section_id: int, soundtrack_id: int) -> None:
        # ON DELETE SET NULL (schema) já reatribui os itens dessa seção para
        # "sem seção" automaticamente — nada é apagado, só desagrupado.
        self._db.execute("DELETE FROM soundtrack_sections WHERE id = ?", (section_id,))
        self.touch(soundtrack_id)

    def reorder_sections(self, soundtrack_id: int, ordered_section_ids: list[int]) -> None:
        with self._db.transaction() as conn:
            for position, section_id in enumerate(ordered_section_ids, start=1):
                conn.execute(
                    "UPDATE soundtrack_sections SET position = ? WHERE id = ? AND soundtrack_id = ?",
                    (position, section_id, soundtrack_id),
                )
            conn.execute(
                "UPDATE soundtracks SET updated_at = ? WHERE id = ?", (_now_iso(), soundtrack_id)
            )

    def move_section(self, soundtrack_id: int, section_id: int, direction: int) -> None:
        """Move uma seção uma posição para cima (direction=-1) ou para baixo (direction=+1)."""
        sections = self.list_sections(soundtrack_id)
        ids = [s.id for s in sections]
        if section_id not in ids:
            return
        index = ids.index(section_id)
        new_index = index + direction
        if new_index < 0 or new_index >= len(ids):
            return
        ids[index], ids[new_index] = ids[new_index], ids[index]
        self.reorder_sections(soundtrack_id, ids)

    def move_track_to_section(self, item_id: int, section_id: int | None, soundtrack_id: int) -> None:
        self._db.execute(
            "UPDATE soundtrack_items SET section_id = ? WHERE id = ?", (section_id, item_id)
        )
        self.touch(soundtrack_id)

    # ------------------------------------------------------------------
    # Itens
    # ------------------------------------------------------------------

    def get_items(self, soundtrack_id: int) -> list[SoundtrackItem]:
        # IMPORTANTE: "si.id" é renomeado para "item_id" porque "t.*" também
        # traz uma coluna "id" (tracks.id) — sem o alias, o dict resultante
        # (que é montado por nome de coluna) teria a segunda ocorrência de
        # "id" sobrescrevendo a primeira, fazendo o item da soundtrack
        # "herdar" o id da faixa (quebrando remover/mover/reordenar).
        rows = self._db.query_all(
            """
            SELECT si.id AS item_id, si.soundtrack_id, si.section_id, si.track_id, si.position,
                ss.position AS section_position,
                t.*,
                (SELECT GROUP_CONCAT(tg.name, char(31)) FROM track_tags tt
                    JOIN tags tg ON tg.id = tt.tag_id WHERE tt.track_id = t.id) AS tags,
                (SELECT GROUP_CONCAT(c.name, char(31)) FROM track_campaigns tc
                    JOIN campaigns c ON c.id = tc.campaign_id WHERE tc.track_id = t.id) AS campaigns,
                (SELECT COUNT(*) FROM soundtrack_items si2 WHERE si2.track_id = t.id) AS in_soundtrack_count
            FROM soundtrack_items si
            LEFT JOIN soundtrack_sections ss ON ss.id = si.section_id
            JOIN tracks t ON t.id = si.track_id
            WHERE si.soundtrack_id = ?
            ORDER BY (CASE WHEN si.section_id IS NULL THEN 0 ELSE 1 END), ss.position ASC, si.position ASC
            """,
            (soundtrack_id,),
        )
        items = []
        for row in rows:
            track = Track.from_row(row)
            items.append(
                SoundtrackItem(
                    id=row["item_id"],
                    soundtrack_id=row["soundtrack_id"],
                    section_id=row["section_id"],
                    track_id=row["track_id"],
                    position=row["position"],
                    track=track,
                )
            )
        return items

    def has_track(self, soundtrack_id: int, track_id: int) -> bool:
        row = self._db.query_one(
            "SELECT 1 FROM soundtrack_items WHERE soundtrack_id = ? AND track_id = ? LIMIT 1",
            (soundtrack_id, track_id),
        )
        return row is not None

    def add_track(self, soundtrack_id: int, track_id: int, section_id: int | None = None) -> SoundtrackItem:
        row = self._db.query_one(
            "SELECT COALESCE(MAX(position), 0) AS max_pos FROM soundtrack_items WHERE soundtrack_id = ?",
            (soundtrack_id,),
        )
        next_position = (row["max_pos"] if row else 0) + 1
        cursor = self._db.execute(
            "INSERT INTO soundtrack_items (soundtrack_id, section_id, track_id, position) "
            "VALUES (?, ?, ?, ?)",
            (soundtrack_id, section_id, track_id, next_position),
        )
        self.touch(soundtrack_id)
        return SoundtrackItem(
            id=cursor.lastrowid, soundtrack_id=soundtrack_id, section_id=section_id,
            track_id=track_id, position=next_position,
        )

    def remove_item(self, item_id: int, soundtrack_id: int) -> None:
        self._db.execute("DELETE FROM soundtrack_items WHERE id = ?", (item_id,))
        self.touch(soundtrack_id)

    def reorder(self, soundtrack_id: int, ordered_item_ids: list[int]) -> None:
        """Reaplica a posição (1..N) de acordo com a ordem informada, sem alterar seção.

        Usado quando a soundtrack não tem seções (equivalente à etapa 2).
        """
        with self._db.transaction() as conn:
            for position, item_id in enumerate(ordered_item_ids, start=1):
                conn.execute(
                    "UPDATE soundtrack_items SET position = ? WHERE id = ? AND soundtrack_id = ?",
                    (position, item_id, soundtrack_id),
                )
            conn.execute(
                "UPDATE soundtracks SET updated_at = ? WHERE id = ?", (_now_iso(), soundtrack_id)
            )

    def reorder_with_sections(self, soundtrack_id: int, ordered: list[tuple[int, int | None]]) -> None:
        """Reaplica seção e posição de cada item a partir da ORDEM DE EXIBIÇÃO completa.

        ``ordered`` é a lista completa de itens da soundtrack, na nova ordem
        visual desejada, como pares ``(item_id, section_id)`` — usado tanto
        para reordenar dentro do mesmo grupo quanto para mover um item para
        outro grupo (ex.: arrastar uma faixa para debaixo de outro cabeçalho
        de seção reatribui a seção E a posição em uma única operação).
        """
        with self._db.transaction() as conn:
            for position, (item_id, section_id) in enumerate(ordered, start=1):
                conn.execute(
                    "UPDATE soundtrack_items SET section_id = ?, position = ? "
                    "WHERE id = ? AND soundtrack_id = ?",
                    (section_id, position, item_id, soundtrack_id),
                )
            conn.execute(
                "UPDATE soundtracks SET updated_at = ? WHERE id = ?", (_now_iso(), soundtrack_id)
            )

    def move_item(self, soundtrack_id: int, item_id: int, direction: int) -> None:
        """Move um item uma posição para cima (direction=-1) ou para baixo (direction=+1).

        Opera sobre a ORDEM DE EXIBIÇÃO (que já leva seções em conta), então
        mover um item para além do limite do seu grupo o transfere para o
        grupo vizinho — consistente com o que acontece ao arrastar.
        """
        items = self.get_items(soundtrack_id)
        ids = [item.id for item in items]
        if item_id not in ids:
            return
        index = ids.index(item_id)
        new_index = index + direction
        if new_index < 0 or new_index >= len(ids):
            return

        pairs = [(item.id, item.section_id) for item in items]
        moved_item = pairs.pop(index)

        # O item assume a seção de quem ficará imediatamente antes dele na
        # nova posição (ou a do primeiro item, se for para o topo da lista).
        # É assim que "mover para cima/baixo" cruza um limite de seção.
        if new_index > 0:
            target_section = pairs[new_index - 1][1]
        elif pairs:
            target_section = pairs[0][1]
        else:
            target_section = moved_item[1]

        pairs.insert(new_index, (moved_item[0], target_section))
        self.reorder_with_sections(soundtrack_id, pairs)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
