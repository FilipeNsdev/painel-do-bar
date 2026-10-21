"""Configuração do painel (itens + preferências) salva em Sistema/config.json.

Para mudar o formato no futuro: aumente SCHEMA_VERSION e escreva uma função
de migração em MIGRATIONS, que recebe o dicionário da versão anterior e
devolve o da versão nova. Configurações antigas são atualizadas sozinhas.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

from app.core.jsonfile import read_json, write_json
from app.core.models import Item, Settings

log = logging.getLogger(__name__)

SCHEMA_VERSION = 1

# versão de origem -> função que converte para a versão seguinte
MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {}


def migrate(data: dict[str, Any]) -> dict[str, Any]:
    version = int(data.get("versao", SCHEMA_VERSION))
    while version < SCHEMA_VERSION:
        step = MIGRATIONS.get(version)
        if step is None:
            raise ValueError(f"Sem migração da versão {version}")
        data = step(data)
        version += 1
        data["versao"] = version
    return data


class ConfigStore:
    """Mantém a configuração em memória e grava no disco a cada mudança."""

    def __init__(self, path: Path):
        self.path = path
        self.settings = Settings()
        self.items: list[Item] = []
        self.load()

    def load(self) -> None:
        raw = read_json(self.path, default={})
        try:
            raw = migrate(raw) if raw else {}
        except ValueError:
            log.exception("Configuração com versão desconhecida; usando padrão")
            raw = {}
        self.settings = Settings.from_dict(raw.get("preferencias", {}))
        self.items = []
        for entry in raw.get("itens", []):
            try:
                self.items.append(Item.from_dict(entry))
            except (TypeError, ValueError):
                log.warning("Item ignorado por estar inválido: %r", entry)

    def save(self) -> None:
        write_json(
            self.path,
            {
                "versao": SCHEMA_VERSION,
                "preferencias": self.settings.to_dict(),
                "itens": [item.to_dict() for item in self.items],
            },
        )
