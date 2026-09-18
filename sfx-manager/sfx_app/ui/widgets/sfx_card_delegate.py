"""Delegate que desenha cada SFX como um "card" clicável (item 39).

Desenhado via QStyledItemDelegate (não um QPushButton por item) para que a
grade continue leve mesmo com milhares de efeitos — o Qt só desenha os
cards visíveis na tela.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

from sfx_app.ui.widgets.sfx_models import TrackObjectRole
from rpg_audio_shared.formatting import format_duration

CARD_SIZE = QSize(132, 96)

_CATEGORY_ICONS = {
    "armas": "⚔️", "espadas": "⚔️", "flechas": "🏹", "armas de fogo": "🔫",
    "impactos": "💥", "magia": "✨", "fogo": "🔥", "gelo": "❄️",
    "eletricidade": "⚡", "explosões": "💥", "monstros": "👹", "animais": "🐾",
    "humanos": "🗣️", "passos": "👣", "portas": "🚪", "objetos": "📦",
    "natureza": "🌿", "clima": "🌧️", "ambiente": "🏞️", "cidade": "🏙️",
    "dungeon": "🕯️", "interface": "🖱️", "terror": "👻",
}
_DEFAULT_ICON = "🔊"


def _icon_for(category_name: str | None) -> str:
    if not category_name:
        return _DEFAULT_ICON
    return _CATEGORY_ICONS.get(category_name.strip().lower(), _DEFAULT_ICON)


class SfxCardDelegate(QStyledItemDelegate):
    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:  # noqa: N802
        return CARD_SIZE

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        track = index.data(TrackObjectRole)
        if track is None:
            super().paint(painter, option, index)
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = option.rect.adjusted(6, 6, -6, -6)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

        if track.is_missing:
            bg = QColor("#3a2226")
            border = QColor("#e0555a")
        elif selected:
            bg = QColor("#5b8cff")
            border = QColor("#5b8cff")
        elif hovered:
            bg = QColor("#2d333e")
            border = QColor("#e0a458")
        else:
            bg = QColor("#262b34")
            border = QColor("#333944")

        painter.setPen(QPen(border, 1))
        painter.setBrush(bg)
        painter.drawRoundedRect(QRectF(rect), 8, 8)

        text_color = QColor("#0d0f12") if selected else QColor("#e8e9ec")
        muted_color = QColor("#0d0f12") if selected else QColor("#9aa0ad")

        icon = _icon_for(track.category_name)
        painter.setPen(text_color)
        icon_font = painter.font()
        icon_font.setPointSize(18)
        painter.setFont(icon_font)
        painter.drawText(
            QRectF(rect.x(), rect.y() + 6, rect.width(), 30),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            icon,
        )

        title_font = painter.font()
        title_font.setPointSize(9)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(text_color)
        title_rect = QRectF(rect.x() + 4, rect.y() + 38, rect.width() - 8, 32)
        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
            track.title,
        )

        meta_font = painter.font()
        meta_font.setBold(False)
        meta_font.setPointSize(8)
        painter.setFont(meta_font)
        painter.setPen(muted_color)
        meta_text = format_duration(track.duration_seconds)
        if track.hotkey:
            meta_text += f"  [{track.hotkey}]"
        painter.drawText(
            QRectF(rect.x(), rect.bottom() - 18, rect.width(), 16),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            meta_text,
        )

        if track.is_favorite:
            painter.setPen(QColor("#e0a458"))
            star_font = painter.font()
            star_font.setPointSize(10)
            painter.setFont(star_font)
            painter.drawText(
                QRectF(rect.right() - 20, rect.y() + 2, 18, 18),
                Qt.AlignmentFlag.AlignCenter,
                "★",
            )

        painter.restore()
