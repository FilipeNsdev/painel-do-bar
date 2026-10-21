"""Estruturas de dados do painel.

Cada classe sabe se converter para/desde dicionário (JSON). A leitura ignora
campos desconhecidos e usa o padrão para campos ausentes, assim versões novas
do programa conseguem ler configurações antigas e vice-versa.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar

T = TypeVar("T")


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def _from_dict(cls: type[T], data: dict[str, Any]) -> T:
    known = {f.name for f in fields(cls)}  # type: ignore[arg-type]
    return cls(**{k: v for k, v in data.items() if k in known})


class ItemKind(str, Enum):
    MANAGED = "gerenciado"   # arquivo/pasta guardado dentro de Dados/Arquivos
    LINKED = "vinculado"     # arquivo/pasta que continua em outro lugar do PC
    LINK = "link"            # endereço de site


@dataclass
class Item:
    """Um cartão do painel.

    `name`, `description`, `image` e `color` existem só no painel: mudar
    qualquer um deles nunca renomeia nem altera o arquivo de verdade.
    """

    kind: ItemKind
    target: str              # gerenciado: nome dentro de Arquivos | vinculado: caminho completo | link: URL
    name: str
    id: str = field(default_factory=new_id)
    description: str = ""
    image: str | None = None         # nome do arquivo em Sistema/imagens
    color: str | None = None         # cor escolhida para o cartão (sem foto)
    include_in_backup: bool = True
    position: int = 0
    added_at: str = field(default_factory=now_iso)
    missing_since: str | None = None  # quando o arquivo deixou de ser encontrado

    @property
    def is_missing(self) -> bool:
        return self.missing_since is not None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Item":
        data = dict(data)
        data["kind"] = ItemKind(data.get("kind", ItemKind.LINKED.value))
        return _from_dict(cls, data)


WEEKDAYS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


@dataclass
class Settings:
    panel_name: str = "Painel do Bar"
    theme: str = "auto"                     # auto | claro | escuro
    backup_destination: str = ""            # pasta na nuvem (Google Drive, OneDrive...)
    backup_keep: int = 10                   # quantos backups manter em cada lugar
    backup_on_open_if_overdue: bool = True
    backup_overdue_days: int = 7
    weekly_enabled: bool = False
    weekly_day: int = 6                     # 0 = segunda ... 6 = domingo
    weekly_time: str = "22:00"
    notify_after_auto_backup: bool = True
    window_geometry: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Settings":
        return _from_dict(cls, data)


class BackupStatus(str, Enum):
    OK = "ok"
    WARNING = "aviso"     # backup feito, mas com observações (ex.: nuvem indisponível)
    FAILED = "falha"


class BackupTrigger(str, Enum):
    MANUAL = "manual"
    SCHEDULED = "agendado"
    ON_OPEN = "ao_abrir"

    @property
    def label(self) -> str:
        return {"manual": "Manual", "agendado": "Semanal", "ao_abrir": "Ao abrir"}[self.value]


@dataclass
class BackupRecord:
    started_at: str
    finished_at: str
    trigger: str
    status: str
    file_name: str = ""
    size_bytes: int = 0
    file_count: int = 0
    local_path: str = ""
    cloud_path: str = ""
    warnings: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def produced_zip(self) -> bool:
        return self.status in (BackupStatus.OK.value, BackupStatus.WARNING.value)

    @property
    def reached_cloud(self) -> bool:
        return bool(self.cloud_path)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BackupRecord":
        return _from_dict(cls, data)
