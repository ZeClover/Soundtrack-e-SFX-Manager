"""Estilos extras do shell (barra lateral), aplicados por cima do tema
escuro compartilhado — mantém os módulos com seu QSS de sempre e só
acrescenta a aparência da navegação, que é exclusiva do Studio."""

from __future__ import annotations

from rpg_audio_shared.theme import BG_ELEVATED, BG_PANEL, BORDER, TEXT_PRIMARY, TEXT_SECONDARY


def sidebar_stylesheet(accent: str) -> str:
    return f"""
    QWidget#Sidebar {{
        background-color: {BG_PANEL};
        border-right: 1px solid {BORDER};
    }}

    QLabel#SidebarTitle {{
        color: {TEXT_PRIMARY};
        font-size: 14px;
        font-weight: 700;
        letter-spacing: 1px;
    }}

    QListWidget#SidebarList {{
        background: transparent;
        border: none;
        padding: 6px;
    }}
    QListWidget#SidebarList::item {{
        color: {TEXT_SECONDARY};
        padding: 10px 12px;
        border-radius: 6px;
        margin: 2px 0;
    }}
    QListWidget#SidebarList::item:hover {{
        background-color: {BG_ELEVATED};
        color: {TEXT_PRIMARY};
    }}
    QListWidget#SidebarList::item:selected {{
        background-color: {accent};
        color: #0d0f12;
        font-weight: 600;
    }}
    """
