"""Gerenciar campanhas (item 24/etapa 3 item 7): criar, renomear, apagar."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.repositories import CampaignRepository

_CAMPAIGN_ID_ROLE = Qt.ItemDataRole.UserRole + 1


class CampaignManagerDialog(QDialog):
    def __init__(self, campaign_repo: CampaignRepository, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gerenciar campanhas")
        self.setMinimumSize(360, 420)
        self._campaign_repo = campaign_repo
        self.changed = False

        layout = QVBoxLayout(self)

        add_row = QHBoxLayout()
        self.new_name_edit = QLineEdit()
        self.new_name_edit.setPlaceholderText("Nome da nova campanha (ex.: Darkrem)")
        self.new_name_edit.returnPressed.connect(self._on_add)
        add_row.addWidget(self.new_name_edit, stretch=1)
        add_button = QPushButton("＋ Adicionar")
        add_button.clicked.connect(self._on_add)
        add_row.addWidget(add_button)
        layout.addLayout(add_row)

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

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.accept)
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.accept)
        layout.addWidget(buttons)

        self._reload()

    def _reload(self) -> None:
        self.list_widget.clear()
        for campaign in self._campaign_repo.list_all():
            item = QListWidgetItem(campaign.name)
            item.setData(_CAMPAIGN_ID_ROLE, campaign.id)
            self.list_widget.addItem(item)

    def _selected_campaign(self):
        items = self.list_widget.selectedItems()
        if not items:
            return None
        return items[0].data(_CAMPAIGN_ID_ROLE), items[0].text()

    def _on_add(self) -> None:
        name = self.new_name_edit.text().strip()
        if not name:
            return
        self._campaign_repo.get_or_create(name)
        self.new_name_edit.clear()
        self.changed = True
        self._reload()

    def _on_rename(self) -> None:
        selected = self._selected_campaign()
        if selected is None:
            return
        campaign_id, current_name = selected
        name, ok = QInputDialog.getText(self, "Renomear campanha", "Novo nome:", text=current_name)
        if not ok or not name.strip():
            return
        self._campaign_repo.rename(campaign_id, name.strip())
        self.changed = True
        self._reload()

    def _on_delete(self) -> None:
        selected = self._selected_campaign()
        if selected is None:
            return
        campaign_id, name = selected
        answer = QMessageBox.question(
            self, "Excluir campanha",
            f"Excluir a campanha “{name}”?\n\nAs músicas não são afetadas, só deixam de "
            "estar associadas a ela.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._campaign_repo.delete(campaign_id)
        self.changed = True
        self._reload()
