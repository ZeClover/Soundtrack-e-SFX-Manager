"""Painel direito: soundtrack atual, com suporte opcional a seções (itens 25-31, etapa 3 item 5).

Uma soundtrack sem nenhuma seção se comporta exatamente como na etapa 2:
lista plana, sem cabeçalhos. Quando existem seções, elas aparecem como
linhas de cabeçalho intercaladas na mesma lista (não clicáveis/arrastáveis)
— arrastar uma faixa para debaixo de outro cabeçalho reatribui sua seção
e sua posição em uma única operação, exatamente como reordenar.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from soundtrack_app.models import Soundtrack, SoundtrackItem, SoundtrackSection
from rpg_audio_shared.formatting import format_duration
from rpg_audio_shared.theme import DEFAULT_ACCENT

_ITEM_ID_ROLE = Qt.ItemDataRole.UserRole + 1
_TRACK_ID_ROLE = Qt.ItemDataRole.UserRole + 2
_ROW_KIND_ROLE = Qt.ItemDataRole.UserRole + 3
_SECTION_ID_ROLE = Qt.ItemDataRole.UserRole + 4

_KIND_HEADER = "header"
_KIND_TRACK = "track"
_UNSECTIONED_LABEL = "Sem seção"


class SoundtrackPanel(QWidget):
    soundtrack_selected = Signal(int)  # soundtrack_id
    new_soundtrack_requested = Signal()
    remove_item_requested = Signal(int)  # item_id
    move_item_requested = Signal(int, int)  # item_id, direction (-1/+1)
    reorder_requested = Signal(list)  # lista completa [(item_id, section_id|None), ...]
    play_item_requested = Signal(int)  # track_id
    export_requested = Signal()

    create_section_requested = Signal()
    rename_section_requested = Signal(int, str)  # section_id, novo nome
    delete_section_requested = Signal(int)  # section_id
    move_section_requested = Signal(int, int)  # section_id, direction (-1/+1)
    move_item_to_section_requested = Signal(int, object)  # item_id, section_id|None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setMinimumWidth(260)
        self._sections: list[SoundtrackSection] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self.soundtrack_combo = QComboBox()
        self.soundtrack_combo.currentIndexChanged.connect(self._on_combo_changed)
        header.addWidget(self.soundtrack_combo, stretch=1)
        self.new_button = QPushButton("＋ Nova")
        self.new_button.clicked.connect(self.new_soundtrack_requested)
        header.addWidget(self.new_button)
        layout.addLayout(header)

        section_row = QHBoxLayout()
        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("color: #9aa0ad;")
        section_row.addWidget(self.summary_label, stretch=1)
        self.new_section_button = QPushButton("＋ Seção")
        self.new_section_button.setToolTip("Criar uma seção (ex.: Combate, Exploração)")
        self.new_section_button.clicked.connect(self.create_section_requested)
        section_row.addWidget(self.new_section_button)
        layout.addLayout(section_row)

        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_widget.model().rowsMoved.connect(self._on_rows_moved)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.list_widget, stretch=1)

        actions_row = QHBoxLayout()
        self.remove_button = QPushButton("Remover")
        self.remove_button.clicked.connect(self._on_remove_clicked)
        actions_row.addWidget(self.remove_button)
        self.up_button = QPushButton("▲")
        self.up_button.setFixedWidth(36)
        self.up_button.clicked.connect(lambda: self._move_selected(-1))
        actions_row.addWidget(self.up_button)
        self.down_button = QPushButton("▼")
        self.down_button.setFixedWidth(36)
        self.down_button.clicked.connect(lambda: self._move_selected(1))
        actions_row.addWidget(self.down_button)
        layout.addLayout(actions_row)

        self.export_button = QPushButton("EXPORTAR SOUNDTRACK")
        self.export_button.setObjectName("PrimaryButton")
        self.export_button.clicked.connect(self.export_requested)
        layout.addWidget(self.export_button)

        self._loading = False

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def set_soundtracks(self, soundtracks: list[Soundtrack], selected_id: int | None) -> None:
        self._loading = True
        self.soundtrack_combo.clear()
        for st in soundtracks:
            self.soundtrack_combo.addItem(f"{st.name}  ({st.track_count})", st.id)
        if selected_id is not None:
            index = self.soundtrack_combo.findData(selected_id)
            if index >= 0:
                self.soundtrack_combo.setCurrentIndex(index)
        self._loading = False

    def set_content(self, sections: list[SoundtrackSection], items: list[SoundtrackItem]) -> None:
        """Renderiza a lista completa (cabeçalhos de seção + faixas), já na ordem de exibição."""
        self._sections = sections
        self.list_widget.clear()

        by_section: dict[int, list[SoundtrackItem]] = {s.id: [] for s in sections}
        unsectioned: list[SoundtrackItem] = []
        for item in items:
            if item.section_id in by_section:
                by_section[item.section_id].append(item)
            else:
                unsectioned.append(item)

        show_headers = bool(sections)
        total_seconds = 0.0
        position = 1

        def add_track_row(item: SoundtrackItem) -> None:
            nonlocal total_seconds, position
            track = item.track
            total_seconds += track.duration_seconds if track else 0
            title = track.title if track else "(arquivo removido)"
            text = f"{position:02d}. {title}"
            if track:
                text += f"   {format_duration(track.duration_seconds)}"
            list_item = QListWidgetItem(text)
            list_item.setData(_ROW_KIND_ROLE, _KIND_TRACK)
            list_item.setData(_ITEM_ID_ROLE, item.id)
            list_item.setData(_TRACK_ID_ROLE, item.track_id)
            list_item.setData(_SECTION_ID_ROLE, item.section_id)
            self.list_widget.addItem(list_item)
            position += 1

        if show_headers and unsectioned:
            self._add_header_row(None, _UNSECTIONED_LABEL)
            for item in unsectioned:
                add_track_row(item)
        elif not show_headers:
            for item in unsectioned:
                add_track_row(item)

        for section in sections:
            self._add_header_row(section.id, section.name)
            for item in by_section.get(section.id, []):
                add_track_row(item)

        count = len(items)
        self.summary_label.setText(f"{count} música(s) — {format_duration(total_seconds)}")
        self.export_button.setEnabled(count > 0)

    def current_soundtrack_id(self) -> int | None:
        return self.soundtrack_combo.currentData()

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _add_header_row(self, section_id: int | None, name: str) -> None:
        item = QListWidgetItem(f"—  {name.upper()}  —")
        item.setData(_ROW_KIND_ROLE, _KIND_HEADER)
        item.setData(_SECTION_ID_ROLE, section_id)
        flags = item.flags()
        flags &= ~Qt.ItemFlag.ItemIsDragEnabled
        flags &= ~Qt.ItemFlag.ItemIsSelectable
        item.setFlags(flags)
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        item.setForeground(QColor(DEFAULT_ACCENT))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.list_widget.addItem(item)

    def _on_combo_changed(self, _index: int) -> None:
        if self._loading:
            return
        soundtrack_id = self.soundtrack_combo.currentData()
        if soundtrack_id is not None:
            self.soundtrack_selected.emit(soundtrack_id)

    def _selected_track_items(self) -> list[QListWidgetItem]:
        return [
            item for item in self.list_widget.selectedItems()
            if item.data(_ROW_KIND_ROLE) == _KIND_TRACK
        ]

    def _on_remove_clicked(self) -> None:
        for item in self._selected_track_items():
            self.remove_item_requested.emit(item.data(_ITEM_ID_ROLE))

    def _move_selected(self, direction: int) -> None:
        items = self._selected_track_items()
        if len(items) == 1:
            self.move_item_requested.emit(items[0].data(_ITEM_ID_ROLE), direction)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        if item.data(_ROW_KIND_ROLE) != _KIND_TRACK:
            return
        track_id = item.data(_TRACK_ID_ROLE)
        if track_id:
            self.play_item_requested.emit(track_id)

    def _on_rows_moved(self, *_args) -> None:
        """Reconstrói (item_id, section_id) a partir da nova ordem visual completa.

        A seção de cada faixa é a do cabeçalho mais próximo acima dela na
        lista (None se nenhum cabeçalho precede — "sem seção").
        """
        ordered: list[tuple[int, int | None]] = []
        current_section: int | None = None
        for i in range(self.list_widget.count()):
            row = self.list_widget.item(i)
            if row.data(_ROW_KIND_ROLE) == _KIND_HEADER:
                current_section = row.data(_SECTION_ID_ROLE)
            else:
                ordered.append((row.data(_ITEM_ID_ROLE), current_section))
        self.reorder_requested.emit(ordered)

    def _show_context_menu(self, pos) -> None:
        item = self.list_widget.itemAt(pos)
        if item is None:
            return

        if item.data(_ROW_KIND_ROLE) == _KIND_HEADER:
            self._show_header_context_menu(item, pos)
        else:
            self._show_track_context_menu(item, pos)

    def _show_track_context_menu(self, item: QListWidgetItem, pos) -> None:
        menu = QMenu(self)
        play_action = menu.addAction("▶ Tocar")
        remove_action = menu.addAction("Remover da soundtrack")

        move_menu = None
        none_action = None
        section_actions: dict = {}
        if self._sections:
            move_menu = menu.addMenu("Mover para seção")
            current_section = item.data(_SECTION_ID_ROLE)
            none_action = move_menu.addAction(_UNSECTIONED_LABEL)
            none_action.setCheckable(True)
            none_action.setChecked(current_section is None)
            for section in self._sections:
                action = move_menu.addAction(section.name)
                action.setCheckable(True)
                action.setChecked(current_section == section.id)
                section_actions[action] = section.id

        chosen = menu.exec(self.list_widget.viewport().mapToGlobal(pos))
        if chosen == play_action:
            self.play_item_requested.emit(item.data(_TRACK_ID_ROLE))
        elif chosen == remove_action:
            self.remove_item_requested.emit(item.data(_ITEM_ID_ROLE))
        elif move_menu is not None and chosen is not None:
            if chosen is none_action:
                self.move_item_to_section_requested.emit(item.data(_ITEM_ID_ROLE), None)
            elif chosen in section_actions:
                self.move_item_to_section_requested.emit(item.data(_ITEM_ID_ROLE), section_actions[chosen])

    def _show_header_context_menu(self, item: QListWidgetItem, pos) -> None:
        section_id = item.data(_SECTION_ID_ROLE)
        if section_id is None:
            return  # cabeçalho "Sem seção" não é uma seção de verdade, não tem o que editar

        menu = QMenu(self)
        rename_action = menu.addAction("Renomear seção")
        move_up_action = menu.addAction("▲ Mover seção para cima")
        move_down_action = menu.addAction("▼ Mover seção para baixo")
        delete_action = menu.addAction("Remover seção")
        chosen = menu.exec(self.list_widget.viewport().mapToGlobal(pos))

        if chosen == rename_action:
            from PySide6.QtWidgets import QInputDialog
            current = next((s for s in self._sections if s.id == section_id), None)
            current_name = current.name if current else ""
            name, ok = QInputDialog.getText(self, "Renomear seção", "Novo nome:", text=current_name)
            if ok and name.strip():
                self.rename_section_requested.emit(section_id, name.strip())
        elif chosen == move_up_action:
            self.move_section_requested.emit(section_id, -1)
        elif chosen == move_down_action:
            self.move_section_requested.emit(section_id, 1)
        elif chosen == delete_action:
            self.delete_section_requested.emit(section_id)
