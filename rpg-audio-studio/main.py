"""Ponto de entrada do RPG Audio Studio.

Uso em desenvolvimento:
    python main.py

Este arquivo é a "raiz de composição" da aplicação: é o único lugar que
conhece todos os módulos (Música/Soundtracks, SFX/Packs, Downloader, Home,
Configurações) ao mesmo tempo e faz a integração entre eles (item 16) — os
módulos em si não se importam uns aos outros.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox
from rpg_audio_shared.logging_setup import configure_logging, configure_module_log_stream
from rpg_audio_shared.stdio_guard import ensure_stdio
from rpg_audio_shared.theme import apply_dark_theme

from app.bootstrap import ensure_sibling_modules_importable
from app.config import ACCENT_COLOR, APP_NAME, APP_SLUG, log_dir
from app.shell.main_window import StudioWindow
from app.shell.theme_extra import sidebar_stylesheet


def build_studio_window(
    *,
    soundtrack_db_path: Path | None = None,
    sfx_db_path: Path | None = None,
    studio_settings_db_path: Path | None = None,
) -> StudioWindow:
    """Os três parâmetros ``*_db_path`` só existem para os testes
    automatizados poderem montar a janela inteira com bancos isolados em
    ``tmp_path`` — em produção (``main()``) ficam ``None`` e cada módulo usa
    seu caminho real de sempre."""
    ensure_sibling_modules_importable()

    from app.settings.database import Database as StudioDatabase
    from app.settings.settings_page import SettingsPage
    from app.settings.settings_repository import StudioSettingsRepository
    from app.config import database_path as studio_database_path
    from modules.downloader.ui.downloader_page import DownloaderPage
    from modules.history.history_page import HistoryPage
    from modules.home.home_page import HomePage
    from modules.sfx.page import create_sfx_page
    from modules.soundtrack.page import create_soundtrack_page
    from soundtrack_app.ui.widgets.player_bar import PlayerBar

    window = StudioWindow()

    settings_db = StudioDatabase(studio_settings_db_path or studio_database_path())
    settings_repo = StudioSettingsRepository(settings_db)
    window.studio_settings_db = settings_db  # só para fechar limpo no shutdown

    home_page = HomePage(soundtrack_db_path=soundtrack_db_path, sfx_db_path=sfx_db_path)
    window.register_page("home", lambda: home_page)

    def _music_factory():
        module = create_soundtrack_page(db_path=soundtrack_db_path)
        window.set_global_player_bar(PlayerBar(module.player_service))
        return module

    window.register_page("music", _music_factory)
    window.register_page("sfx", lambda: create_sfx_page(db_path=sfx_db_path))

    def _downloader_factory():
        page = DownloaderPage()
        _apply_downloader_preferences(window, settings_repo, page)
        _wire_downloader_to_library(window, page)
        return page

    window.register_page("downloader", _downloader_factory)
    window.register_page(
        "history",
        lambda: HistoryPage(soundtrack_db_path=soundtrack_db_path, sfx_db_path=sfx_db_path),
    )

    def _before_restore() -> None:
        # No Windows, sobrescrever um banco com uma conexão aberta pode
        # falhar — fecha os módulos já abertos nesta sessão antes de
        # restaurar (item 27: restauração com confirmação adequada).
        for key in ("music", "sfx"):
            page = window.get_page(key)
            if page is not None and hasattr(page, "shutdown"):
                page.shutdown()
        settings_db.close()

    def _settings_factory():
        page = SettingsPage(settings_repo)
        page.set_music_folder_hooks(
            lambda: window.ensure_page_created("music").current_library_folder(),
            lambda: window.ensure_page_created("music").select_library_folder(),
        )
        page.set_sfx_folder_hooks(
            lambda: window.ensure_page_created("sfx").current_library_folder(),
            lambda: window.ensure_page_created("sfx").select_library_folder(),
        )
        page.set_before_restore_hook(_before_restore)
        return page

    window.register_page("settings", _settings_factory)

    def _on_home_action(code: str) -> None:
        if code == "add_music":
            window.show_page("music")
            music = window.get_page("music")
            if music is not None:
                music.select_library_folder()
        elif code == "triage":
            window.show_page("music")
            music = window.get_page("music")
            if music is not None:
                music.open_triage()
        elif code == "new_soundtrack":
            window.show_page("music")
            music = window.get_page("music")
            if music is not None:
                music.create_new_soundtrack()
        elif code == "open_sfx":
            window.show_page("sfx")
        elif code == "new_pack":
            window.show_page("sfx")
            sfx = window.get_page("sfx")
            if sfx is not None:
                sfx.create_new_pack()
        elif code == "download_playlist":
            window.show_page("downloader")

    home_page.action_requested.connect(_on_home_action)
    home_page.set_recent_downloads_provider(_recent_download_titles)

    window.show_page("home")
    return window


def _recent_download_titles() -> list[str]:
    from modules.downloader.services.recent_downloads import list_recent_titles

    return list_recent_titles()


def _wire_downloader_to_library(window: StudioWindow, downloader_page) -> None:
    """Integração Downloader → Biblioteca (item 15): depois de um download,
    oferece adicionar a pasta baixada à biblioteca, ou — se a pasta de
    downloads já É a biblioteca configurada — só atualiza (rescan), sem
    copiar nenhum arquivo. Chamada pela própria fábrica lazy da página do
    Downloader (na primeira vez que ela é criada), então este código não
    força o módulo Música a existir antes da hora."""

    def _on_download_finished(report, destination: Path | None) -> None:
        from modules.downloader.models import ItemStatus
        from modules.downloader.services.recent_downloads import record_downloads

        record_downloads([item.title for item in report.completed if item.status == ItemStatus.DONE])

        if report.success_count == 0 or destination is None:
            return

        # Cria o módulo Música se preciso, sem navegar pra lá ainda — assim
        # a pergunta abaixo aparece com o Downloader ainda na tela.
        music = window.ensure_page_created("music")
        if music is None:
            return

        current_folder = music.current_library_folder()
        already_in_library = False
        if current_folder:
            try:
                library_path = Path(current_folder).resolve()
                already_in_library = destination.resolve() == library_path or destination.resolve().is_relative_to(
                    library_path
                )
            except OSError:
                already_in_library = False

        if already_in_library:
            window.status_bar.showMessage("Pasta de downloads já é a biblioteca — atualizando...", 6000)
            music.rescan_library()
            window.show_page("music")
            return

        answer = QMessageBox.question(
            window,
            "Adicionar à biblioteca?",
            f"{report.success_count} música(s) baixada(s) em uma pasta fora da biblioteca atual "
            f"({destination}).\n\nDeseja usar essa pasta como biblioteca de músicas?",
        )
        if answer == QMessageBox.StandardButton.Yes:
            music.scan_folder(destination)
            window.show_page("music")

    downloader_page.download_finished.connect(_on_download_finished)


def _apply_downloader_preferences(window: StudioWindow, settings_repo, downloader_page) -> None:
    """Pré-preenche a página do Downloader com as preferências salvas em
    Configurações (item 19) — nada aqui duplica a preferência, só lê o que
    já está no banco do Studio."""
    from app.settings.settings_repository import (
        KEY_CREATE_PLAYLIST_SUBFOLDER,
        KEY_DOWNLOADS_FOLDER_IS_LIBRARY,
        KEY_DEFAULT_DOWNLOADS_FOLDER,
        KEY_MP3_QUALITY,
        KEY_NUMBER_TRACKS,
        KEY_PREFERRED_FORMAT,
    )

    default_folder = settings_repo.get(KEY_DEFAULT_DOWNLOADS_FOLDER)
    if settings_repo.get(KEY_DOWNLOADS_FOLDER_IS_LIBRARY, False):
        music = window.get_page("music")
        if music is not None and music.current_library_folder():
            default_folder = music.current_library_folder()
    if default_folder:
        downloader_page.destination_edit.setText(default_folder)

    format_index = downloader_page.format_combo.findData(settings_repo.get(KEY_PREFERRED_FORMAT, "mp3"))
    if format_index >= 0:
        downloader_page.format_combo.setCurrentIndex(format_index)

    quality_index = downloader_page.quality_combo.findData(settings_repo.get(KEY_MP3_QUALITY, "high"))
    if quality_index >= 0:
        downloader_page.quality_combo.setCurrentIndex(quality_index)

    downloader_page.numbering_checkbox.setChecked(bool(settings_repo.get(KEY_NUMBER_TRACKS, True)))
    downloader_page.subfolder_checkbox.setChecked(bool(settings_repo.get(KEY_CREATE_PLAYLIST_SUBFOLDER, True)))


def main() -> int:
    # Precisa rodar antes de qualquer outra coisa: pythonw.exe (sem console)
    # deixa sys.stdout/stderr como None, e bibliotecas como o yt-dlp usadas
    # pelo Downloader quebram com 'NoneType' object has no attribute 'write'
    # se tentarem escrever neles (item 13).
    ensure_stdio()

    configure_logging(APP_SLUG)
    # Log geral (app-*.log) já cobre tudo, mas um arquivo por módulo facilita
    # depurar um problema específico sem vasculhar o log inteiro (item 28).
    module_log_dir = log_dir()
    configure_module_log_stream("soundtrack_app", module_log_dir, "soundtrack")
    configure_module_log_stream("sfx_app", module_log_dir, "sfx")
    configure_module_log_stream("modules.downloader", module_log_dir, "downloader")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    apply_dark_theme(app, ACCENT_COLOR)
    app.setStyleSheet(app.styleSheet() + sidebar_stylesheet(ACCENT_COLOR))

    window = build_studio_window()
    window.show()

    exit_code = app.exec()
    window.studio_settings_db.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
