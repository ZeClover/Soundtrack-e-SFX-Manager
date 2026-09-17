"""Testes de seções de soundtrack (etapa 3, item 5).

Cobrem: criar/renomear/remover seção, reordenar seções, mover faixas entre
seções, e a garantia de que uma soundtrack sem nenhuma seção continua se
comportando exatamente como na etapa 2 (lista plana).
"""

from __future__ import annotations


def _add(soundtrack_repo, track_repo, library_root_repo, titles: list[str]) -> dict[str, int]:
    root_id = library_root_repo.get_or_create("/library")
    ids = {}
    for title in titles:
        ids[title] = track_repo.upsert_from_scan(
            library_root_id=root_id, absolute_path=f"/library/{title}.mp3",
            relative_path=f"{title}.mp3", filename=f"{title}.mp3", extension=".mp3",
            title=title, artist=None, album=None, duration_seconds=10, file_size=100,
            partial_hash=title, has_embedded_cover=False,
        )
    return ids


def test_soundtrack_without_sections_behaves_like_flat_list(soundtrack_repo, track_repo, library_root_repo):
    ids = _add(soundtrack_repo, track_repo, library_root_repo, ["A", "B", "C"])
    st = soundtrack_repo.create("Sem Secoes")
    for title in ["A", "B", "C"]:
        soundtrack_repo.add_track(st.id, ids[title])

    items = soundtrack_repo.get_items(st.id)
    assert [i.track.title for i in items] == ["A", "B", "C"]
    assert all(i.section_id is None for i in items)
    assert soundtrack_repo.list_sections(st.id) == []


def test_create_rename_delete_section(soundtrack_repo, sample_track_id):
    st = soundtrack_repo.create("Darkrem")
    section = soundtrack_repo.create_section(st.id, "Combate")
    assert section.name == "Combate"
    assert section.position == 1

    soundtrack_repo.rename_section(section.id, "Combate Épico", st.id)
    sections = soundtrack_repo.list_sections(st.id)
    assert sections[0].name == "Combate Épico"

    # Item associado à seção é preservado (só desagrupado) quando a seção é removida.
    item = soundtrack_repo.add_track(st.id, sample_track_id, section_id=section.id)
    soundtrack_repo.delete_section(section.id, st.id)
    assert soundtrack_repo.list_sections(st.id) == []
    remaining = soundtrack_repo.get_items(st.id)
    assert len(remaining) == 1
    assert remaining[0].id == item.id
    assert remaining[0].section_id is None


def test_get_items_orders_unsectioned_first_then_sections_by_position(
    soundtrack_repo, track_repo, library_root_repo
):
    ids = _add(soundtrack_repo, track_repo, library_root_repo, ["Solta", "Tema", "Boss"])
    st = soundtrack_repo.create("Darkrem")

    tema_section = soundtrack_repo.create_section(st.id, "Tema Principal")
    boss_section = soundtrack_repo.create_section(st.id, "Boss")

    # Adiciona fora de ordem para garantir que o ORDER BY é quem manda, não a ordem de insert.
    soundtrack_repo.add_track(st.id, ids["Boss"], section_id=boss_section.id)
    soundtrack_repo.add_track(st.id, ids["Solta"])  # sem seção
    soundtrack_repo.add_track(st.id, ids["Tema"], section_id=tema_section.id)

    items = soundtrack_repo.get_items(st.id)
    assert [i.track.title for i in items] == ["Solta", "Tema", "Boss"]


def test_reorder_sections_changes_group_order(soundtrack_repo, track_repo, library_root_repo):
    ids = _add(soundtrack_repo, track_repo, library_root_repo, ["Tema", "Boss"])
    st = soundtrack_repo.create("Darkrem")
    tema_section = soundtrack_repo.create_section(st.id, "Tema Principal")
    boss_section = soundtrack_repo.create_section(st.id, "Boss")
    soundtrack_repo.add_track(st.id, ids["Tema"], section_id=tema_section.id)
    soundtrack_repo.add_track(st.id, ids["Boss"], section_id=boss_section.id)

    assert [i.track.title for i in soundtrack_repo.get_items(st.id)] == ["Tema", "Boss"]

    soundtrack_repo.reorder_sections(st.id, [boss_section.id, tema_section.id])

    assert [i.track.title for i in soundtrack_repo.get_items(st.id)] == ["Boss", "Tema"]


def test_move_track_to_section_via_context_menu_equivalent(soundtrack_repo, track_repo, library_root_repo):
    ids = _add(soundtrack_repo, track_repo, library_root_repo, ["Musica"])
    st = soundtrack_repo.create("Darkrem")
    section = soundtrack_repo.create_section(st.id, "Exploração")
    item = soundtrack_repo.add_track(st.id, ids["Musica"])
    assert item.section_id is None

    soundtrack_repo.move_track_to_section(item.id, section.id, st.id)

    items = soundtrack_repo.get_items(st.id)
    assert items[0].section_id == section.id


def test_move_item_down_crosses_section_boundary_and_adopts_section(
    soundtrack_repo, track_repo, library_root_repo
):
    ids = _add(soundtrack_repo, track_repo, library_root_repo, ["A", "B", "C", "D", "E"])
    st = soundtrack_repo.create("Darkrem")
    section_x = soundtrack_repo.create_section(st.id, "X")
    section_y = soundtrack_repo.create_section(st.id, "Y")

    soundtrack_repo.add_track(st.id, ids["A"])  # sem seção
    b_item = soundtrack_repo.add_track(st.id, ids["B"])  # sem seção
    soundtrack_repo.add_track(st.id, ids["C"], section_id=section_x.id)
    soundtrack_repo.add_track(st.id, ids["D"], section_id=section_x.id)
    soundtrack_repo.add_track(st.id, ids["E"], section_id=section_y.id)

    assert [i.track.title for i in soundtrack_repo.get_items(st.id)] == ["A", "B", "C", "D", "E"]

    # Move B para baixo: cruza a fronteira da seção X e deve virar membro dela.
    soundtrack_repo.move_item(st.id, b_item.id, direction=1)

    items = soundtrack_repo.get_items(st.id)
    assert [i.track.title for i in items] == ["A", "C", "B", "D", "E"]
    moved = next(i for i in items if i.track.title == "B")
    assert moved.section_id == section_x.id
    # C não muda de seção, só de posição visual.
    c_item = next(i for i in items if i.track.title == "C")
    assert c_item.section_id == section_x.id


def test_move_item_up_out_of_section_becomes_unsectioned(soundtrack_repo, track_repo, library_root_repo):
    ids = _add(soundtrack_repo, track_repo, library_root_repo, ["A", "B"])
    st = soundtrack_repo.create("Darkrem")
    section = soundtrack_repo.create_section(st.id, "X")
    soundtrack_repo.add_track(st.id, ids["A"])  # sem seção
    b_item = soundtrack_repo.add_track(st.id, ids["B"], section_id=section.id)

    assert [i.track.title for i in soundtrack_repo.get_items(st.id)] == ["A", "B"]

    soundtrack_repo.move_item(st.id, b_item.id, direction=-1)

    items = soundtrack_repo.get_items(st.id)
    assert [i.track.title for i in items] == ["B", "A"]
    assert items[0].section_id is None


def test_move_section_swaps_with_neighbor(soundtrack_repo, track_repo, library_root_repo):
    st = soundtrack_repo.create("Darkrem")
    s1 = soundtrack_repo.create_section(st.id, "Tema")
    s2 = soundtrack_repo.create_section(st.id, "Combate")
    s3 = soundtrack_repo.create_section(st.id, "Boss")
    assert [s.name for s in soundtrack_repo.list_sections(st.id)] == ["Tema", "Combate", "Boss"]

    soundtrack_repo.move_section(st.id, s3.id, direction=-1)
    assert [s.name for s in soundtrack_repo.list_sections(st.id)] == ["Tema", "Boss", "Combate"]

    # Não deve estourar limites
    soundtrack_repo.move_section(st.id, s1.id, direction=-1)
    assert [s.name for s in soundtrack_repo.list_sections(st.id)] == ["Tema", "Boss", "Combate"]


def test_reorder_with_sections_full_rewrite(soundtrack_repo, track_repo, library_root_repo):
    ids = _add(soundtrack_repo, track_repo, library_root_repo, ["A", "B"])
    st = soundtrack_repo.create("Darkrem")
    section = soundtrack_repo.create_section(st.id, "X")
    a_item = soundtrack_repo.add_track(st.id, ids["A"])
    b_item = soundtrack_repo.add_track(st.id, ids["B"])

    soundtrack_repo.reorder_with_sections(st.id, [(b_item.id, section.id), (a_item.id, None)])

    items = soundtrack_repo.get_items(st.id)
    assert [i.track.title for i in items] == ["A", "B"]  # sem seção sempre primeiro
    assert items[1].section_id == section.id
