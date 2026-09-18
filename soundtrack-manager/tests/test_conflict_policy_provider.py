"""Regressão da Etapa 6 (item 14): MainWindow precisa realmente repassar o
valor do provider pro ExportDialog ao abrir a exportação — sem isso, a
preferência salva em Configurações nunca chegaria no diálogo."""

from __future__ import annotations

from pathlib import Path

import soundtrack_app.ui.main_window as main_window_module
from soundtrack_app.ui.main_window import MainWindow


class _FakeExportDialog:
    last_kwargs: dict = {}
    instances: list["_FakeExportDialog"] = []

    def __init__(self, *args, **kwargs):
        _FakeExportDialog.last_kwargs = kwargs
        _FakeExportDialog.instances.append(self)

    def exec(self):
        return 0  # Rejected — não precisa seguir pra exportação de verdade

    class DialogCode:
        Accepted = 1
        Rejected = 0


def test_on_export_passes_provider_value_to_dialog(tmp_path: Path, qt_core_app, monkeypatch):
    window = MainWindow(db_path=tmp_path / "test.db")
    window.set_default_conflict_policy_provider(lambda: "overwrite")

    soundtrack = window.soundtrack_repo.create("Trilha")
    window._reload_soundtracks(select_id=soundtrack.id)
    track_id = window.track_repo.upsert_from_scan(
        library_root_id=window.library_root_repo.get_or_create("/lib"),
        absolute_path="/lib/a.mp3", relative_path="a.mp3", filename="a.mp3",
        extension=".mp3", title="A", artist="", album="", duration_seconds=1.0,
        file_size=1, partial_hash="h", has_embedded_cover=False,
    )
    window.soundtrack_repo.add_track(soundtrack.id, track_id)

    monkeypatch.setattr(main_window_module, "ExportDialog", _FakeExportDialog)
    window._on_export()

    assert _FakeExportDialog.last_kwargs["initial_conflict_policy"] == "overwrite"
    window.shutdown()


def test_on_export_passes_none_when_no_provider_set(tmp_path: Path, qt_core_app, monkeypatch):
    window = MainWindow(db_path=tmp_path / "test.db")

    soundtrack = window.soundtrack_repo.create("Trilha")
    window._reload_soundtracks(select_id=soundtrack.id)
    track_id = window.track_repo.upsert_from_scan(
        library_root_id=window.library_root_repo.get_or_create("/lib"),
        absolute_path="/lib/a.mp3", relative_path="a.mp3", filename="a.mp3",
        extension=".mp3", title="A", artist="", album="", duration_seconds=1.0,
        file_size=1, partial_hash="h", has_embedded_cover=False,
    )
    window.soundtrack_repo.add_track(soundtrack.id, track_id)

    monkeypatch.setattr(main_window_module, "ExportDialog", _FakeExportDialog)
    window._on_export()

    assert _FakeExportDialog.last_kwargs["initial_conflict_policy"] is None
    window.shutdown()
