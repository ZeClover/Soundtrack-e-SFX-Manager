"""Testes do widget LibraryPanel: seleção e navegação (item 18 — escuta rápida)."""

from __future__ import annotations

from app.models import Track
from app.ui.widgets.library_panel import LibraryPanel


def _track(id_: int, title: str) -> Track:
    return Track(
        id=id_, library_root_id=1, absolute_path=f"/lib/{title}.mp3", relative_path=f"{title}.mp3",
        filename=f"{title}.mp3", extension=".mp3", title=title, artist=None, album=None,
        duration_seconds=100, file_size=1, partial_hash="h", has_embedded_cover=False,
        is_favorite=False, note="", is_missing=False, play_count=0, last_played_at=None,
        date_detected="now", updated_at="now",
    )


def test_select_track_id_updates_selection_and_details(qt_core_app):
    panel = LibraryPanel()
    tracks = [_track(1, "A"), _track(2, "B"), _track(3, "C")]
    panel.set_tracks(tracks)

    panel.select_track_id(2)

    assert panel.selected_track().id == 2
    assert panel.detail_title.text().startswith("B")


def test_move_selection_navigates_up_and_down(qt_core_app):
    panel = LibraryPanel()
    tracks = [_track(1, "A"), _track(2, "B"), _track(3, "C")]
    panel.set_tracks(tracks)
    panel.select_track_id(1)

    panel.move_selection(1)
    assert panel.selected_track().id == 2

    panel.move_selection(1)
    assert panel.selected_track().id == 3

    panel.move_selection(1)  # não deve passar do fim
    assert panel.selected_track().id == 3

    panel.move_selection(-1)
    assert panel.selected_track().id == 2


def test_set_tracks_preserves_selection_when_possible(qt_core_app):
    panel = LibraryPanel()
    tracks = [_track(1, "A"), _track(2, "B")]
    panel.set_tracks(tracks)
    panel.select_track_id(2)

    panel.set_tracks([_track(2, "B"), _track(3, "C")])

    assert panel.selected_track().id == 2
