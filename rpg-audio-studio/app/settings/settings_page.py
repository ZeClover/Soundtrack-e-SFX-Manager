"""Tela única de Configurações do RPG Audio Studio (item 19).

Cada seção lê/escreve onde o dado já mora de verdade — a pasta da
biblioteca de música e a de SFX continuam nos bancos dos próprios módulos
(``settings_repo`` de cada um); só o que não pertence a nenhum módulo
(pasta padrão de downloads, preferências do Downloader, tema, comportamento
de duplicados na exportação) fica no banco próprio do Studio. Isso evita
duplicar a mesma configuração em três lugares diferentes.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from rpg_audio_shared.error_dialog import show_friendly_error

from app.backup.backup_service import create_backup, restore_backup
from app.settings.settings_repository import (
    KEY_CREATE_PLAYLIST_SUBFOLDER,
    KEY_DEFAULT_DOWNLOADS_FOLDER,
    KEY_DOWNLOADS_FOLDER_IS_LIBRARY,
    KEY_EXPORT_CONFLICT_POLICY,
    KEY_MP3_QUALITY,
    KEY_NUMBER_TRACKS,
    KEY_PREFERRED_FORMAT,
    StudioSettingsRepository,
)

logger = logging.getLogger(__name__)


class SettingsPage(QWidget):
    def __init__(self, settings_repo: StudioSettingsRepository, parent=None):
        super().__init__(parent)
        self._settings_repo = settings_repo
        self._get_music_folder: Callable[[], str | None] | None = None
        self._get_sfx_folder: Callable[[], str | None] | None = None
        self._on_change_music_folder: Callable[[], None] | None = None
        self._on_change_sfx_folder: Callable[[], None] | None = None
        self._before_restore: Callable[[], None] | None = None
        self._build_ui()
        self._load_from_repo()

    # ------------------------------------------------------------------
    # Ganchos com os módulos (injetados pelo main.py — item 16: sem o
    # Studio acoplar Settings diretamente ao soundtrack_app/sfx_app)
    # ------------------------------------------------------------------

    def set_music_folder_hooks(self, getter: Callable[[], str | None], on_change: Callable[[], None]) -> None:
        self._get_music_folder = getter
        self._on_change_music_folder = on_change

    def set_sfx_folder_hooks(self, getter: Callable[[], str | None], on_change: Callable[[], None]) -> None:
        self._get_sfx_folder = getter
        self._on_change_sfx_folder = on_change

    def on_page_shown(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        if self._get_music_folder is not None:
            folder = self._get_music_folder()
            self.music_folder_label.setText(folder or "Nenhuma pasta selecionada")
        if self._get_sfx_folder is not None:
            folder = self._get_sfx_folder()
            self.sfx_folder_label.setText(folder or "Nenhuma pasta selecionada")

    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("Configurações")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        layout.addWidget(self._build_general_group())
        layout.addWidget(self._build_music_group())
        layout.addWidget(self._build_sfx_group())
        layout.addWidget(self._build_downloader_group())
        layout.addWidget(self._build_export_group())
        layout.addWidget(self._build_backup_group())
        layout.addStretch(1)

    def _build_general_group(self) -> QGroupBox:
        group = QGroupBox("Geral")
        form = QFormLayout(group)
        theme_label = QLabel("Escuro (padrão da suíte)")
        theme_label.setStyleSheet("color: #9aa0ad;")
        form.addRow("Tema:", theme_label)

        about_button = QPushButton("Sobre o RPG Audio Studio")
        about_button.clicked.connect(self._on_show_about)
        form.addRow("", about_button)
        return group

    def _on_show_about(self) -> None:
        from app.shell.about_dialog import AboutDialog

        AboutDialog(self).exec()

    def _build_music_group(self) -> QGroupBox:
        group = QGroupBox("Músicas")
        layout = QVBoxLayout(group)
        row = QHBoxLayout()
        self.music_folder_label = QLabel("Nenhuma pasta selecionada")
        self.music_folder_label.setStyleSheet("color: #9aa0ad;")
        row.addWidget(self.music_folder_label, stretch=1)
        change_button = QPushButton("Selecionar pasta...")
        change_button.clicked.connect(self._on_change_music_folder_clicked)
        row.addWidget(change_button)
        layout.addLayout(row)
        return group

    def _build_sfx_group(self) -> QGroupBox:
        group = QGroupBox("SFX")
        layout = QVBoxLayout(group)
        row = QHBoxLayout()
        self.sfx_folder_label = QLabel("Nenhuma pasta selecionada")
        self.sfx_folder_label.setStyleSheet("color: #9aa0ad;")
        row.addWidget(self.sfx_folder_label, stretch=1)
        change_button = QPushButton("Selecionar pasta...")
        change_button.clicked.connect(self._on_change_sfx_folder_clicked)
        row.addWidget(change_button)
        layout.addLayout(row)
        return group

    def _build_downloader_group(self) -> QGroupBox:
        group = QGroupBox("Downloader")
        form = QFormLayout(group)

        dest_row = QHBoxLayout()
        self.default_downloads_edit = QLabel("Nenhuma pasta padrão definida")
        self.default_downloads_edit.setStyleSheet("color: #9aa0ad;")
        dest_row.addWidget(self.default_downloads_edit, stretch=1)
        choose_button = QPushButton("Escolher pasta...")
        choose_button.clicked.connect(self._on_choose_default_downloads_folder)
        dest_row.addWidget(choose_button)
        form.addRow("Pasta padrão de downloads:", dest_row)

        self.use_library_as_downloads_checkbox = QCheckBox(
            "Usar a pasta da biblioteca de músicas como pasta padrão de downloads"
        )
        self.use_library_as_downloads_checkbox.toggled.connect(self._on_use_library_as_downloads_toggled)
        form.addRow(self.use_library_as_downloads_checkbox)

        self.format_combo = QComboBox()
        self.format_combo.addItem("MP3", "mp3")
        self.format_combo.addItem("Melhor áudio original", "best")
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        form.addRow("Formato preferido:", self.format_combo)

        self.quality_combo = QComboBox()
        self.quality_combo.addItem("Alta (~192 kbps)", "high")
        self.quality_combo.addItem("Média (~128 kbps)", "medium")
        self.quality_combo.addItem("Econômica (~96 kbps)", "economic")
        self.quality_combo.currentIndexChanged.connect(self._on_quality_changed)
        form.addRow("Qualidade MP3 preferida:", self.quality_combo)

        self.number_tracks_checkbox = QCheckBox("Numerar músicas pela ordem")
        self.number_tracks_checkbox.toggled.connect(self._on_number_tracks_toggled)
        form.addRow(self.number_tracks_checkbox)

        self.create_subfolder_checkbox = QCheckBox("Criar pasta com nome da playlist")
        self.create_subfolder_checkbox.toggled.connect(self._on_create_subfolder_toggled)
        form.addRow(self.create_subfolder_checkbox)

        return group

    def _build_export_group(self) -> QGroupBox:
        group = QGroupBox("Exportação")
        form = QFormLayout(group)
        self.conflict_policy_combo = QComboBox()
        self.conflict_policy_combo.addItem("Renomear (adiciona um número)", "rename")
        self.conflict_policy_combo.addItem("Substituir o arquivo existente", "overwrite")
        self.conflict_policy_combo.addItem("Pular (não exportar de novo)", "skip")
        self.conflict_policy_combo.currentIndexChanged.connect(self._on_conflict_policy_changed)
        form.addRow("Se já existir um arquivo com o mesmo nome:", self.conflict_policy_combo)
        return group

    def _build_backup_group(self) -> QGroupBox:
        group = QGroupBox("Backup")
        layout = QVBoxLayout(group)

        note = QLabel(
            "Inclui os bancos (músicas, tags, soundtracks, SFX, packs, histórico) e "
            "configurações. Nunca inclui os arquivos de áudio em si."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #9aa0ad;")
        layout.addWidget(note)

        row = QHBoxLayout()
        backup_button = QPushButton("BACKUP DO RPG AUDIO STUDIO")
        backup_button.clicked.connect(self._on_backup_clicked)
        row.addWidget(backup_button)

        restore_button = QPushButton("RESTAURAR BACKUP")
        restore_button.clicked.connect(self._on_restore_clicked)
        row.addWidget(restore_button)
        row.addStretch(1)
        layout.addLayout(row)

        return group

    # ------------------------------------------------------------------
    # Carregar/salvar
    # ------------------------------------------------------------------

    def _load_from_repo(self) -> None:
        folder = self._settings_repo.get(KEY_DEFAULT_DOWNLOADS_FOLDER)
        self.default_downloads_edit.setText(folder or "Nenhuma pasta padrão definida")

        self.use_library_as_downloads_checkbox.blockSignals(True)
        self.use_library_as_downloads_checkbox.setChecked(bool(self._settings_repo.get(KEY_DOWNLOADS_FOLDER_IS_LIBRARY, False)))
        self.use_library_as_downloads_checkbox.blockSignals(False)

        self._select_combo_data(self.format_combo, self._settings_repo.get(KEY_PREFERRED_FORMAT, "mp3"))
        self._select_combo_data(self.quality_combo, self._settings_repo.get(KEY_MP3_QUALITY, "high"))
        self._select_combo_data(self.conflict_policy_combo, self._settings_repo.get(KEY_EXPORT_CONFLICT_POLICY, "rename"))

        self.number_tracks_checkbox.blockSignals(True)
        self.number_tracks_checkbox.setChecked(bool(self._settings_repo.get(KEY_NUMBER_TRACKS, True)))
        self.number_tracks_checkbox.blockSignals(False)

        self.create_subfolder_checkbox.blockSignals(True)
        self.create_subfolder_checkbox.setChecked(bool(self._settings_repo.get(KEY_CREATE_PLAYLIST_SUBFOLDER, True)))
        self.create_subfolder_checkbox.blockSignals(False)

    @staticmethod
    def _select_combo_data(combo: QComboBox, value) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.blockSignals(True)
            combo.setCurrentIndex(index)
            combo.blockSignals(False)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _on_change_music_folder_clicked(self) -> None:
        if self._on_change_music_folder is not None:
            self._on_change_music_folder()
            self.refresh()

    def _on_change_sfx_folder_clicked(self) -> None:
        if self._on_change_sfx_folder is not None:
            self._on_change_sfx_folder()
            self.refresh()

    def _on_choose_default_downloads_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Pasta padrão de downloads")
        if not folder:
            return
        self._settings_repo.set(KEY_DEFAULT_DOWNLOADS_FOLDER, folder)
        self.default_downloads_edit.setText(folder)
        self.use_library_as_downloads_checkbox.blockSignals(True)
        self.use_library_as_downloads_checkbox.setChecked(False)
        self.use_library_as_downloads_checkbox.blockSignals(False)
        self._settings_repo.set(KEY_DOWNLOADS_FOLDER_IS_LIBRARY, False)

    def _on_use_library_as_downloads_toggled(self, checked: bool) -> None:
        self._settings_repo.set(KEY_DOWNLOADS_FOLDER_IS_LIBRARY, checked)
        if checked and self._get_music_folder is not None:
            folder = self._get_music_folder()
            if folder:
                self.default_downloads_edit.setText(folder)

    def _on_format_changed(self) -> None:
        self._settings_repo.set(KEY_PREFERRED_FORMAT, self.format_combo.currentData())

    def _on_quality_changed(self) -> None:
        self._settings_repo.set(KEY_MP3_QUALITY, self.quality_combo.currentData())

    def _on_number_tracks_toggled(self, checked: bool) -> None:
        self._settings_repo.set(KEY_NUMBER_TRACKS, checked)

    def _on_create_subfolder_toggled(self, checked: bool) -> None:
        self._settings_repo.set(KEY_CREATE_PLAYLIST_SUBFOLDER, checked)

    def _on_conflict_policy_changed(self) -> None:
        self._settings_repo.set(KEY_EXPORT_CONFLICT_POLICY, self.conflict_policy_combo.currentData())

    # ------------------------------------------------------------------
    # Backup / Restauração
    # ------------------------------------------------------------------

    def set_before_restore_hook(self, hook: Callable[[], None]) -> None:
        """Chamado antes de sobrescrever os bancos na restauração, pra
        fechar conexões de módulos já abertos nesta sessão (no Windows,
        sobrescrever um arquivo com uma conexão aberta pode falhar)."""
        self._before_restore = hook

    def _on_backup_clicked(self) -> None:
        suggested_name = f"rpg-audio-studio-backup-{self._today_str()}.zip"
        path_str, _ = QFileDialog.getSaveFileName(self, "Salvar backup", suggested_name, "Backup (*.zip)")
        if not path_str:
            return
        try:
            result = create_backup(Path(path_str))
        except Exception as exc:  # noqa: BLE001 - nunca pode derrubar a UI
            show_friendly_error(
                self,
                "Falha ao criar backup",
                "Não foi possível criar o backup. Verifique se a pasta de destino "
                "tem espaço e permissão de escrita, e tente novamente.",
                exc=exc,
                logger=logger,
            )
            return

        message = f"Backup criado em:\n{path_str}\n\nIncluído: {', '.join(result.included) or 'nada (nenhum dado encontrado)'}"
        if result.skipped:
            message += f"\n\nNão encontrado (ainda não existia): {', '.join(result.skipped)}"
        QMessageBox.information(self, "Backup concluído", message)

    def _on_restore_clicked(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(self, "Escolher arquivo de backup", "", "Backup (*.zip)")
        if not path_str:
            return

        answer = QMessageBox.question(
            self,
            "Restaurar backup?",
            "Isso vai SUBSTITUIR os dados atuais (bibliotecas, tags, soundtracks, packs, "
            "histórico e configurações) pelos do backup escolhido.\n\n"
            "Essa ação não pode ser desfeita. Deseja continuar?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        if self._before_restore is not None:
            self._before_restore()

        try:
            result = restore_backup(Path(path_str))
        except Exception as exc:  # noqa: BLE001 - nunca pode derrubar a UI
            show_friendly_error(
                self,
                "Falha ao restaurar backup",
                "Não foi possível restaurar o backup. Confirme que o arquivo escolhido "
                "é um backup válido do RPG Audio Studio e tente novamente.",
                exc=exc,
                logger=logger,
            )
            return

        QMessageBox.information(
            self,
            "Restauração concluída",
            f"Restaurado: {', '.join(result.restored) or 'nada'}.\n\n"
            "O RPG Audio Studio precisa ser reiniciado para usar os dados restaurados. "
            "Ele vai fechar agora — abra de novo pelo ABRIR.bat.",
        )
        app = QApplication.instance()
        if app is not None:
            app.quit()

    @staticmethod
    def _today_str() -> str:
        from datetime import date

        return date.today().isoformat()

    # ------------------------------------------------------------------

    def effective_downloads_folder(self) -> str | None:
        """Resolve a pasta padrão de downloads, considerando a opção "usar
        a biblioteca de música" (item 15)."""
        if self._settings_repo.get(KEY_DOWNLOADS_FOLDER_IS_LIBRARY, False) and self._get_music_folder is not None:
            folder = self._get_music_folder()
            if folder:
                return folder
        return self._settings_repo.get(KEY_DEFAULT_DOWNLOADS_FOLDER)
