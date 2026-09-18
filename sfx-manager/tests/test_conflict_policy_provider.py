"""Regressão da Etapa 6 (item 14): MainWindow precisa realmente repassar o
valor do provider pro ExportDialog ao abrir a exportação."""

from __future__ import annotations

from pathlib import Path

import sfx_app.ui.main_window as main_window_module
from sfx_app.ui.main_window import MainWindow


class _FakeExportDialog:
    last_kwargs: dict = {}

    def __init__(self, *args, **kwargs):
        _FakeExportDialog.last_kwargs = kwargs

    def exec(self):
        return 0  # Rejected

    class DialogCode:
        Accepted = 1
        Rejected = 0


def test_on_export_passes_provider_value_to_dialog(tmp_path: Path, qt_core_app, monkeypatch):
    window = MainWindow(db_path=tmp_path / "test.db")
    window.set_default_conflict_policy_provider(lambda: "skip")

    pack = window.pack_repo.create("Pack")
    window._current_pack_id = pack.id
    root_id = window.library_root_repo.get_or_create("/sfx")
    track_id = window.track_repo.upsert_from_scan(
        library_root_id=root_id, category_id=None, absolute_path="/sfx/a.wav",
        relative_path="a.wav", filename="a.wav", extension=".wav", title="A",
        duration_seconds=1.0, file_size=1, partial_hash="h",
    )
    window.pack_repo.add_track(pack.id, track_id)

    monkeypatch.setattr(main_window_module, "ExportDialog", _FakeExportDialog)
    window._on_export()

    assert _FakeExportDialog.last_kwargs["initial_conflict_policy"] == "skip"
    window.shutdown()


def test_on_export_passes_none_when_no_provider_set(tmp_path: Path, qt_core_app, monkeypatch):
    window = MainWindow(db_path=tmp_path / "test.db")

    pack = window.pack_repo.create("Pack")
    window._current_pack_id = pack.id
    root_id = window.library_root_repo.get_or_create("/sfx")
    track_id = window.track_repo.upsert_from_scan(
        library_root_id=root_id, category_id=None, absolute_path="/sfx/a.wav",
        relative_path="a.wav", filename="a.wav", extension=".wav", title="A",
        duration_seconds=1.0, file_size=1, partial_hash="h",
    )
    window.pack_repo.add_track(pack.id, track_id)

    monkeypatch.setattr(main_window_module, "ExportDialog", _FakeExportDialog)
    window._on_export()

    assert _FakeExportDialog.last_kwargs["initial_conflict_policy"] is None
    window.shutdown()
