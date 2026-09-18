"""Diálogo de erro amigável reutilizável (Etapa 6, item 62).

Regra do produto: a UI nunca mostra um traceback bruto pro usuário — só uma
mensagem amigável. O traceback completo (quando existe uma exceção) sempre
vai pro log em arquivo, e fica disponível na hora também através do botão
nativo "Show Details..." do ``QMessageBox`` (``setDetailedText``), sem
precisar de um diálogo customizado.
"""

from __future__ import annotations

import logging
import traceback

from PySide6.QtWidgets import QMessageBox, QWidget

_MODULE_LOGGER = logging.getLogger(__name__)


def show_friendly_error(
    parent: QWidget | None,
    title: str,
    friendly_message: str,
    *,
    exc: BaseException | None = None,
    logger: logging.Logger | None = None,
) -> None:
    (logger or _MODULE_LOGGER).error(friendly_message, exc_info=exc)

    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(title)
    box.setText(friendly_message)
    if exc is not None:
        box.setDetailedText("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    box.exec()
