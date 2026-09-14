"""Tema escuro compartilhado pelos três aplicativos.

Objetivo: aparência moderna e discreta (sem neon, sem visual "gamer"
exagerado), com uma única cor de destaque configurável por app.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

# Paleta de cores base (Material-ish, discreta)
BG_BASE = "#1a1d23"
BG_PANEL = "#20242c"
BG_ELEVATED = "#262b34"
BG_HOVER = "#2d333e"
BORDER = "#333944"
TEXT_PRIMARY = "#e8e9ec"
TEXT_SECONDARY = "#9aa0ad"
TEXT_DISABLED = "#5a6070"

# Cor de destaque padrão (pode ser sobrescrita por app via `accent`)
DEFAULT_ACCENT = "#5b8cff"


def apply_dark_theme(app: QApplication, accent: str = DEFAULT_ACCENT) -> None:
    """Aplica o tema escuro (paleta + QSS) à aplicação Qt inteira."""
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(BG_BASE))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base, QColor(BG_PANEL))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(BG_ELEVATED))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(BG_ELEVATED))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Button, QColor(BG_ELEVATED))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#ff5c5c"))
    palette.setColor(QPalette.ColorRole.Link, QColor(accent))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(accent))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#0d0f12"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(TEXT_DISABLED))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(TEXT_DISABLED))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(TEXT_DISABLED))
    app.setPalette(palette)

    app.setStyleSheet(build_stylesheet(accent))


def build_stylesheet(accent: str) -> str:
    return f"""
    * {{
        font-family: "Segoe UI", "Inter", sans-serif;
        font-size: 13px;
        outline: none;
    }}

    QMainWindow, QDialog {{
        background-color: {BG_BASE};
    }}

    QWidget#Panel {{
        background-color: {BG_PANEL};
        border-radius: 6px;
    }}

    QToolTip {{
        background-color: {BG_ELEVATED};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        padding: 4px 6px;
        border-radius: 4px;
    }}

    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        border-radius: 5px;
        padding: 5px 8px;
        color: {TEXT_PRIMARY};
        selection-background-color: {accent};
    }}

    QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
        border: 1px solid {accent};
    }}

    QPushButton {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        border-radius: 5px;
        padding: 6px 14px;
        color: {TEXT_PRIMARY};
    }}

    QPushButton:hover {{
        background-color: {BG_HOVER};
        border-color: {accent};
    }}

    QPushButton:pressed {{
        background-color: {BORDER};
    }}

    QPushButton:disabled {{
        color: {TEXT_DISABLED};
    }}

    QPushButton#PrimaryButton {{
        background-color: {accent};
        color: #0d0f12;
        font-weight: 600;
        border: none;
    }}

    QPushButton#PrimaryButton:hover {{
        background-color: {accent};
    }}

    QListView, QTreeView, QTableView {{
        background-color: {BG_PANEL};
        border: 1px solid {BORDER};
        border-radius: 6px;
        alternate-background-color: {BG_ELEVATED};
        color: {TEXT_PRIMARY};
    }}

    QListView::item, QTreeView::item {{
        padding: 4px 6px;
        border-radius: 4px;
    }}

    QListView::item:selected, QTreeView::item:selected, QTableView::item:selected {{
        background-color: {accent};
        color: #0d0f12;
    }}

    QHeaderView::section {{
        background-color: {BG_ELEVATED};
        color: {TEXT_SECONDARY};
        padding: 6px;
        border: none;
        border-bottom: 1px solid {BORDER};
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER};
        border-radius: 5px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {accent};
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        height: 0px;
    }}

    QSlider::groove:horizontal {{
        height: 4px;
        background: {BORDER};
        border-radius: 2px;
    }}
    QSlider::sub-page:horizontal {{
        background: {accent};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {TEXT_PRIMARY};
        width: 12px;
        height: 12px;
        margin: -5px 0;
        border-radius: 6px;
    }}

    QProgressBar {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        border-radius: 5px;
        text-align: center;
        color: {TEXT_PRIMARY};
    }}
    QProgressBar::chunk {{
        background-color: {accent};
        border-radius: 4px;
    }}

    QMenu {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 20px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background-color: {accent};
        color: #0d0f12;
    }}

    QTabWidget::pane {{
        border: 1px solid {BORDER};
        border-radius: 6px;
    }}
    QTabBar::tab {{
        background: {BG_PANEL};
        color: {TEXT_SECONDARY};
        padding: 6px 14px;
    }}
    QTabBar::tab:selected {{
        color: {TEXT_PRIMARY};
        border-bottom: 2px solid {accent};
    }}

    QSplitter::handle {{
        background-color: {BG_BASE};
    }}
    QSplitter::handle:hover {{
        background-color: {accent};
    }}

    QCheckBox::indicator, QRadioButton::indicator {{
        width: 15px;
        height: 15px;
    }}

    QStatusBar {{
        background-color: {BG_PANEL};
        color: {TEXT_SECONDARY};
    }}
    """
