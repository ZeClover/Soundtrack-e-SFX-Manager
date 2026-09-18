"""Testes do painel de filtros do SFX Manager.

Cobre especificamente a regressão em que chamar set_categories() mais de
uma vez quebrava: o item "Todas" era reaproveitado após um
QListWidget.clear() já ter destruído seu objeto C++ subjacente.
"""

from __future__ import annotations

from sfx_app.models import Category, Tag
from sfx_app.ui.widgets.sfx_filters_panel import SfxFiltersPanel


def test_set_categories_can_be_called_multiple_times(qt_core_app):
    panel = SfxFiltersPanel()
    panel.set_categories([Category(id=1, name="Espadas"), Category(id=2, name="Portas")])
    panel.set_categories([Category(id=1, name="Espadas"), Category(id=2, name="Portas"), Category(id=3, name="Magia")])
    panel.set_categories([Category(id=1, name="Espadas")])

    names = [panel.category_list.item(i).text() for i in range(panel.category_list.count())]
    assert names == ["Todas", "Espadas"]


def test_set_categories_preserves_selection_across_reload(qt_core_app):
    panel = SfxFiltersPanel()
    categories = [Category(id=1, name="Espadas"), Category(id=2, name="Portas")]
    panel.set_categories(categories)

    for i in range(panel.category_list.count()):
        if panel.category_list.item(i).text() == "Portas":
            panel.category_list.setCurrentRow(i)

    assert panel.selected_category_id == 2

    panel.set_categories(categories)
    assert panel.selected_category_id == 2


def test_set_tags_can_be_called_multiple_times(qt_core_app):
    panel = SfxFiltersPanel()
    panel.set_tags([Tag(id=1, name="metal")])
    panel.set_tags([Tag(id=1, name="metal"), Tag(id=2, name="pesado")])
    assert panel.tags_list.count() == 2
