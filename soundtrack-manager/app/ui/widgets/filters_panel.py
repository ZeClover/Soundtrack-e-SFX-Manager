"""Painel esquerdo de filtros: campanha, tags e favoritos (itens 16, 20, 22, 24)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models import Campaign, Tag


class FiltersPanel(QWidget):
    filters_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setMinimumWidth(180)
        self.setMaximumWidth(260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        layout.addWidget(_section_title("Filtros"))

        self.favorites_checkbox = QCheckBox("Somente favoritos")
        self.favorites_checkbox.toggled.connect(self.filters_changed)
        layout.addWidget(self.favorites_checkbox)

        self.missing_checkbox = QCheckBox("Somente ausentes")
        self.missing_checkbox.toggled.connect(self.filters_changed)
        layout.addWidget(self.missing_checkbox)

        layout.addWidget(_section_title("Campanha"))
        self.campaign_combo = QComboBox()
        self.campaign_combo.addItem("Todas", None)
        self.campaign_combo.currentIndexChanged.connect(self.filters_changed)
        layout.addWidget(self.campaign_combo)

        layout.addWidget(_section_title("Tags"))
        self.tags_list = QListWidget()
        self.tags_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.tags_list.itemChanged.connect(self.filters_changed)
        layout.addWidget(self.tags_list, stretch=1)

        layout.addStretch(0)

    def set_campaigns(self, campaigns: list[Campaign]) -> None:
        current = self.campaign_combo.currentData()
        self.campaign_combo.blockSignals(True)
        self.campaign_combo.clear()
        self.campaign_combo.addItem("Todas", None)
        for campaign in campaigns:
            self.campaign_combo.addItem(campaign.name, campaign.id)
        index = self.campaign_combo.findData(current)
        self.campaign_combo.setCurrentIndex(index if index >= 0 else 0)
        self.campaign_combo.blockSignals(False)

    def set_tags(self, tags: list[Tag]) -> None:
        checked_ids = set(self.checked_tag_ids())
        self.tags_list.blockSignals(True)
        self.tags_list.clear()
        for tag in tags:
            item = QListWidgetItem(tag.name)
            item.setData(_TAG_ID_ROLE, tag.id)
            item.setFlags(item.flags() | _CHECKABLE)
            item.setCheckState(_checked_state(tag.id in checked_ids))
            self.tags_list.addItem(item)
        self.tags_list.blockSignals(False)

    def checked_tag_ids(self) -> list[int]:
        ids = []
        for i in range(self.tags_list.count()):
            item = self.tags_list.item(i)
            if item.checkState() == _CHECKED:
                ids.append(item.data(_TAG_ID_ROLE))
        return ids

    @property
    def favorites_only(self) -> bool:
        return self.favorites_checkbox.isChecked()

    @property
    def missing_only(self) -> bool:
        return self.missing_checkbox.isChecked()

    @property
    def campaign_id(self) -> int | None:
        return self.campaign_combo.currentData()


def _section_title(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setStyleSheet("color: #9aa0ad; font-weight: 600; font-size: 11px; letter-spacing: 1px;")
    return label


_TAG_ID_ROLE = Qt.ItemDataRole.UserRole + 1
_CHECKABLE = Qt.ItemFlag.ItemIsUserCheckable
_CHECKED = Qt.CheckState.Checked


def _checked_state(is_checked: bool) -> Qt.CheckState:
    return Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked
