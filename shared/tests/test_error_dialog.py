"""Regressão da Etapa 6 (item 62): erros nunca mostram traceback bruto na
mensagem principal — só um texto amigável, com o traceback completo
disponível via "Show Details..." (quando há uma exceção) e sempre
registrado no log."""

from __future__ import annotations

import logging

from rpg_audio_shared.error_dialog import show_friendly_error


def test_friendly_message_never_contains_raw_traceback_markers():
    captured = {}

    class _FakeBox:
        Icon = type("Icon", (), {"Warning": 1})

        def __init__(self, parent=None):
            captured["parent"] = parent

        def setIcon(self, icon):
            pass

        def setWindowTitle(self, title):
            captured["title"] = title

        def setText(self, text):
            captured["text"] = text

        def setDetailedText(self, text):
            captured["detailed"] = text

        def exec(self):
            captured["executed"] = True

    import rpg_audio_shared.error_dialog as module

    original = module.QMessageBox
    module.QMessageBox = _FakeBox
    try:
        try:
            raise ValueError("caminho inválido")
        except ValueError as exc:
            show_friendly_error(None, "Falha", "Não foi possível concluir a operação.", exc=exc)
    finally:
        module.QMessageBox = original

    assert captured["text"] == "Não foi possível concluir a operação."
    assert "Traceback" not in captured["text"]
    assert "Traceback" in captured["detailed"]
    assert captured["executed"] is True


def test_logs_the_exception_even_without_a_details_button(caplog):
    class _FakeBox:
        Icon = type("Icon", (), {"Warning": 1})

        def __init__(self, parent=None):
            pass

        def setIcon(self, icon):
            pass

        def setWindowTitle(self, title):
            pass

        def setText(self, text):
            pass

        def setDetailedText(self, text):
            raise AssertionError("não deveria ser chamado sem exceção")

        def exec(self):
            pass

    import rpg_audio_shared.error_dialog as module

    original = module.QMessageBox
    module.QMessageBox = _FakeBox
    logger = logging.getLogger("test.error_dialog")
    try:
        with caplog.at_level(logging.ERROR, logger="test.error_dialog"):
            show_friendly_error(None, "Aviso", "Nada crítico aconteceu.", logger=logger)
    finally:
        module.QMessageBox = original

    assert "Nada crítico aconteceu." in caplog.text
