from app.models import Track
from app.services.random_picker import pick_random_track


def _track(id_: int, title: str) -> Track:
    return Track(
        id=id_, library_root_id=1, absolute_path=f"/lib/{title}.mp3", relative_path=f"{title}.mp3",
        filename=f"{title}.mp3", extension=".mp3", title=title, artist=None, album=None,
        duration_seconds=100, file_size=1, partial_hash="h", has_embedded_cover=False,
        is_favorite=False, note="", is_missing=False, play_count=0, last_played_at=None,
        date_detected="now", updated_at="now",
    )


def test_pick_random_returns_none_for_empty_list():
    assert pick_random_track([], []) is None


def test_pick_random_returns_the_only_track():
    track = _track(1, "A")
    assert pick_random_track([track], []) is track


def test_pick_random_avoids_recent_ids_when_possible():
    tracks = [_track(1, "A"), _track(2, "B"), _track(3, "C")]
    for _ in range(50):  # roda várias vezes pra não passar por sorte
        picked = pick_random_track(tracks, recent_ids=[1, 2])
        assert picked.id == 3


def test_pick_random_falls_back_to_full_list_when_all_are_recent():
    tracks = [_track(1, "A"), _track(2, "B")]
    picked = pick_random_track(tracks, recent_ids=[1, 2])
    assert picked is not None
    assert picked.id in (1, 2)


def test_pick_random_only_considers_given_tracks_not_global_library():
    filtered = [_track(5, "Boss")]
    picked = pick_random_track(filtered, recent_ids=[])
    assert picked.id == 5
