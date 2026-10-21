"""Leitura e gravação segura de arquivos JSON.

A gravação é atômica: escreve num arquivo temporário e só depois troca pelo
definitivo. Assim, se o PC desligar no meio, o arquivo antigo continua inteiro.
Uma cópia da versão anterior fica em `<nome>.bak` para recuperação.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.flush()
        os.fsync(fh.fileno())
    if path.exists():
        try:
            shutil.copy2(path, path.with_name(path.name + ".bak"))
        except OSError:
            log.warning("Não foi possível guardar a cópia anterior de %s", path)
    os.replace(tmp, path)


def read_json(path: Path, default: Any) -> Any:
    """Lê o JSON; se estiver corrompido, tenta o .bak; senão devolve `default`."""
    for candidate in (path, path.with_name(path.name + ".bak")):
        if not candidate.exists():
            continue
        try:
            with open(candidate, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            log.exception("Arquivo ilegível: %s", candidate)
            if candidate == path:
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                try:
                    path.rename(path.with_name(f"{path.name}.corrompido-{stamp}"))
                except OSError:
                    pass
    return default
