"""Painel esquerdo de filtros do SFX Manager: categorias, tags, favoritos.

Diferente do Soundtrack Manager, categorias aparecem como uma lista de
seleção única (mais perto de como pastas de SFX costumam ser navegadas),
não um combo — SFX tende a ter poucas dezenas de categorias, mas usadas o
tempo todo, então vale ficar sempre visível.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.models import Category, Tag

_CATEGORY_ID_ROLE = Qt.ItemDataRole.UserRole + 1
_TAG_ID_ROLE = Qt.ItemDataRole.UserRole + 2
_CHECKABLE = Qt.ItemFlag.ItemIsUserCheckable
_CHECKED = Qt.CheckState.Checked


class SfxFiltersPanel(QWidget):
    filters_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setMinimumWidth(190)
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

        category_header = QHBoxLayout()
        category_header.addWidget(_section_title("Categorias"))
        category_header.addStretch(1)
        self.manage_categories_button = QPushButton("Gerenciar...")
        self.manage_categories_button.setFlat(True)
        self.manage_categories_button.setStyleSheet("color: #e0a458; padding: 0;")
        category_header.addWidget(self.manage_categories_button)
        layout.addLayout(category_header)

        self.category_list = QListWidget()
        self.category_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._add_all_categories_item()
        self.category_list.currentItemChanged.connect(lambda *_: self.filters_changed.emit())
        layout.addWidget(self.category_list, stretch=1)

        layout.addWidget(_section_title("Tags"))
        self.tags_list = QListWidget()
        self.tags_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.tags_list.itemChanged.connect(self.filters_changed)
        layout.addWidget(self.tags_list, stretch=1)

    def _add_all_categories_item(self) -> QListWidgetItem:
        # Sempre cria um item novo (nunca reaproveita um antigo): depois de
        # um QListWidget.clear() o objeto C++ do item anterior já foi
        # destruído pelo Qt, então guardar e reinserir a mesma referência
        # Python quebraria na próxima chamada a set_categories().
        item = QListWidgetItem("Todas")
        item.setData(_CATEGORY_ID_ROLE, None)
        self.category_list.addItem(item)
        self.category_list.setCurrentItem(item)
        return item

    def set_categories(self, categories: list[Category]) -> None:
        current_id = self.selected_category_id
        self.category_list.blockSignals(True)
        self.category_list.clear()
        target = self._add_all_categories_item()
        for category in categories:
            item = QListWidgetItem(category.name)
            item.setData(_CATEGORY_ID_ROLE, category.id)
            self.category_list.addItem(item)
            if category.id == current_id:
                target = item
        self.category_list.setCurrentItem(target)
        self.category_list.blockSignals(False)

    def set_tags(self, tags: list[Tag]) -> None:
        checked_ids = set(self.checked_tag_ids())
        self.tags_list.blockSignals(True)
        self.tags_list.clear()
        for tag in tags:
            item = QListWidgetItem(tag.name)
            item.setData(_TAG_ID_ROLE, tag.id)
            item.setFlags(item.flags() | _CHECKABLE)
            item.setCheckState(Qt.CheckState.Checked if tag.id in checked_ids else Qt.CheckState.Unchecked)
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
    def selected_category_id(self) -> int | None:
        item = self.category_list.currentItem()
        return item.data(_CATEGORY_ID_ROLE) if item else None


def _section_title(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setStyleSheet("color: #9aa0ad; font-weight: 600; font-size: 11px; letter-spacing: 1px;")
    return label
