from app.repositories import TrackFilter


def test_set_tags_for_track_replaces_and_creates(tag_repo, track_repo, sample_track_id):
    tag_repo.set_tags_for_track(sample_track_id, ["boss", "combate"])
    track = track_repo.get_by_id(sample_track_id)
    assert track.tags == ["boss", "combate"]

    tag_repo.set_tags_for_track(sample_track_id, ["triste"])
    track = track_repo.get_by_id(sample_track_id)
    assert track.tags == ["triste"]


def test_tags_are_case_insensitive_unique(tag_repo):
    t1 = tag_repo.get_or_create("Boss")
    t2 = tag_repo.get_or_create("boss")
    assert t1.id == t2.id


def test_find_by_tag_id(tag_repo, track_repo, sample_track_id):
    tag_repo.set_tags_for_track(sample_track_id, ["boss"])
    tag = tag_repo.get_or_create("boss")

    results = track_repo.find(TrackFilter(tag_ids=(tag.id,)))
    assert len(results) == 1
    assert results[0].id == sample_track_id


def test_search_matches_tag_name(tag_repo, track_repo, sample_track_id):
    tag_repo.set_tags_for_track(sample_track_id, ["dungeon noturna"])
    results = track_repo.find(TrackFilter(search_text="noturna"))
    assert len(results) == 1


def test_campaign_association(campaign_repo, track_repo, sample_track_id):
    campaign_repo.set_campaigns_for_track(sample_track_id, ["Darkrem", "One Piece"])
    track = track_repo.get_by_id(sample_track_id)
    assert track.campaigns == ["Darkrem", "One Piece"]

    darkrem = campaign_repo.get_or_create("Darkrem")
    results = track_repo.find(TrackFilter(campaign_id=darkrem.id))
    assert len(results) == 1


def test_campaign_rename_and_delete(campaign_repo, track_repo, sample_track_id):
    campaign_repo.set_campaigns_for_track(sample_track_id, ["Darkrem"])
    darkrem = campaign_repo.get_or_create("Darkrem")

    campaign_repo.rename(darkrem.id, "Darkrem Remasterizado")
    names = [c.name for c in campaign_repo.list_all()]
    assert names == ["Darkrem Remasterizado"]

    track = track_repo.get_by_id(sample_track_id)
    assert track.campaigns == ["Darkrem Remasterizado"]

    campaign_repo.delete(darkrem.id)
    assert campaign_repo.list_all() == []
    track_after = track_repo.get_by_id(sample_track_id)
    assert track_after.campaigns == []  # a musica continua, so perde a associacao


def test_soundtrack_add_reorder_remove(soundtrack_repo, track_repo, library_root_repo):
    root_id = library_root_repo.get_or_create("/library")
    ids = []
    for i in range(3):
        tid = track_repo.upsert_from_scan(
            library_root_id=root_id, absolute_path=f"/library/{i}.mp3", relative_path=f"{i}.mp3",
            filename=f"{i}.mp3", extension=".mp3", title=f"Track {i}", artist=None, album=None,
            duration_seconds=10, file_size=100, partial_hash=f"h{i}", has_embedded_cover=False,
        )
        ids.append(tid)

    st = soundtrack_repo.create("Darkrem — Soundtrack Principal")
    items = [soundtrack_repo.add_track(st.id, tid) for tid in ids]

    ordered = soundtrack_repo.get_items(st.id)
    assert [item.track.title for item in ordered] == ["Track 0", "Track 1", "Track 2"]

    # Reordenar: colocar o último primeiro
    new_order = [items[2].id, items[0].id, items[1].id]
    soundtrack_repo.reorder(st.id, new_order)
    reordered = soundtrack_repo.get_items(st.id)
    assert [item.track.title for item in reordered] == ["Track 2", "Track 0", "Track 1"]

    # Mover item para cima (Track 1 estava na última posição, sobe uma posição)
    soundtrack_repo.move_item(st.id, items[1].id, direction=-1)
    moved = soundtrack_repo.get_items(st.id)
    assert [item.track.title for item in moved] == ["Track 2", "Track 1", "Track 0"]

    # Remover item
    soundtrack_repo.remove_item(items[0].id, st.id)
    remaining = soundtrack_repo.get_items(st.id)
    assert len(remaining) == 2
    assert all(item.track_id != items[0].track_id for item in remaining)


def test_soundtrack_item_id_is_never_confused_with_track_id(soundtrack_repo, track_repo, library_root_repo):
    """Regressão: get_items() selecionava `si.id` e depois `t.*` (que também tem
    coluna `id`) na mesma query — como o resultado é montado por nome de coluna,
    o id da faixa sobrescrevia o id do item, quebrando remover/mover/reordenar
    sempre que os dois ids fossem diferentes (o caso comum na vida real, já que
    a ordem de descoberta do scanner raramente bate com a ordem de adição)."""
    root_id = library_root_repo.get_or_create("/library")

    # Cria as faixas em ordem C, B, A — para que os track_id NÃO coincidam
    # com a ordem em que serão adicionadas à soundtrack (A, B, C).
    track_ids = {}
    for title in ["C", "B", "A"]:
        track_ids[title] = track_repo.upsert_from_scan(
            library_root_id=root_id, absolute_path=f"/library/{title}.mp3",
            relative_path=f"{title}.mp3", filename=f"{title}.mp3", extension=".mp3",
            title=title, artist=None, album=None, duration_seconds=10, file_size=100,
            partial_hash=title, has_embedded_cover=False,
        )
    # track_ids agora é {"C": 1, "B": 2, "A": 3} — divergente da ordem de uso.

    st = soundtrack_repo.create("Teste")
    added = {title: soundtrack_repo.add_track(st.id, track_ids[title]) for title in ["A", "B", "C"]}
    # added["A"].id == 1 (primeiro item inserido), mas track_ids["A"] == 3.
    assert added["A"].id != track_ids["A"]

    items = soundtrack_repo.get_items(st.id)
    by_title = {item.track.title: item for item in items}
    for title in ["A", "B", "C"]:
        assert by_title[title].id == added[title].id, f"item.id incorreto para {title}"
        assert by_title[title].track_id == track_ids[title]

    # Remover "A" deve remover exatamente o item de A, não o item cujo id
    # coincide com o track_id de A.
    soundtrack_repo.remove_item(by_title["A"].id, st.id)
    remaining_titles = {item.track.title for item in soundtrack_repo.get_items(st.id)}
    assert remaining_titles == {"B", "C"}


def test_soundtrack_has_track_detects_duplicate(soundtrack_repo, sample_track_id):
    st = soundtrack_repo.create("Sessão 14")
    assert soundtrack_repo.has_track(st.id, sample_track_id) is False
    soundtrack_repo.add_track(st.id, sample_track_id)
    assert soundtrack_repo.has_track(st.id, sample_track_id) is True


def test_soundtrack_list_all_includes_track_count(soundtrack_repo, sample_track_id):
    st = soundtrack_repo.create("Academia Mágica")
    soundtrack_repo.add_track(st.id, sample_track_id)

    all_soundtracks = soundtrack_repo.list_all()
    assert len(all_soundtracks) == 1
    assert all_soundtracks[0].track_count == 1
