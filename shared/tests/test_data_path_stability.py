"""Regressão da Etapa 6 (item 9): dados de instalações/desenvolvimento
anteriores não podem se perder no build final. A garantia aqui é
estrutural: o caminho de dados do usuário (``app_data_dir``) nunca depende
de o processo estar rodando do código-fonte ou de um executável
empacotado — só de ``%APPDATA%`` (Windows) ou ``~`` (outros sistemas).
Sem mudança de diretório entre "antes" e "depois", não existe migração a
fazer: os mesmos bancos continuam sendo usados automaticamente."""

from __future__ import annotations

import sys
from pathlib import Path

from rpg_audio_shared.app_dirs import app_data_dir, suite_data_root


def test_app_data_dir_is_identical_whether_frozen_or_not(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "win32")

    not_frozen_path = app_data_dir("soundtrack-manager")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "meipass-do-onefile"), raising=False)
    frozen_path = app_data_dir("soundtrack-manager")

    assert not_frozen_path == frozen_path


def test_suite_data_root_never_reads_frozen_state(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "win32")

    baseline = suite_data_root()

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "RPG Audio Studio.exe"))
    assert suite_data_root() == baseline
