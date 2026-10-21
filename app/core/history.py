"""Histórico dos backups, guardado em Sistema/historico_backups.json.

Fica separado do config.json porque é escrito também pelo backup automático,
que roda em outro processo, enquanto o painel pode estar aberto.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.core.jsonfile import read_json, write_json
from app.core.models import BackupRecord

MAX_RECORDS = 60


class BackupHistory:
    def __init__(self, path: Path):
        self.path = path

    def records(self) -> list[BackupRecord]:
        """Mais recente primeiro."""
        raw = read_json(self.path, default=[])
        out = []
        for entry in raw if isinstance(raw, list) else []:
            try:
                out.append(BackupRecord.from_dict(entry))
            except TypeError:
                continue
        return sorted(out, key=lambda r: r.started_at, reverse=True)

    def append(self, record: BackupRecord) -> None:
        records = [record, *self.records()][:MAX_RECORDS]
        write_json(self.path, [r.to_dict() for r in records])

    def last(self) -> BackupRecord | None:
        recs = self.records()
        return recs[0] if recs else None

    def last_success(self) -> BackupRecord | None:
        return next((r for r in self.records() if r.produced_zip), None)

    def last_cloud_success(self) -> BackupRecord | None:
        return next((r for r in self.records() if r.produced_zip and r.reached_cloud), None)

    def is_overdue(self, days: int) -> bool:
        last = self.last_success()
        if last is None:
            return True
        age = datetime.now() - datetime.fromisoformat(last.started_at)
        return age.total_seconds() > days * 86400

    def mtime(self) -> float:
        try:
            return self.path.stat().st_mtime
        except OSError:
            return 0.0
