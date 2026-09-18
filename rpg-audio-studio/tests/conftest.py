import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.bootstrap import ensure_sibling_modules_importable  # noqa: E402

ensure_sibling_modules_importable()


@pytest.fixture(scope="session", autouse=True)
def qt_core_app():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def _isolated_suite_data_root(tmp_path: Path, monkeypatch):
    """Rede de segurança contra tocar em dados reais do usuário durante os
    testes: qualquer código que resolva um caminho de dados através de
    ``rpg_audio_shared.app_dirs`` (bancos dos módulos, configurações do
    Studio, download_archive, recent_downloads...) — mesmo um caminho ao
    qual um teste específico não passou ``db_path``/``archive_path``
    explicitamente — cai dentro de ``tmp_path`` em vez de
    ``~/.rpg-audio-toolkit`` real. Isso já pegou dados reais sendo escritos
    durante o desenvolvimento desta suíte (Home lendo estatísticas, downloads
    recentes) antes de existir."""
    from rpg_audio_shared import app_dirs

    isolated_root = tmp_path / "rpg-audio-toolkit-isolated"
    monkeypatch.setattr(app_dirs, "suite_data_root", lambda: isolated_root)


@pytest.fixture
def studio_db_path(tmp_path: Path) -> Path:
    return tmp_path / "studio_settings.db"
