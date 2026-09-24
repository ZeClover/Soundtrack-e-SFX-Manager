"""Gerenciar tags: renomear, excluir, excluir tags sem uso.

Modelado no mesmo padrão do :class:`CampaignManagerDialog` (lista +
renomear/excluir com confirmação), mas sem campo de "adicionar" — tags
novas continuam sendo criadas normalmente ao editar as tags de uma faixa;
este diálogo só organiza as que já existem.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from soundtrack_app.repositories import TagRepository

_TAG_ID_ROLE = Qt.ItemDataRole.UserRole + 1


def _item_label(name: str, usage_count: int) -> str:
    suffix = "música" if usage_count == 1 else "músicas"
    return f"{name}  ({usage_count} {suffix})"


class TagManagerDialog(QDialog):
    def __init__(self, tag_repo: TagRepository, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gerenciar tags")
        self.setMinimumSize(360, 420)
        self._tag_repo = tag_repo
        self.changed = False

        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget, stretch=1)

        actions_row = QHBoxLayout()
        rename_button = QPushButton("Renomear")
        rename_button.clicked.connect(self._on_rename)
        actions_row.addWidget(rename_button)
        delete_button = QPushButton("Excluir")
        delete_button.clicked.connect(self._on_delete)
        actions_row.addWidget(delete_button)
        layout.addLayout(actions_row)

        cleanup_button = QPushButton("Excluir tags sem uso")
        cleanup_button.clicked.connect(self._on_delete_unused)
        layout.addWidget(cleanup_button)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.accept)
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.accept)
        layout.addWidget(buttons)

        self._reload()

    def _reload(self) -> None:
        self.list_widget.clear()
        for tag in self._tag_repo.list_all():
            item = QListWidgetItem(_item_label(tag.name, tag.usage_count))
            item.setData(_TAG_ID_ROLE, tag.id)
            self.list_widget.addItem(item)

    def _selected_tag(self):
        items = self.list_widget.selectedItems()
        if not items:
            return None
        return items[0].data(_TAG_ID_ROLE), _strip_usage_suffix(items[0].text())

    def _on_rename(self) -> None:
        selected = self._selected_tag()
        if selected is None:
            return
        tag_id, current_name = selected
        name, ok = QInputDialog.getText(self, "Renomear tag", "Novo nome:", text=current_name)
        if not ok or not name.strip():
            return
        self._tag_repo.rename(tag_id, name.strip())
        self.changed = True
        self._reload()

    def _on_delete(self) -> None:
        selected = self._selected_tag()
        if selected is None:
            return
        tag_id, name = selected
        answer = QMessageBox.question(
            self, "Excluir tag",
            f"Excluir a tag “{name}”?\n\nAs músicas não são afetadas, só deixam de "
            "estar associadas a ela.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._tag_repo.delete(tag_id)
        self.changed = True
        self._reload()

    def _on_delete_unused(self) -> None:
        unused = [tag for tag in self._tag_repo.list_all() if tag.usage_count == 0]
        if not unused:
            QMessageBox.information(self, "Excluir tags sem uso", "Não há tags sem uso no momento.")
            return
        answer = QMessageBox.question(
            self, "Excluir tags sem uso",
            f"{len(unused)} tag(s) não estão associadas a nenhuma música e serão excluídas:\n\n"
            + ", ".join(tag.name for tag in unused)
            + "\n\nDeseja continuar?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._tag_repo.delete_unused()
        self.changed = True
        self._reload()


def _strip_usage_suffix(label: str) -> str:
    return label.rsplit("  (", 1)[0]
