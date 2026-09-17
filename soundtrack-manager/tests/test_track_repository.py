from app.repositories import TrackFilter


def test_upsert_creates_new_track(track_repo, sample_track_id):
    track = track_repo.get_by_id(sample_track_id)
    assert track is not None
    assert track.title == "Battle Theme"
    assert track.is_favorite is False
    assert track.tags == []


def test_upsert_is_idempotent_and_preserves_user_data(track_repo, library_root_repo):
    root_id = library_root_repo.get_or_create("/library")
    track_id = track_repo.upsert_from_scan(
        library_root_id=root_id, absolute_path="/library/a.mp3", relative_path="a.mp3",
        filename="a.mp3", extension=".mp3", title="A", artist=None, album=None,
        duration_seconds=10, file_size=100, partial_hash="h1", has_embedded_cover=False,
    )
    track_repo.set_favorite(track_id, True)
    track_repo.set_note(track_id, "nota pessoal")

    # Re-scan do mesmo arquivo (metadados podem mudar, classificação do usuário não)
    same_id = track_repo.upsert_from_scan(
        library_root_id=root_id, absolute_path="/library/a.mp3", relative_path="a.mp3",
        filename="a.mp3", extension=".mp3", title="A (retagged)", artist="Someone", album=None,
        duration_seconds=11, file_size=101, partial_hash="h2", has_embedded_cover=False,
    )

    assert same_id == track_id
    track = track_repo.get_by_id(track_id)
    assert track.title == "A (retagged)"
    assert track.is_favorite is True
    assert track.note == "nota pessoal"


def test_mark_missing_flags_tracks_not_seen(track_repo, library_root_repo):
    root_id = library_root_repo.get_or_create("/library")
    id1 = track_repo.upsert_from_scan(
        library_root_id=root_id, absolute_path="/library/a.mp3", relative_path="a.mp3",
        filename="a.mp3", extension=".mp3", title="A", artist=None, album=None,
        duration_seconds=10, file_size=100, partial_hash="h1", has_embedded_cover=False,
    )
    id2 = track_repo.upsert_from_scan(
        library_root_id=root_id, absolute_path="/library/b.mp3", relative_path="b.mp3",
        filename="b.mp3", extension=".mp3", title="B", artist=None, album=None,
        duration_seconds=10, file_size=100, partial_hash="h2", has_embedded_cover=False,
    )

    missing_count = track_repo.mark_missing(root_id, seen_paths={"/library/a.mp3"})

    assert missing_count == 1
    assert track_repo.get_by_id(id1).is_missing is False
    assert track_repo.get_by_id(id2).is_missing is True


def test_find_search_matches_title_artist_and_filename(track_repo, library_root_repo):
    root_id = library_root_repo.get_or_create("/library")
    track_repo.upsert_from_scan(
        library_root_id=root_id, absolute_path="/library/boss.mp3", relative_path="boss.mp3",
        filename="boss.mp3", extension=".mp3", title="Final Boss", artist="X", album=None,
        duration_seconds=10, file_size=100, partial_hash="h1", has_embedded_cover=False,
    )
    track_repo.upsert_from_scan(
        library_root_id=root_id, absolute_path="/library/calm.mp3", relative_path="calm.mp3",
        filename="calm.mp3", extension=".mp3", title="Calm Village", artist="Y", album=None,
        duration_seconds=10, file_size=100, partial_hash="h2", has_embedded_cover=False,
    )

    results = track_repo.find(TrackFilter(search_text="boss"))

    assert len(results) == 1
    assert results[0].title == "Final Boss"


def test_find_favorites_only(track_repo, sample_track_id):
    track_repo.set_favorite(sample_track_id, True)
    all_tracks = track_repo.find(TrackFilter())
    favorites = track_repo.find(TrackFilter(favorites_only=True))

    assert len(all_tracks) == 1
    assert len(favorites) == 1
    assert favorites[0].id == sample_track_id


def test_find_excludes_missing_by_default(track_repo, library_root_repo):
    root_id = library_root_repo.get_or_create("/library")
    track_id = track_repo.upsert_from_scan(
        library_root_id=root_id, absolute_path="/library/a.mp3", relative_path="a.mp3",
        filename="a.mp3", extension=".mp3", title="A", artist=None, album=None,
        duration_seconds=10, file_size=100, partial_hash="h1", has_embedded_cover=False,
    )
    track_repo.mark_missing(root_id, seen_paths=set())

    assert track_repo.find(TrackFilter()) == []
    assert len(track_repo.find(TrackFilter(missing_only=True))) == 1


def test_register_play_increments_count_and_history(track_repo, history_repo, sample_track_id):
    track_repo.register_play(sample_track_id)
    track_repo.register_play(sample_track_id)

    track = track_repo.get_by_id(sample_track_id)
    assert track.play_count == 2
    assert track.last_played_at is not None

    recent = history_repo.recent_tracks()
    assert len(recent) == 1
    assert recent[0].id == sample_track_id


def test_stats_counts_total_favorites_and_used(track_repo, soundtrack_repo, sample_track_id):
    track_repo.set_favorite(sample_track_id, True)
    st = soundtrack_repo.create("Darkrem")
    soundtrack_repo.add_track(st.id, sample_track_id)

    stats = track_repo.stats()

    assert stats["total"] == 1
    assert stats["favorites"] == 1
    assert stats["used_in_soundtracks"] == 1


def test_stats_evaluated_counts_favorite_played_or_used_in_soundtrack(
    track_repo, soundtrack_repo, library_root_repo
):
    """Item 70/71: 'avaliada' = ouvida OU favorita OU usada em soundtrack."""
    root_id = library_root_repo.get_or_create("/library")

    def make(name):
        return track_repo.upsert_from_scan(
            library_root_id=root_id, absolute_path=f"/library/{name}.mp3", relative_path=f"{name}.mp3",
            filename=f"{name}.mp3", extension=".mp3", title=name, artist=None, album=None,
            duration_seconds=10, file_size=100, partial_hash=name, has_embedded_cover=False,
        )

    never_heard = make("nunca-ouvida")
    heard = make("ouvida")
    favorite = make("favorita")
    used = make("usada")

    track_repo.register_play(heard)
    track_repo.set_favorite(favorite, True)
    st = soundtrack_repo.create("Darkrem")
    soundtrack_repo.add_track(st.id, used)

    stats = track_repo.stats()
    assert stats["total"] == 4
    assert stats["evaluated"] == 3  # tudo, exceto never_heard

    unrated = track_repo.find(TrackFilter(unrated_only=True))
    assert [t.id for t in unrated] == [never_heard]
