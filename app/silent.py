"""Modo silencioso: faz o backup sem abrir a janela do painel.

É o que o Agendador de Tarefas do Windows chama toda semana
(PainelDoBar.exe --backup). Também dá para rodar à mão para testar.
"""

from __future__ import annotations

import logging

from app.core.models import BackupTrigger
from app.core.panel import Panel
from app.logging_setup import setup_logging

log = logging.getLogger(__name__)


def run_scheduled_backup() -> int:
    panel = Panel()
    setup_logging(panel.paths.logs)
    log.info("Backup automático iniciado")
    panel.library.sync()
    record = panel.run_backup(BackupTrigger.SCHEDULED)

    if panel.settings.notify_after_auto_backup:
        try:
            from app.ui.notification import show_backup_notification

            show_backup_notification(record, panel.settings.panel_name)
        except Exception:  # noqa: BLE001 - o aviso nunca pode derrubar o backup
            log.exception("Não foi possível mostrar o aviso do backup")
    return 0 if record.produced_zip else 1
