from soundtrack_app.models import Track
from soundtrack_app.services.playlist_cursor import PlaylistCursor


def _track(id_: int, title: str) -> Track:
    return Track(
        id=id_, library_root_id=1, absolute_path=f"/lib/{title}.mp3", relative_path=f"{title}.mp3",
        filename=f"{title}.mp3", extension=".mp3", title=title, artist=None, album=None,
        duration_seconds=100, file_size=1, partial_hash="h", has_embedded_cover=False,
        is_favorite=False, note="", is_missing=False, play_count=0, last_played_at=None,
        date_detected="now", updated_at="now",
    )


def test_set_items_starts_at_given_index():
    cursor = PlaylistCursor()
    tracks = [_track(1, "A"), _track(2, "B"), _track(3, "C")]
    current = cursor.set_items(tracks, start_index=1)
    assert current.title == "B"
    assert cursor.index == 1


def test_next_and_previous_navigate_in_order():
    cursor = PlaylistCursor()
    cursor.set_items([_track(1, "A"), _track(2, "B"), _track(3, "C")])

    assert cursor.current().title == "A"
    assert cursor.has_previous is False
    assert cursor.has_next is True

    assert cursor.next().title == "B"
    assert cursor.next().title == "C"
    assert cursor.has_next is False
    assert cursor.next() is None  # não avança além do fim

    assert cursor.previous().title == "B"
    assert cursor.previous().title == "A"
    assert cursor.previous() is None  # não recua além do início


def test_empty_playlist():
    cursor = PlaylistCursor()
    assert cursor.set_items([]) is None
    assert cursor.current() is None
    assert cursor.has_next is False
    assert cursor.has_previous is False


def test_jump_to_track_id():
    cursor = PlaylistCursor()
    cursor.set_items([_track(1, "A"), _track(2, "B"), _track(3, "C")])
    found = cursor.jump_to_track_id(3)
    assert found.title == "C"
    assert cursor.index == 2
    assert cursor.jump_to_track_id(999) is None


def test_remove_current_track_moves_index_back():
    cursor = PlaylistCursor()
    cursor.set_items([_track(1, "A"), _track(2, "B"), _track(3, "C")], start_index=2)
    cursor.remove_track_id(3)
    assert [t.title for t in cursor.items] == ["A", "B"]


def test_remove_earlier_track_shifts_index():
    cursor = PlaylistCursor()
    cursor.set_items([_track(1, "A"), _track(2, "B"), _track(3, "C")], start_index=2)
    cursor.remove_track_id(1)
    assert cursor.current().title == "C"
