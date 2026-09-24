"""Testes do diálogo de gerenciamento de tags."""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

import soundtrack_app.ui.dialogs.tag_manager_dialog as tag_manager_dialog_module
from soundtrack_app.ui.dialogs.tag_manager_dialog import TagManagerDialog


def _patch_question(monkeypatch, answer):
    monkeypatch.setattr(
        tag_manager_dialog_module.QMessageBox, "question", staticmethod(lambda *a, **k: answer)
    )


def _patch_information(monkeypatch):
    calls = []
    monkeypatch.setattr(
        tag_manager_dialog_module.QMessageBox,
        "information",
        staticmethod(lambda *a, **k: calls.append(a) or None),
    )
    return calls


def _patch_input(monkeypatch, text, ok=True):
    monkeypatch.setattr(
        tag_manager_dialog_module.QInputDialog, "getText", staticmethod(lambda *a, **k: (text, ok))
    )


def test_dialog_lists_tags_with_usage_count(tag_repo, track_repo, sample_track_id):
    tag_repo.set_tags_for_track(sample_track_id, ["boss"])
    tag_repo.get_or_create("sem uso")

    dialog = TagManagerDialog(tag_repo)

    assert dialog.list_widget.count() == 2
    labels = {dialog.list_widget.item(i).text() for i in range(dialog.list_widget.count())}
    assert "boss  (1 música)" in labels
    assert "sem uso  (0 músicas)" in labels
    assert dialog.changed is False


def test_rename_updates_list_and_sets_changed_flag(tag_repo, track_repo, sample_track_id, monkeypatch):
    tag_repo.set_tags_for_track(sample_track_id, ["boss"])
    dialog = TagManagerDialog(tag_repo)
    dialog.list_widget.setCurrentRow(0)
    _patch_input(monkeypatch, "chefão")

    dialog._on_rename()

    assert dialog.changed is True
    assert track_repo.get_by_id(sample_track_id).tags == ["chefão"]
    assert dialog.list_widget.item(0).text().startswith("chefão")


def test_rename_with_empty_name_is_ignored(tag_repo, track_repo, sample_track_id, monkeypatch):
    tag_repo.set_tags_for_track(sample_track_id, ["boss"])
    dialog = TagManagerDialog(tag_repo)
    dialog.list_widget.setCurrentRow(0)
    _patch_input(monkeypatch, "   ")

    dialog._on_rename()

    assert dialog.changed is False
    assert track_repo.get_by_id(sample_track_id).tags == ["boss"]


def test_rename_cancelled_by_user_changes_nothing(tag_repo, track_repo, sample_track_id, monkeypatch):
    tag_repo.set_tags_for_track(sample_track_id, ["boss"])
    dialog = TagManagerDialog(tag_repo)
    dialog.list_widget.setCurrentRow(0)
    _patch_input(monkeypatch, "chefão", ok=False)

    dialog._on_rename()

    assert dialog.changed is False
    assert track_repo.get_by_id(sample_track_id).tags == ["boss"]


def test_delete_asks_confirmation_and_removes_only_the_tag(
    tag_repo, track_repo, sample_track_id, monkeypatch
):
    track_repo.set_favorite(sample_track_id, True)
    tag_repo.set_tags_for_track(sample_track_id, ["boss"])
    dialog = TagManagerDialog(tag_repo)
    dialog.list_widget.setCurrentRow(0)
    _patch_question(monkeypatch, QMessageBox.StandardButton.Yes)

    dialog._on_delete()

    assert dialog.changed is True
    assert dialog.list_widget.count() == 0
    track = track_repo.get_by_id(sample_track_id)
    assert track is not None
    assert track.tags == []
    assert track.is_favorite is True  # a musica e o resto dos dados continuam


def test_delete_declined_confirmation_keeps_the_tag(tag_repo, track_repo, sample_track_id, monkeypatch):
    tag_repo.set_tags_for_track(sample_track_id, ["boss"])
    dialog = TagManagerDialog(tag_repo)
    dialog.list_widget.setCurrentRow(0)
    _patch_question(monkeypatch, QMessageBox.StandardButton.No)

    dialog._on_delete()

    assert dialog.changed is False
    assert track_repo.get_by_id(sample_track_id).tags == ["boss"]


def test_delete_unused_shows_count_and_confirms_before_removing(
    tag_repo, track_repo, sample_track_id, monkeypatch
):
    tag_repo.set_tags_for_track(sample_track_id, ["combate"])
    tag_repo.get_or_create("abandonada 1")
    tag_repo.get_or_create("abandonada 2")
    dialog = TagManagerDialog(tag_repo)

    captured_messages = []
    monkeypatch.setattr(
        tag_manager_dialog_module.QMessageBox,
        "question",
        staticmethod(lambda parent, title, text: captured_messages.append(text) or QMessageBox.StandardButton.Yes),
    )

    dialog._on_delete_unused()

    assert dialog.changed is True
    assert "2" in captured_messages[0]  # mostra quantas serão removidas
    remaining = [t.name for t in tag_repo.list_all()]
    assert remaining == ["combate"]  # só a em uso sobrou


def test_delete_unused_declined_keeps_all_tags(tag_repo, track_repo, sample_track_id, monkeypatch):
    tag_repo.set_tags_for_track(sample_track_id, ["combate"])
    tag_repo.get_or_create("abandonada")
    dialog = TagManagerDialog(tag_repo)
    _patch_question(monkeypatch, QMessageBox.StandardButton.No)

    dialog._on_delete_unused()

    assert dialog.changed is False
    assert {t.name for t in tag_repo.list_all()} == {"combate", "abandonada"}


def test_delete_unused_with_nothing_to_remove_shows_information_and_does_nothing(
    tag_repo, track_repo, sample_track_id, monkeypatch
):
    tag_repo.set_tags_for_track(sample_track_id, ["combate"])
    dialog = TagManagerDialog(tag_repo)
    info_calls = _patch_information(monkeypatch)

    dialog._on_delete_unused()

    assert dialog.changed is False
    assert len(info_calls) == 1
    assert {t.name for t in tag_repo.list_all()} == {"combate"}
