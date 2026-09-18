"""Regressão de ponta a ponta da Etapa 6 (item 14): salvar a preferência de
duplicados em Configurações precisa mesmo mudar o padrão que aparece no
diálogo de exportação da Música e do SFX dentro do Studio."""

from __future__ import annotations

from pathlib import Path

import main as studio_main
from app.settings.settings_repository import KEY_EXPORT_CONFLICT_POLICY


def _build_window(tmp_path: Path):
    return studio_main.build_studio_window(
        soundtrack_db_path=tmp_path / "soundtrack.db",
        sfx_db_path=tmp_path / "sfx.db",
        studio_settings_db_path=tmp_path / "studio.db",
    )


def test_music_module_provider_reflects_settings_preference(qt_core_app, tmp_path: Path):
    window = _build_window(tmp_path)
    settings = window.ensure_page_created("settings")
    music = window.ensure_page_created("music")

    # padrão inicial (nada salvo ainda)
    assert music._default_conflict_policy_provider() == "rename"

    index = settings.conflict_policy_combo.findData("overwrite")
    settings.conflict_policy_combo.setCurrentIndex(index)

    # o provider consulta o banco a cada chamada, então já reflete a mudança
    assert music._default_conflict_policy_provider() == "overwrite"


def test_sfx_module_provider_reflects_settings_preference(qt_core_app, tmp_path: Path):
    window = _build_window(tmp_path)
    settings = window.ensure_page_created("settings")
    sfx = window.ensure_page_created("sfx")

    index = settings.conflict_policy_combo.findData("skip")
    settings.conflict_policy_combo.setCurrentIndex(index)

    assert sfx._default_conflict_policy_provider() == "skip"


def test_preference_saved_before_module_creation_is_already_applied(qt_core_app, tmp_path: Path):
    from app.settings.database import Database
    from app.settings.settings_repository import StudioSettingsRepository

    studio_db_path = tmp_path / "studio.db"
    db = Database(studio_db_path)
    StudioSettingsRepository(db).set(KEY_EXPORT_CONFLICT_POLICY, "overwrite")
    db.close()

    window = _build_window(tmp_path)
    music = window.ensure_page_created("music")
    assert music._default_conflict_policy_provider() == "overwrite"
