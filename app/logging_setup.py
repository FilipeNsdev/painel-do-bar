"""Registro (log) do painel em Dados/Sistema/registros/painel.log.

Quando algo dá errado no computador do bar, é nesse arquivo que está o
detalhe técnico. Ele gira sozinho para não crescer sem limite.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(folder: Path) -> None:
    root = logging.getLogger()
    if any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        return
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%d/%m/%Y %H:%M:%S")
    try:
        folder.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            folder / "painel.log", maxBytes=512_000, backupCount=3, encoding="utf-8"
        )
        handler.setFormatter(fmt)
        root.addHandler(handler)
    except OSError:
        pass
    # No .exe sem console, sys.stderr é None: só mostra no terminal quando existe um.
    if sys.stderr is not None:
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        console.setLevel(logging.WARNING)
        root.addHandler(console)
