"""Regressão da Etapa 6 (item 14): a preferência de comportamento de
duplicados salva em Configurações precisa realmente pré-selecionar o
diálogo de exportação, não só ficar guardada sem efeito."""

from __future__ import annotations

from sfx_app.ui.dialogs.export_dialog import ExportDialog


def test_default_conflict_combo_selection_without_initial_policy(qt_core_app):
    dialog = ExportDialog("Pack", 3)
    assert dialog.conflict_combo.currentData() == "rename"


def test_initial_conflict_policy_preselects_the_combo(qt_core_app):
    dialog = ExportDialog("Pack", 3, initial_conflict_policy="overwrite")
    assert dialog.conflict_combo.currentData() == "overwrite"


def test_initial_conflict_policy_skip(qt_core_app):
    dialog = ExportDialog("Pack", 3, initial_conflict_policy="skip")
    assert dialog.conflict_combo.currentData() == "skip"
