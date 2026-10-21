"""Ponto de entrada do núcleo: junta pastas, configuração, biblioteca e backup.

A interface (e o modo de backup silencioso) conversam só com esta classe.
Assim dá para trocar a interface no futuro sem mexer nas regras.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

from app.core import excel, scheduler, updater
from app.core.backup import BackupService, ProgressFn
from app.core.history import BackupHistory
from app.core.library import Library
from app.core.models import BackupRecord, BackupTrigger, Item, ItemKind, Settings
from app.core.paths import AppPaths, default_paths, install_dir, is_frozen
from app.core.storage import ConfigStore

log = logging.getLogger(__name__)


class Panel:
    def __init__(self, paths: AppPaths | None = None):
        self.paths = paths or default_paths()
        self.store = ConfigStore(self.paths.config_file)
        self.library = Library(self.paths, self.store)
        self.history = BackupHistory(self.paths.history_file)
        self.backup_service = BackupService(self.paths, self.history)

    # ------------------------------------------------------------------ preferências
    @property
    def settings(self) -> Settings:
        return self.store.settings

    def save_settings(self, new: Settings) -> None:
        """Grava as preferências e ajusta o agendamento do Windows se preciso.

        Pode levantar scheduler.SchedulerError: nesse caso as preferências já
        foram salvas, só o agendamento não pôde ser aplicado.
        """
        old = self.store.settings
        self.store.settings = new
        self.store.save()
        schedule_changed = (
            old.weekly_enabled != new.weekly_enabled
            or old.weekly_day != new.weekly_day
            or old.weekly_time != new.weekly_time
        )
        if schedule_changed:
            try:
                self.apply_schedule()
            except scheduler.SchedulerError:
                if new.weekly_enabled:          # não ficou agendado: não fingir que está
                    new.weekly_enabled = False
                    self.store.save()
                raise

    def set_theme(self, value: str) -> None:
        """Guarda a aparência na hora em que é escolhida ("auto", "claro" ou "escuro")."""
        if value not in ("auto", "claro", "escuro"):
            raise ValueError(f"Aparência desconhecida: {value}")
        if self.settings.theme != value:
            self.settings.theme = value
            self.store.save()

    def save_window_geometry(self, geometry: str) -> None:
        if self.settings.window_geometry != geometry:
            self.settings.window_geometry = geometry
            self.store.save()

    # ------------------------------------------------------------------ agendamento
    def apply_schedule(self) -> None:
        """Cria/atualiza ou remove a tarefa semanal conforme as preferências."""
        if not scheduler.is_supported():
            return
        s = self.settings
        if s.weekly_enabled:
            scheduler.install(s.weekly_day, s.weekly_time)
        else:
            scheduler.uninstall()

    def refresh_schedule_quietly(self) -> None:
        """Recria a tarefa ao abrir o painel.

        Se o .exe mudou de pasta, a tarefa antiga apontaria para o lugar
        errado; recriar sempre garante que ela aponta para o programa atual.
        """
        if self.settings.weekly_enabled and scheduler.is_supported():
            try:
                scheduler.install(self.settings.weekly_day, self.settings.weekly_time)
            except scheduler.SchedulerError:
                log.exception("Não foi possível atualizar a tarefa semanal")

    def next_scheduled_backup(self) -> datetime | None:
        s = self.settings
        if not s.weekly_enabled:
            return None
        try:
            return scheduler.next_run(s.weekly_day, s.weekly_time)
        except scheduler.SchedulerError:
            return None

    # ------------------------------------------------------------------ backup
    def snapshot_items(self) -> list[Item]:
        """Cópia dos itens, para o backup rodar em segundo plano com segurança."""
        return [Item.from_dict(i.to_dict()) for i in self.library.items]

    def open_spreadsheets(self) -> list[Item]:
        """Planilhas do painel que estão abertas agora (pelo arquivo de trava)."""
        open_ids = self.library.open_item_ids()
        return [
            i for i in self.library.items
            if i.id in open_ids and (path := self.library.path_of(i)) and excel.is_spreadsheet(path)
        ]

    def save_and_close_spreadsheets(self) -> excel.ExcelResult:
        """Salva e fecha no Excel tudo que é do painel (pasta Arquivos e atalhos).

        Usado só no backup pelo botão. Pode levantar excel.ExcelError."""
        folders = [self.paths.files]
        files = []
        for item in self.library.items:
            if item.kind is ItemKind.LINKED:
                path = Path(item.target)
                (folders if path.is_dir() else files).append(path)
        return excel.save_and_close(folders, files)

    def run_backup(
        self,
        trigger: BackupTrigger,
        progress: ProgressFn | None = None,
        items: list[Item] | None = None,
        settings: Settings | None = None,
    ) -> BackupRecord:
        items = items if items is not None else self.snapshot_items()
        settings = settings or Settings.from_dict(self.settings.to_dict())
        return self.backup_service.run(items, settings, trigger, progress)

    # ------------------------------------------------------------------ atualização
    def check_update(self) -> updater.UpdateInfo | None:
        """Versão nova no GitHub? Só no .exe: rodando pelo código, nunca oferece."""
        if not is_frozen():
            return None
        updater.cleanup(install_dir())
        return updater.check()

    def download_update(self, info: updater.UpdateInfo, progress=None) -> Path:
        return updater.download(info, install_dir(), progress)

    def install_update(self, new_exe: Path) -> None:
        """Dispara a troca do .exe. A tela deve fechar logo depois."""
        updater.apply(new_exe, Path(sys.executable))

    def backup_is_overdue(self) -> bool:
        s = self.settings
        return s.backup_on_open_if_overdue and self.history.is_overdue(s.backup_overdue_days)
