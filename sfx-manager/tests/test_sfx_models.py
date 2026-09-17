"""Testes dos modelos de biblioteca (cards e lista).

Cobre especificamente a regressão em que update_track() quebrava no
SfxCardModel: QAbstractListModel.columnCount() herdado exige o argumento
parent explicitamente em PySide6, e self.columnCount() (sem argumentos)
lançava TypeError até o método ser sobrescrito explicitamente.
"""

from __future__ import annotations

from app.models import SfxTrack
from app.ui.widgets.sfx_models import SfxCardModel, SfxTableModel, TrackObjectRole


def _track(id_: int, title: str, favorite: bool = False) -> SfxTrack:
    return SfxTrack(
        id=id_, library_root_id=1, category_id=None, absolute_path=f"/lib/{title}.wav",
        relative_path=f"{title}.wav", filename=f"{title}.wav", extension=".wav", title=title,
        duration_seconds=1, file_size=1, partial_hash="h", is_favorite=favorite, note="",
        is_missing=False, play_count=0, last_played_at=None, date_detected="now", updated_at="now",
    )


def test_card_model_update_track_does_not_raise(qt_core_app):
    model = SfxCardModel()
    model.set_tracks([_track(1, "A"), _track(2, "B")])

    updated = _track(1, "A", favorite=True)
    model.update_track(updated)  # não deveria lançar TypeError

    index = model.index(0, 0)
    assert model.data(index, TrackObjectRole).is_favorite is True


def test_table_model_update_track_refreshes_all_columns(qt_core_app):
    model = SfxTableModel()
    model.set_tracks([_track(1, "A")])

    updated = _track(1, "A", favorite=True)
    model.update_track(updated)

    index = model.index(0, 0)
    assert model.data(index, TrackObjectRole).is_favorite is True
