"""Descobre quais arquivos estão abertos no Excel, Word ou LibreOffice.

Esses programas criam um arquivo de trava ao lado do original enquanto ele
está aberto:
    Excel/Word   ->  ~$Nome do arquivo.xlsx   (o Word às vezes corta o começo)
    LibreOffice  ->  .~lock.Nome do arquivo.xlsx#
"""

from __future__ import annotations

import os
from pathlib import Path


def open_names_in(filenames: list[str]) -> set[str]:
    """Recebe os nomes de uma pasta e devolve os que estão abertos."""
    found: set[str] = set()
    for name in filenames:
        if name.startswith("~$"):
            tail = name[2:]
            match = next(
                (f for f in filenames if f != name and not f.startswith("~$") and f.endswith(tail)),
                None,
            )
            found.add(match or tail)
        elif name.startswith(".~lock.") and name.endswith("#"):
            found.add(name[len(".~lock."):-1])
    return found


def find_open_files(folder: Path, *, recursive: bool = True) -> set[str]:
    """Nomes dos arquivos abertos numa pasta (e subpastas, se recursive)."""
    found: set[str] = set()
    if not folder.is_dir():
        return found
    try:
        if recursive:
            for _dirpath, _dirs, filenames in os.walk(folder):
                found |= open_names_in(filenames)
        else:
            found |= open_names_in(os.listdir(folder))
    except OSError:
        pass
    return found


def is_open(path: Path) -> bool:
    """True se este arquivo específico está aberto."""
    return path.is_file() and path.name in find_open_files(path.parent, recursive=False)
