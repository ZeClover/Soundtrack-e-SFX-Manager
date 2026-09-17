from app.repositories import SfxTrackFilter


def test_upsert_creates_new_track(track_repo, sample_track_id):
    track = track_repo.get_by_id(sample_track_id)
    assert track is not None
    assert track.title == "Sword Slash"
    assert track.is_favorite is False
    assert track.tags == []


def test_upsert_is_idempotent_and_preserves_user_data(track_repo, library_root_repo):
    root_id = library_root_repo.get_or_create("/library")
    track_id = track_repo.upsert_from_scan(
        library_root_id=root_id, category_id=None, absolute_path="/library/a.wav",
        relative_path="a.wav", filename="a.wav", extension=".wav", title="A",
        duration_seconds=1, file_size=100, partial_hash="h1",
    )
    track_repo.set_favorite(track_id, True)
    track_repo.set_note(track_id, "nota pessoal")

    same_id = track_repo.upsert_from_scan(
        library_root_id=root_id, category_id=None, absolute_path="/library/a.wav",
        relative_path="a.wav", filename="a.wav", extension=".wav", title="A (retag)",
        duration_seconds=1.1, file_size=101, partial_hash="h2",
    )

    assert same_id == track_id
    track = track_repo.get_by_id(track_id)
    assert track.title == "A (retag)"
    assert track.is_favorite is True
    assert track.note == "nota pessoal"


def test_mark_missing_flags_tracks_not_seen(track_repo, library_root_repo):
    root_id = library_root_repo.get_or_create("/library")
    id1 = track_repo.upsert_from_scan(
        library_root_id=root_id, category_id=None, absolute_path="/library/a.wav",
        relative_path="a.wav", filename="a.wav", extension=".wav", title="A",
        duration_seconds=1, file_size=100, partial_hash="h1",
    )
    id2 = track_repo.upsert_from_scan(
        library_root_id=root_id, category_id=None, absolute_path="/library/b.wav",
        relative_path="b.wav", filename="b.wav", extension=".wav", title="B",
        duration_seconds=1, file_size=100, partial_hash="h2",
    )

    missing_count = track_repo.mark_missing(root_id, seen_paths={"/library/a.wav"})

    assert missing_count == 1
    assert track_repo.get_by_id(id1).is_missing is False
    assert track_repo.get_by_id(id2).is_missing is True


def test_find_search_matches_title_and_category(track_repo, category_repo, library_root_repo):
    root_id = library_root_repo.get_or_create("/library")
    magic = category_repo.get_or_create("Magia")
    track_repo.upsert_from_scan(
        library_root_id=root_id, category_id=magic.id, absolute_path="/library/fire.wav",
        relative_path="Magia/fire.wav", filename="fire.wav", extension=".wav", title="Fireball",
        duration_seconds=1, file_size=100, partial_hash="h1",
    )
    track_repo.upsert_from_scan(
        library_root_id=root_id, category_id=None, absolute_path="/library/door.wav",
        relative_path="door.wav", filename="door.wav", extension=".wav", title="Door Creak",
        duration_seconds=1, file_size=100, partial_hash="h2",
    )

    by_title = track_repo.find(SfxTrackFilter(search_text="fireball"))
    assert len(by_title) == 1

    by_category = track_repo.find(SfxTrackFilter(search_text="magia"))
    assert len(by_category) == 1
    assert by_category[0].title == "Fireball"


def test_find_favorites_only(track_repo, sample_track_id):
    track_repo.set_favorite(sample_track_id, True)
    assert len(track_repo.find(SfxTrackFilter())) == 1
    favorites = track_repo.find(SfxTrackFilter(favorites_only=True))
    assert len(favorites) == 1
    assert favorites[0].id == sample_track_id


def test_find_by_category(track_repo, category_repo, library_root_repo):
    root_id = library_root_repo.get_or_create("/library")
    swords = category_repo.get_or_create("Espadas")
    doors = category_repo.get_or_create("Portas")
    track_repo.upsert_from_scan(
        library_root_id=root_id, category_id=swords.id, absolute_path="/library/s1.wav",
        relative_path="s1.wav", filename="s1.wav", extension=".wav", title="Slash",
        duration_seconds=1, file_size=100, partial_hash="h1",
    )
    track_repo.upsert_from_scan(
        library_root_id=root_id, category_id=doors.id, absolute_path="/library/d1.wav",
        relative_path="d1.wav", filename="d1.wav", extension=".wav", title="Creak",
        duration_seconds=1, file_size=100, partial_hash="h2",
    )

    results = track_repo.find(SfxTrackFilter(category_id=swords.id))
    assert len(results) == 1
    assert results[0].title == "Slash"
    assert results[0].category_name == "Espadas"


def test_find_excludes_missing_by_default(track_repo, library_root_repo):
    root_id = library_root_repo.get_or_create("/library")
    track_id = track_repo.upsert_from_scan(
        library_root_id=root_id, category_id=None, absolute_path="/library/a.wav",
        relative_path="a.wav", filename="a.wav", extension=".wav", title="A",
        duration_seconds=1, file_size=100, partial_hash="h1",
    )
    track_repo.mark_missing(root_id, seen_paths=set())

    assert track_repo.find(SfxTrackFilter()) == []
    assert len(track_repo.find(SfxTrackFilter(missing_only=True))) == 1


def test_register_play_increments_count_and_history(track_repo, history_repo, sample_track_id):
    track_repo.register_play(sample_track_id)
    track_repo.register_play(sample_track_id)

    track = track_repo.get_by_id(sample_track_id)
    assert track.play_count == 2
    assert track.last_played_at is not None

    recent = history_repo.recent_tracks()
    assert len(recent) == 1
    assert recent[0].id == sample_track_id


def test_stats_counts_total_and_favorites(track_repo, sample_track_id):
    track_repo.set_favorite(sample_track_id, True)
    stats = track_repo.stats()
    assert stats["total"] == 1
    assert stats["favorites"] == 1


def test_set_category_updates_and_shows_in_result(track_repo, category_repo, sample_track_id):
    swords = category_repo.get_or_create("Espadas")
    track_repo.set_category(sample_track_id, swords.id)
    track = track_repo.get_by_id(sample_track_id)
    assert track.category_id == swords.id
    assert track.category_name == "Espadas"
