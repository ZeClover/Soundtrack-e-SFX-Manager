"""Testes do Modo Triagem (item 67): navegação e ações sem duplo-toggle de favorito."""

from __future__ import annotations

from app.models import Track
from app.services.player_service import PlayerService
from app.ui.dialogs.triage_dialog import TriageDialog


def _track(id_: int, title: str) -> Track:
    return Track(
        id=id_, library_root_id=1, absolute_path=f"/lib/{title}.mp3", relative_path=f"{title}.mp3",
        filename=f"{title}.mp3", extension=".mp3", title=title, artist="Artista", album=None,
        duration_seconds=1, file_size=1, partial_hash="h", has_embedded_cover=False,
        is_favorite=False, note="", is_missing=True, play_count=0, last_played_at=None,
        date_detected="now", updated_at="now",
    )
    # is_missing=True propositalmente: evita que o PlayerService tente abrir
    # um arquivo de verdade (que não existe) ao trocar de faixa no teste.


def test_triage_dialog_shows_first_track_and_progress(qt_core_app):
    player = PlayerService()
    tracks = [_track(1, "A"), _track(2, "B"), _track(3, "C")]
    dialog = TriageDialog(tracks, player)

    assert dialog.title_label.text() == "A"
    assert dialog.artist_label.text() == "Artista"
    assert dialog.progress_label.text() == "1 / 3"


def test_triage_dialog_add_emits_current_track(qt_core_app):
    player = PlayerService()
    tracks = [_track(1, "A"), _track(2, "B")]
    dialog = TriageDialog(tracks, player)

    emitted = []
    dialog.add_to_soundtrack_requested.connect(emitted.append)
    dialog._on_add()

    assert len(emitted) == 1
    assert emitted[0].title == "A"


def test_triage_dialog_favorite_toggles_locally_without_double_negation(qt_core_app):
    player = PlayerService()
    tracks = [_track(1, "A")]
    dialog = TriageDialog(tracks, player)

    emitted = []
    dialog.favorite_toggle_requested.connect(emitted.append)

    dialog._on_favorite()
    assert emitted[0].is_favorite is True  # já veio invertido, pronto pra persistir direto
    assert dialog.favorite_button.text() == "★ FAVORITO"

    dialog._on_favorite()
    assert emitted[1].is_favorite is False
    assert dialog.favorite_button.text() == "☆ FAVORITO"


def test_triage_dialog_navigation_updates_display(qt_core_app):
    player = PlayerService()
    tracks = [_track(1, "A"), _track(2, "B"), _track(3, "C")]
    dialog = TriageDialog(tracks, player)

    player.next_track()
    assert dialog.title_label.text() == "B"
    assert dialog.progress_label.text() == "2 / 3"

    player.previous_track()
    assert dialog.title_label.text() == "A"
    assert dialog.progress_label.text() == "1 / 3"


def test_triage_dialog_with_empty_list_shows_message(qt_core_app):
    player = PlayerService()
    dialog = TriageDialog([], player)
    assert "Nenhuma música" in dialog.title_label.text()
