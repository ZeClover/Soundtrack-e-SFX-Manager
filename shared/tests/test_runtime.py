from __future__ import annotations

import sys
from pathlib import Path

from rpg_audio_shared.runtime import frozen_base_dir, is_frozen


def test_is_frozen_false_in_normal_dev_execution():
    # O processo de teste nunca é um executável do PyInstaller.
    assert is_frozen() is False


def test_frozen_base_dir_is_none_when_not_frozen():
    assert frozen_base_dir() is None


def test_frozen_base_dir_uses_meipass_when_onefile(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert frozen_base_dir() == tmp_path


def test_frozen_base_dir_falls_back_to_executable_dir_when_onedir(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    fake_exe = tmp_path / "RPG Audio Studio.exe"
    fake_exe.touch()
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    assert frozen_base_dir() == tmp_path
