from app.repositories import SfxTrackFilter


def test_set_tags_for_track_replaces_and_creates(tag_repo, track_repo, sample_track_id):
    tag_repo.set_tags_for_track(sample_track_id, ["metal", "pesado"])
    track = track_repo.get_by_id(sample_track_id)
    assert track.tags == ["metal", "pesado"]

    tag_repo.set_tags_for_track(sample_track_id, ["rapido"])
    track = track_repo.get_by_id(sample_track_id)
    assert track.tags == ["rapido"]


def test_tags_are_case_insensitive_unique(tag_repo):
    t1 = tag_repo.get_or_create("Espada")
    t2 = tag_repo.get_or_create("espada")
    assert t1.id == t2.id


def test_find_by_tag_id(tag_repo, track_repo, sample_track_id):
    tag_repo.set_tags_for_track(sample_track_id, ["metal"])
    tag = tag_repo.get_or_create("metal")
    results = track_repo.find(SfxTrackFilter(tag_ids=(tag.id,)))
    assert len(results) == 1


def test_category_rename_and_delete(category_repo, track_repo, sample_track_id):
    swords = category_repo.get_or_create("Espadas")
    track_repo.set_category(sample_track_id, swords.id)

    category_repo.rename(swords.id, "Espadas Longas")
    names = [c.name for c in category_repo.list_all()]
    assert names == ["Espadas Longas"]

    category_repo.delete(swords.id)
    assert category_repo.list_all() == []
    # A faixa continua existindo, só perde a categoria (FK ON DELETE SET NULL)
    track = track_repo.get_by_id(sample_track_id)
    assert track.category_id is None


def test_pack_add_reorder_remove(pack_repo, track_repo, library_root_repo):
    root_id = library_root_repo.get_or_create("/library")
    ids = []
    for i in range(3):
        tid = track_repo.upsert_from_scan(
            library_root_id=root_id, category_id=None, absolute_path=f"/library/{i}.wav",
            relative_path=f"{i}.wav", filename=f"{i}.wav", extension=".wav", title=f"SFX {i}",
            duration_seconds=1, file_size=100, partial_hash=f"h{i}",
        )
        ids.append(tid)

    pack = pack_repo.create("Darkrem — Dungeon")
    items = [pack_repo.add_track(pack.id, tid) for tid in ids]

    ordered = pack_repo.get_items(pack.id)
    assert [item.track.title for item in ordered] == ["SFX 0", "SFX 1", "SFX 2"]

    new_order = [items[2].id, items[0].id, items[1].id]
    pack_repo.reorder(pack.id, new_order)
    reordered = pack_repo.get_items(pack.id)
    assert [item.track.title for item in reordered] == ["SFX 2", "SFX 0", "SFX 1"]

    pack_repo.move_item(pack.id, items[1].id, direction=-1)
    moved = pack_repo.get_items(pack.id)
    assert [item.track.title for item in moved] == ["SFX 2", "SFX 1", "SFX 0"]

    pack_repo.remove_item(items[0].id, pack.id)
    remaining = pack_repo.get_items(pack.id)
    assert len(remaining) == 2
    assert all(item.track_id != items[0].track_id for item in remaining)


def test_pack_has_track_detects_duplicate(pack_repo, sample_track_id):
    pack = pack_repo.create("Combate")
    assert pack_repo.has_track(pack.id, sample_track_id) is False
    pack_repo.add_track(pack.id, sample_track_id)
    assert pack_repo.has_track(pack.id, sample_track_id) is True


def test_pack_item_id_is_never_confused_with_track_id(pack_repo, track_repo, library_root_repo):
    """Mesma regressão coberta no Soundtrack Manager: si.id != t.id na query de itens."""
    root_id = library_root_repo.get_or_create("/library")
    track_ids = {}
    for title in ["C", "B", "A"]:
        track_ids[title] = track_repo.upsert_from_scan(
            library_root_id=root_id, category_id=None, absolute_path=f"/library/{title}.wav",
            relative_path=f"{title}.wav", filename=f"{title}.wav", extension=".wav", title=title,
            duration_seconds=1, file_size=100, partial_hash=title,
        )

    pack = pack_repo.create("Teste")
    added = {title: pack_repo.add_track(pack.id, track_ids[title]) for title in ["A", "B", "C"]}
    assert added["A"].id != track_ids["A"]

    items = pack_repo.get_items(pack.id)
    by_title = {item.track.title: item for item in items}
    for title in ["A", "B", "C"]:
        assert by_title[title].id == added[title].id
        assert by_title[title].track_id == track_ids[title]

    pack_repo.remove_item(by_title["A"].id, pack.id)
    remaining_titles = {item.track.title for item in pack_repo.get_items(pack.id)}
    assert remaining_titles == {"B", "C"}


def test_hotkey_assign_and_map(hotkey_repo, track_repo, sample_track_id, library_root_repo):
    hotkey_repo.assign(sample_track_id, "1")
    assert hotkey_repo.get_key_for_track(sample_track_id) == "1"
    assert hotkey_repo.get_map() == {"1": sample_track_id}

    root_id = library_root_repo.get_or_create("/library")
    other_id = track_repo.upsert_from_scan(
        library_root_id=root_id, category_id=None, absolute_path="/library/x.wav",
        relative_path="x.wav", filename="x.wav", extension=".wav", title="X",
        duration_seconds=1, file_size=100, partial_hash="hx",
    )

    # Reatribuir a mesma tecla para outro efeito libera do anterior
    hotkey_repo.assign(other_id, "1")
    assert hotkey_repo.get_key_for_track(sample_track_id) is None
    assert hotkey_repo.get_key_for_track(other_id) == "1"

    hotkey_repo.clear(other_id)
    assert hotkey_repo.get_map() == {}


def test_track_shows_its_own_hotkey(hotkey_repo, track_repo, sample_track_id):
    hotkey_repo.assign(sample_track_id, "5")
    track = track_repo.get_by_id(sample_track_id)
    assert track.hotkey == "5"
