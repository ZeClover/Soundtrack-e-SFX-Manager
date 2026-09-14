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
