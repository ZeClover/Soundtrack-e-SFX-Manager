"""Testes do diálogo de histórico (item 68)."""

from __future__ import annotations

from soundtrack_app.models import Track
from soundtrack_app.ui.dialogs.history_dialog import HistoryDialog


def _track(id_: int, title: str) -> Track:
    return Track(
        id=id_, library_root_id=1, absolute_path=f"/lib/{title}.mp3", relative_path=f"{title}.mp3",
        filename=f"{title}.mp3", extension=".mp3", title=title, artist=None, album=None,
        duration_seconds=90, file_size=1, partial_hash="h", has_embedded_cover=False,
        is_favorite=False, note="", is_missing=False, play_count=0, last_played_at=None,
        date_detected="now", updated_at="now",
    )


def test_history_dialog_lists_tracks_in_given_order(qt_core_app):
    tracks = [_track(3, "C"), _track(2, "B"), _track(1, "A")]
    dialog = HistoryDialog(tracks)
    assert dialog.list_widget.count() == 3
    assert dialog.list_widget.item(0).text().startswith("C")


def test_history_dialog_play_button_emits_selected_track(qt_core_app):
    tracks = [_track(1, "A"), _track(2, "B")]
    dialog = HistoryDialog(tracks)
    dialog.list_widget.setCurrentRow(1)

    emitted = []
    dialog.play_requested.connect(emitted.append)
    dialog._on_play_clicked()

    assert len(emitted) == 1
    assert emitted[0].title == "B"


def test_history_dialog_select_in_library_closes_dialog(qt_core_app):
    tracks = [_track(1, "A")]
    dialog = HistoryDialog(tracks)
    dialog.list_widget.setCurrentRow(0)

    emitted = []
    dialog.select_in_library_requested.connect(emitted.append)
    dialog._on_select_clicked()

    assert len(emitted) == 1
    assert dialog.result() == dialog.DialogCode.Accepted
